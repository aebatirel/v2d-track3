"""Start-frame survey (orchestrator request 1 Nov 06:36 UTC, keen-heisenberg; REPORT ONLY: no gates, no new pieces).
For every packed eval reference (focused-pascal packed_refs.json): every object free at its reference pose at f0 with
its PACKED collision geometry, hands-free plain-MuJoCo settle (settle.py scene: sim=rl options, table plane at the
reference's support usda top, URDF mass / COM / inertia, condim 3, friction 1, 2.0 s). If any object has a robot hand
point within 30 mm at f0, also the first H30 rest frame (first frame of the first run of >= 5 frames in which every
object is H30 and static, < 2 mm per frame). GT-free: our references, our meshes, the packed pieces, our table.

  python -I f0_survey.py PACKED_REFS.json DL_ROOTS(comma) FP_PIPELINE COACD1011 WORK OUT_DIR EP [EP ...]

Collision per object = the URDF the reference names (object_urdf_paths): /content/refs/... -> the downloaded store copy;
/content/assets/... -> make_assets.py (focused-pascal) on the episode's library with its packed --pieces folder.
<collision> glb -> FlashCHORD's CoACD (1.0.11, threshold 0.05, cached by glb md5); obj / stl -> one piece each.
Diagnostics at the settled frame (heuristics, labelled): table penetration of the lowest collision point; floating
(> 4 mm above the table and > 4 mm from every partner); packed overlap with each partner (cm3, 1.5 mm grid, both
directions, max); support band = collision vertices within 1 mm (and 3 mm) of the lowest point, COM margin to the band's
xy hull (mm, > 0 inside); hand distance.
Settle: exact pose + 16 copies, every object jittered 0.5 mm / 0.005 rad (seed 2). Falls over := rotation >= 30 deg at
2 s; moved := > 4 mm or > 5 deg (the G3 thresholds of GATES.md, used here only as labels).
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull, Delaunay
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebase as rb  # noqa: E402
import settle as st  # noqa: E402

PIECES = {'1': 'meshes/carve/ev01', '10': 'meshes/carve/ev10', '25': 'meshes/carve/ev25'}
FALL_DEG, MOVE_MM, MOVE_DEG, FLOAT_M, OV_CM3 = 30.0, 4.0, 5.0, 0.004, 1.0
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import sys, numpy as np, trimesh
sys.path.insert(0, sys.argv[1]); import coacd, importlib.metadata as md
coacd.set_log_level("error")
m = trimesh.load(sys.argv[2], force="mesh")
parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(m.vertices, np.float64), np.ascontiguousarray(m.faces, np.int64)),
                        threshold=0.05, max_convex_hull=-1, preprocess_mode="auto")
np.savez(sys.argv[3], n=np.int64(len(parts)), **{f"v{i}": np.asarray(v, np.float64) for i, (v, f) in enumerate(parts)})
print(md.version("coacd"), len(parts))
'''


def coacd_npz(glb, coacd_t, cache):
    os.makedirs(cache, exist_ok=True); p = f'{cache}/{md5(glb)}.npz'
    if not os.path.exists(p):
        r = subprocess.run([sys.executable, '-I', '-c', CHILD, coacd_t, glb, p], capture_output=True, text=True)
        assert r.returncode == 0 and r.stdout.startswith('1.0.11'), r.stderr[-500:]
    return p


def collisions(urdf):
    s = open(urdf).read(); d = os.path.dirname(urdf)
    cols = [os.path.normpath(os.path.join(d, f)) for f in re.findall(
        r'<collision>.*?<mesh filename="([^"]*)"', s, re.S)]
    vis = os.path.normpath(os.path.join(d, re.search(r'<visual>.*?<mesh filename="([^"]*)"', s, re.S).group(1)))
    return cols, vis


def main():
    refs, roots, fp, coacd_t, work, out = sys.argv[1:7]; eps = sys.argv[7:]
    P = json.load(open(refs))['episodes']; roots = roots.split(','); os.makedirs(out, exist_ok=True)
    opt = st.sim_rl(); rng = np.random.default_rng(2)
    J = [np.hstack([rng.normal(0, 0.0005, 3), rng.normal(0, 0.005, 3)]) for _ in range(16 * 4)]
    for e in eps:
        t0 = time.time(); x = P[e]; res = dict(ep=int(e), mode=x['mode'], source_run=x['source_run'], lib=x['lib'],
                                               pieces=x['pieces'], md5_listed=x['md5'])
        try:
            ref = None
            for rt in roots:
                for cand in (f"{rt}/runs/{x['source_run']}/{x['reference']}",
                             f"{rt}/runs/{x['source_run']}/{x['reference']}".replace('perc2mcks', 'perc2mck')):
                    if os.path.exists(cand):
                        ref = cand; break
                if ref:
                    break
            assert ref, 'reference not downloaded'
            root = ref.split('/runs/')[0]; R = rb.load_ref(ref); names = R['names']
            res.update(ref=ref.split('/runs/')[1], ref_md5=R['md5'], md5_match=R['md5'] == x['md5'], names=names)
            rd = os.path.dirname(ref).split('/processed/')[0]           # perc2mcks copies keep their stage in perc2mck
            usda = sorted(glob.glob(os.path.join(rd, 'reconstructed_stage', '*.usda')) +
                          glob.glob(os.path.join(rd.replace('/perc2mcks/', '/perc2mck/'), 'reconstructed_stage', '*.usda')))
            assert usda, 'no support usda'
            sup = rb.support(usda[0]); top = sup['top_z']; res['support'] = dict(top_z=top, md5=sup['md5'], radius=sup['radius'])
            shared = None
            objs = []
            for n, up in zip(names, R['urdf_paths']):
                if up.startswith('/content/refs/'):
                    u = f"{root}/runs/{x['source_run']}/{up[len('/content/'):]}"
                else:
                    if shared is None:
                        shared = f'{work}/shared/ep{e}'; lib = f'{work}/shared/lib{e}'
                        shutil.rmtree(shared, ignore_errors=True); shutil.rmtree(lib, ignore_errors=True); os.makedirs(lib)
                        for m in names:
                            shutil.copy(f'/home/user/v2d-track3/meshes/{x["lib"]}/{m}.glb', lib)
                        pc = PIECES.get(e)
                        pdir = (f'{fp}/../{pc}' if e == '1' else f'/home/user/v2d-track3/{pc}') if pc else None
                        if os.environ.get('F0_PIECES'):                    # a candidate folder instead of the packed one
                            pdir = pc = os.environ['F0_PIECES']
                        cmd = [sys.executable, '-I', f'{fp}/make_assets.py', lib, shared] + (['--pieces', pdir] if pdir else [])
                        r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr[-400:]
                        res['shared_assets'] = dict(lib=x['lib'], pieces=pc, make_assets=r.stdout.strip().splitlines())
                    u = f"{shared}/urdf/{os.path.basename(up)}"
                assert os.path.exists(u), u
                cols, vis = collisions(u)
                hulls, src = [], []
                for c in cols:
                    if c.endswith('.glb'):
                        z = np.load(coacd_npz(c, coacd_t, f'{work}/coacd_cache'))
                        hulls += [np.asarray(z[f'v{i}'], float) for i in range(int(z['n']))]; src.append(f'{os.path.basename(c)} {md5(c)[:8]} -> CoACD {int(z["n"])}')
                    else:
                        hulls.append(np.asarray(trimesh.load(c, force='mesh').vertices, float))
                if any(not c.endswith('.glb') for c in cols):
                    src.append(f'{sum(not c.endswith(".glb") for c in cols)} piece files')
                vm = rb.load_mesh(vis)
                objs.append(dict(name=n, urdf=u, urdf_md5=md5(u), hulls=hulls, src=src, ine=st.urdf_inertial(u),
                                 tree=__import__('scipy.spatial', fromlist=['cKDTree']).cKDTree(
                                     trimesh.sample.sample_surface_even(vm, int(np.ceil(vm.area / 0.002 ** 2)), seed=0)[0]),
                                 V=np.vstack(hulls), H=rb.Hulls(hulls)))
            # frames
            nf = R['nf']; T = R['T']
            hand = np.array([[o['tree'].query(rb.tf(np.linalg.inv(T[f, j]), R['hands'][f]))[0].min() for j, o in enumerate(objs)]
                             for f in range(nf)])
            disp = np.array([[np.linalg.norm(rb.tf(T[f, j], o['V']) - rb.tf(T[max(f - 1, 0) if f else 1, j], o['V']), axis=1).max()
                              for j, o in enumerate(objs)] for f in range(nf)])
            ok = (hand >= rb.HAND_M).all(1) & (disp < rb.STATIC_M).all(1)
            rr = rb.runs(ok); frames = [0]
            first = rr[0][0] if rr else None
            if (hand[0] < rb.HAND_M).any() and first is not None and first != 0:
                frames.append(int(first))
            first_obj = {}                                              # per object held at f0: its own first H30 rest run
            for j, o in enumerate(objs):
                if hand[0, j] < rb.HAND_M:
                    rj = rb.runs((hand[:, j] >= rb.HAND_M) & (disp[:, j] < rb.STATIC_M))
                    first_obj[o['name']] = int(rj[0][0]) if rj else None
                    if rj and rj[0][0] not in frames:
                        frames.append(int(rj[0][0]))
            res['first_H30_rest_frame_per_object'] = first_obj
            if os.environ.get('F0_ALWAYS_FIRST') == '1' and first is not None and first not in frames:
                frames.append(int(first))                                # report the first all-object H30 rest run anyway
            for xf in [int(v) for v in os.environ.get('F0_EXTRA', '').split(',') if v]:
                if xf not in frames:
                    frames.append(xf)
            res['f0_hand_mm'] = {o['name']: round(float(min(hand[0, j], 9.99)) * 1e3, 1) for j, o in enumerate(objs)}
            res['first_H30_rest_frame'] = first
            res['objects'] = {o['name']: dict(urdf_md5=o['urdf_md5'], pieces=len(o['hulls']), collision=o['src'],
                                              mass=o['ine']['mass']) for o in objs}
            grids = {o['name']: rb.solid_grid(o['hulls']) for o in objs} if len(objs) > 1 else {}
            res['frames'] = []
            for f in frames:
                fd = dict(frame=int(f), kind='start' if f == 0 else ('first H30 rest (all objects)' if f == first else ('first H30 rest of ' + ', '.join(n for n, v in first_obj.items() if v == f) if f in first_obj.values() else 'requested')), hand_mm={}, objects={}, pairs={})
                for j, o in enumerate(objs):
                    W = rb.tf(T[f, j], o['V']); low = W[:, 2].min(); com = rb.tf(T[f, j], np.array([o['ine']['com']]))[0]
                    sup_ = {}
                    for b in (0.001, 0.003):
                        band = W[W[:, 2] < low + b]
                        mg = None
                        if len(band) >= 3:
                            try:
                                h = ConvexHull(band[:, :2]); mg = float(-(h.equations[:, :2] @ com[:2] + h.equations[:, 2]).max() * 1e3)
                            except Exception:
                                mg = None
                        sup_[f'band{int(b * 1e3)}mm'] = dict(points=int(len(band)), com_margin_mm=None if mg is None else round(mg, 1))
                    near = []
                    for k, q in enumerate(objs):
                        if k == j:
                            continue
                        X = rb.tf(np.linalg.inv(T[f, k]) @ T[f, j], o['V'])
                        near.append(float(q['tree'].query(X)[0].min()))
                    fd['objects'][o['name']] = dict(pen_mm=round((top - low) * 1e3, 2), com_height_mm=round((com[2] - top) * 1e3, 1),
                                                    hand_mm=round(float(min(hand[f, j], 9.99)) * 1e3, 1), support=sup_,
                                                    min_dist_to_partner_mesh_mm=round(min(near) * 1e3, 1) if near else None)
                for j in range(len(objs)):
                    for k in range(j + 1, len(objs)):
                        a, b_ = objs[j], objs[k]; v = []
                        for g, h_, Tg, Th in ((a, b_, T[f, j], T[f, k]), (b_, a, T[f, k], T[f, j])):
                            X = rb.tf(np.linalg.inv(Th) @ Tg, grids[g['name']]); X = X[np.all((X > h_['H'].LO) & (X < h_['H'].HI), 1)]
                            v.append(float((h_['H'].depth(X) >= 0).sum()) * rb.PITCH_OV ** 3 * 1e6 if len(X) else 0.0)
                        fd['pairs'][f"{a['name']}|{b_['name']}"] = round(max(v), 2)
                spec = [(o['name'], o['hulls'], o['ine']) for o in objs]; T0 = [T[f, j] for j in range(len(objs))]
                g = st.run(st.xml(spec, T0, top, opt), opt, len(objs))
                cps = []
                for c in range(16):
                    T1 = []
                    for j in range(len(objs)):
                        jj = J[c * 4 + j]; Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(jj[3:]).as_matrix(); Jm[:3, 3] = jj[:3]
                        T1.append(T0[j] @ Jm)
                    cps.append(st.run(st.xml(spec, T1, top, opt), opt, len(objs)))
                for j, o in enumerate(objs):
                    d = fd['objects'][o['name']]
                    fm = [c['final_mm'][j] for c in cps if not c['nan']]; fr_ = [c['final_deg'][j] for c in cps if not c['nan']]
                    d.update(settle_mm=g['final_mm'][j], settle_deg=g['final_deg'][j], max_mm=g['max_mm'][j], max_deg=g['max_deg'][j],
                             falls_over=bool(g['final_deg'][j] is not None and g['final_deg'][j] >= FALL_DEG),
                             moved=bool(g['final_mm'][j] is None or g['final_mm'][j] > MOVE_MM or g['final_deg'][j] > MOVE_DEG),
                             jitter16=dict(mm=rb.stats(fm), deg=rb.stats(fr_), falls=int(sum(x >= FALL_DEG for x in fr_)),
                                           nan=int(sum(c['nan'] for c in cps))))
                    cause = []
                    if d['hand_mm'] < 30:
                        cause.append(f"held at f{f} (hand {d['hand_mm']} mm)")
                    if d['pen_mm'] > 2:
                        cause.append(f"in the table {d['pen_mm']} mm")
                    if -d['pen_mm'] > FLOAT_M * 1e3 and (d['min_dist_to_partner_mesh_mm'] is None or d['min_dist_to_partner_mesh_mm'] > 4):
                        cause.append(f"floating {-d['pen_mm']} mm above the table")
                    for pk, pv in fd['pairs'].items():
                        if o['name'] in pk.split('|') and pv >= OV_CM3:
                            cause.append(f"overlap {pv} cm3 with {[n for n in pk.split('|') if n != o['name']][0]}")
                    s1, s3 = d['support']['band1mm'], d['support']['band3mm']
                    if -d['pen_mm'] <= FLOAT_M * 1e3:
                        if s1['com_margin_mm'] is None or s1['com_margin_mm'] < 0:
                            if s3['com_margin_mm'] is not None and s3['com_margin_mm'] > 0:
                                cause.append(f"hull corner below the support ({s1['points']} pts within 1 mm, COM {s1['com_margin_mm']} mm; "
                                             f"within 3 mm COM {s3['com_margin_mm']} mm inside)")
                            else:
                                cause.append(f"COM outside the footprint (1 mm band {s1['com_margin_mm']} mm, 3 mm band {s3['com_margin_mm']} mm)")
                    d['likely_cause'] = cause if d['moved'] else []
                    d['flags'] = cause
                res['frames'].append(fd)
            res['status'] = 'ok'
        except Exception as ex:
            res['status'] = f'not reconstructed: {type(ex).__name__}: {str(ex)[:300]}'
        res['secs'] = round(time.time() - t0, 1)
        json.dump(res, open(f'{out}/ep{e}.json', 'w'), indent=1, default=float)
        brief = {fd['frame']: {n: (o['settle_mm'], o['settle_deg'], o['falls_over'], o['likely_cause']) for n, o in fd['objects'].items()}
                 for fd in res.get('frames', [])}
        print(f"ep{e} {res['status']} {res['secs']} s {brief}", flush=True)


if __name__ == '__main__':
    main()
