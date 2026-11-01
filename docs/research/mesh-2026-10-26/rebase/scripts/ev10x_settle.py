"""Eval-10 cup pieces at chosen frames (orchestrator request 1 Nov ~07:00 UTC; REPORT ONLY, informs the reading of
the running ev10cs5 retrain). Same scene as f0_survey.py / settle.py (plain MuJoCo, sim=rl options, every object free, no
hands, table plane at the support usda top, URDF mass / COM / inertia, 2.0 s, exact pose + 16 copies jittered 0.5 mm /
0.005 rad, seed 2). Per object: absolute translation / rotation at 2 s; for the pair, the beige cup's pose relative to
the blue cup (the nest) at 2 s against the reference's relative pose. Frames: f0, each object's first H30 rest frame
(first frame of its first run of >= 5 frames with no hand point within 30 mm and < 2 mm motion per frame), the first
frame where both are, and any extra frames given.
  python -I ev10x_settle.py REF.parquet USDA OUT.json EXTRA_FRAMES(comma) NAME=ASSET_URDF_DIR [NAME=...]
ASSET_URDF_DIR: a make_assets.py output (urdf/ + mesh/) built with the variant's --pieces folder."""
import json
import os
import re
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebase as rb  # noqa: E402
import settle as st  # noqa: E402

ref, usda, outp, extra = sys.argv[1:5]; variants = dict(a.split('=', 1) for a in sys.argv[5:])
R = rb.load_ref(ref); names = R['names']; T = R['T']; nf = R['nf']; top = rb.support(usda)['top_z']; opt = st.sim_rl()
rng = np.random.default_rng(2)
J = [np.hstack([rng.normal(0, 0.0005, 3), rng.normal(0, 0.005, 3)]) for _ in range(16 * 4)]


def load(adir, n):
    u = f'{adir}/urdf/{n}_rigid.urdf'; s = open(u).read(); d = os.path.dirname(u)
    cols = [os.path.normpath(os.path.join(d, f)) for f in re.findall(r'<collision>.*?<mesh filename="([^"]*)"', s, re.S)]
    vis = os.path.normpath(os.path.join(d, re.search(r'<visual>.*?<mesh filename="([^"]*)"', s, re.S).group(1)))
    hulls, src = [], []
    for c in cols:                                                  # glb -> FlashCHORD's CoACD (f0_survey.coacd_npz)
        if c.endswith('.glb'):
            import f0_survey
            z = np.load(f0_survey.coacd_npz(c, os.environ['COACD1011'], os.environ['COACD_CACHE']))
            hulls += [np.asarray(z[f'v{i}'], float) for i in range(int(z['n']))]; src.append(f'{os.path.basename(c)} {rb.md5(c)[:8]} -> CoACD {int(z["n"])}')
        else:
            hulls.append(np.asarray(trimesh.load(c, force='mesh').vertices, float)); src.append(os.path.basename(c))
    return dict(hulls=hulls, ine=st.urdf_inertial(u), vis=vis, urdf_md5=rb.md5(u), src=src, vis_md5=rb.md5(vis))


def run(spec, T0):
    import mujoco
    m = mujoco.MjModel.from_xml_string(st.xml(spec, T0, top, opt)); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    n = len(spec); p0 = d.xpos[1:n + 1].copy(); q0 = d.xquat[1:n + 1].copy(); me = 0
    for _ in range(int(round(st.SECS / opt['timestep']))):
        mujoco.mj_step(m, d); me = max(me, int(d.nefc))
        if not np.all(np.isfinite(d.qpos)):
            return None
    M = lambda p, q: np.r_[np.c_[Rot.from_quat(q[[1, 2, 3, 0]]).as_matrix(), p], [[0, 0, 0, 1]]]
    A0 = [M(p0[i], q0[i]) for i in range(n)]; A1 = [M(d.xpos[i + 1], d.xquat[i + 1]) for i in range(n)]
    ang = lambda Ra: float(np.degrees(Rot.from_matrix(Ra).magnitude()))
    out = dict(abs=[(float(np.linalg.norm(A1[i][:3, 3] - A0[i][:3, 3]) * 1e3), ang(A1[i][:3, :3] @ A0[i][:3, :3].T)) for i in range(n)],
               max_nefc=me)
    if n == 2:
        r0 = np.linalg.inv(A0[0]) @ A0[1]; r1 = np.linalg.inv(A1[0]) @ A1[1]
        out['rel'] = (float(np.linalg.norm(r1[:3, 3] - r0[:3, 3]) * 1e3), ang(r1[:3, :3] @ r0[:3, :3].T))
    return out


res = dict(ref=ref, ref_md5=R['md5'], names=names, support_top=top, variants={})
first_done = None
for v, adir in variants.items():
    O = [load(adir, n) for n in names]
    if first_done is None:                                         # frames from the visual meshes (same in every variant)
        trees = []
        for o in O:
            vm = rb.load_mesh(o['vis']); trees.append(cKDTree(trimesh.sample.sample_surface_even(vm, int(np.ceil(vm.area / 4e-6)), seed=0)[0]))
        hand = np.array([[trees[j].query(rb.tf(np.linalg.inv(T[f, j]), R['hands'][f]))[0].min() for j in range(len(names))] for f in range(nf)])
        V = [np.vstack(o['hulls']) for o in O]
        disp = np.array([[np.linalg.norm(rb.tf(T[f, j], V[j]) - rb.tf(T[f - 1 if f else 1, j], V[j]), axis=1).max() for j in range(len(names))]
                         for f in range(nf)])
        fr = {'f0': 0}
        for j, n in enumerate(names):
            rr = rb.runs((hand[:, j] >= rb.HAND_M) & (disp[:, j] < rb.STATIC_M)); fr[f'first H30 rest, {n}'] = rr[0][0] if rr else None
        rr = rb.runs((hand >= rb.HAND_M).all(1) & (disp < rb.STATIC_M).all(1)); fr['first H30 rest, both'] = rr[0][0] if rr else None
        for x in [int(s) for s in extra.split(',') if s]:
            fr[f'f{x} (requested)'] = x
        res['frames'] = fr; res['hand_mm'] = {k: [round(float(min(hand[f, j], 9.99)) * 1e3, 1) for j in range(len(names))]
                                              for k, f in fr.items() if f is not None}
        first_done = True
    spec = [(n, o['hulls'], o['ine']) for n, o in zip(names, O)]
    rv = dict(pieces={n: len(o['hulls']) for n, o in zip(names, O)}, urdf_md5={n: o['urdf_md5'] for n, o in zip(names, O)},
              collision={n: o['src'] for n, o in zip(names, O)}, visual_md5={n: o['vis_md5'] for n, o in zip(names, O)}, frames={})
    for k, f in res['frames'].items():
        if f is None:
            rv['frames'][k] = None; continue
        T0 = [T[f, j] for j in range(len(names))]; ex = run(spec, T0); cp = []
        for c in range(16):
            T1 = []
            for j in range(len(names)):
                jj = J[c * 4 + j]; Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(jj[3:]).as_matrix(); Jm[:3, 3] = jj[:3]; T1.append(T0[j] @ Jm)
            cp.append(run(spec, T1))
        ok = [c for c in cp if c is not None]
        rv['frames'][k] = dict(frame=int(f), exact=ex, jitter=dict(
            nan=16 - len(ok),
            abs={n: dict(mm=rb.stats([c['abs'][j][0] for c in ok]), deg=rb.stats([c['abs'][j][1] for c in ok]),
                         falls=int(sum(c['abs'][j][1] >= 30 for c in ok))) for j, n in enumerate(names)},
            rel=dict(mm=rb.stats([c['rel'][0] for c in ok]), deg=rb.stats([c['rel'][1] for c in ok])) if len(names) == 2 else None,
            max_nefc=max(c['max_nefc'] for c in ok)))
        e = ex or {}
        print(v, k, f, 'abs', [tuple(round(x, 2) for x in a) for a in e.get('abs', [])], 'rel', tuple(round(x, 2) for x in e.get('rel', ())),
              'jit abs mm max', [rv['frames'][k]['jitter']['abs'][n]['mm']['max'] for n in names],
              'deg max', [rv['frames'][k]['jitter']['abs'][n]['deg']['max'] for n in names],
              'rel max', (rv['frames'][k]['jitter']['rel'] or {}).get('mm', {}).get('max'), flush=True)
    res['variants'][v] = rv
json.dump(res, open(outp, 'w'), indent=1, default=float)
