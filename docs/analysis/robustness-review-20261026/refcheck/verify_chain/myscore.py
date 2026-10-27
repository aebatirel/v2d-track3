"""Independent re-implementation of the registered Track 3 ADD-AUC (refcheck/verify_chain, 27 Oct 2026).

EVALUATION ONLY (reads public mocap). Written to check refcheck/chain without re-running its scripts or
pipeline/score_registered.py. Own code: reading the GT parquet (w-first quaternion), perception npz, FlashCHORD
reference parquets (object_body_position / object_body_wxyz) and evaluator results parquets (raw columns), the host
stand-in (scan surface centroid, PCA symmetry axis), the pose conversion to the hidden anchor, the frame-0 scene
alignment, the symmetric ADD and the AUC -- all with rotation matrices, not the kit's quaternion helpers.
Kit code used (it IS the official procedure, so re-writing it would only add risk): v2dlb.mesh_budget.budget_mesh
(packer decimation), v2dlb.track3_pose._register_object_body (the scorer's registration), and
v2dlb.mesh_common._sample_mesh_surface for the host points (same seeds as score_registered.py, so the stand-in host is
the same); --alt_points replaces the latter with trimesh's sampler and another count, to test sampling sensitivity.

Usage: python -I myscore.py EP OUT.json --src NAME=KIND:PATH [...] [--modes lib,scan,ours:<obj>,...]
         [--lib DIR] [--alt_points N] [--pf OUT.npz]
  KIND: npz (poses_world_vo.npz, 4x4 per object), refpq (FlashCHORD reference parquet), res (evaluator results dir
        holding episode_XXXXXX.parquet: gives NAME_sim and NAME_ref)
  modes: lib = all objects our meshes; scan = all public scans; ours:<obj> = only <obj> ours, the rest scans.
"""
import argparse, json, os, sys, time
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
KIT = f'{SP}/kit/v2d_submission_kit'
T3 = f'{SP}/t3'
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh                      # noqa: E402
from v2dlb.track3_pose import _register_object_body            # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface             # noqa: E402

SYM_ORDER = {'blue_cup': 360, 'beige_cup': 360, 'white_pot_lid': 2}
THR = np.arange(1, 10) / 100.0


def scan_file(n):
    q = f'{T3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb'


def area_centroid(v, f):
    tri = v[f]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    k = a > 1e-12
    return (tri[k].mean(1) * a[k, None]).sum(0) / a[k].sum()


def load_gt(ep):
    tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects', 'frame_index']).to_pandas()
    assert (tab.frame_index.values == np.arange(len(tab))).all(), 'GT frame_index not 0..N-1'
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    T, B = len(tab), len(names)
    pos, rot = np.zeros((T, B, 3)), np.zeros((T, B, 3, 3))
    for t, objs in enumerate(tab['observation.objects']):
        d = {str(o['name']): np.asarray(o['pose'], float) for o in objs}
        for b, n in enumerate(names):
            p = d[n]
            pos[t, b] = p[:3]
            rot[t, b] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()   # parquet: x y z qw qx qy qz
    return names, pos, rot


def load_src(kind, path, names, T):
    if kind == 'npz':
        P = np.load(path)
        M = np.stack([P[n] for n in names], 1)                                 # T,B,4,4
        assert len(M) == T, (path, len(M), T)
        return {'': (M[:, :, :3, 3].copy(), M[:, :, :3, :3].copy())}
    if kind == 'refpq':
        t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
        bn = t.column('object_body_names')[0].as_py()
        pos = np.array(t.column('object_body_position')[0].as_py(), float)
        q = np.array(t.column('object_body_wxyz')[0].as_py(), float)
        q /= np.linalg.norm(q, axis=-1, keepdims=True)
        idx = [bn.index(n) for n in names]
        pos, q = pos[:, idx], q[:, idx]
        assert len(pos) == T, (path, len(pos), T)
        rot = Rot.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(len(pos), len(names), 3, 3)
        return {'': (pos, rot)}
    if kind == 'res':
        f = [x for x in os.listdir(path) if x.startswith('episode_') and x.endswith('.parquet')][0]
        tb = pq.read_table(os.path.join(path, f))
        md = {k.decode(): v.decode() for k, v in (tb.schema.metadata or {}).items()}
        assert md.get('flash_chord.quaternion_order', 'xyzw') == 'xyzw', md
        d = tb.to_pandas()
        d = d[d.environment_id == d.environment_id.min()]
        frames = np.sort(d.reference_frame.unique())
        out = {}
        for pre, tag in (('achieved', '_sim'), ('reference', '_ref')):
            pos = np.full((len(frames), len(names), 3), np.nan); rot = np.full((len(frames), len(names), 3, 3), np.nan)
            fi = np.searchsorted(frames, d.reference_frame.values)
            sl = d.object_body_id.values
            assert all(d.object_body_name.values[i] == names[sl[i]] for i in range(len(d))), 'slot/name mismatch'
            P = d[[f'{pre}_position_{c}' for c in 'xyz']].values
            Q = d[[f'{pre}_quaternion_{c}' for c in 'xyzw']].values
            pos[fi, sl] = P
            rot[fi, sl] = Rot.from_quat(Q / np.linalg.norm(Q, axis=1, keepdims=True)).as_matrix()
            assert not np.isnan(pos).any()
            out[tag] = (pos, rot, frames)
        return out
    raise SystemExit(kind)


def axial_rots(axis, order):
    ang = np.arange(order) * 2 * np.pi / order
    return Rot.from_rotvec(ang[:, None] * axis[None]).as_matrix()


def sym_add(pa, Ra, pr, Rr, X, axis, order):
    """mean point distance (m), min over symmetry rotations S about axis (through the anchor), per frame"""
    moved = np.einsum('tij,nj->tni', Ra, X) + pa[:, None]
    Ss = axial_rots(axis, order) if order else np.eye(3)[None]
    best = np.full(len(pa), np.inf)
    for S in Ss:
        tgt = np.einsum('tij,nj->tni', Rr, X @ S.T) + pr[:, None]
        best = np.minimum(best, np.linalg.norm(moved - tgt, axis=-1).mean(-1))
    return best


def auc(add):
    frac = np.array([(add < t).mean() for t in THR])
    return float(np.trapezoid(frac, x=np.linspace(0, 1, len(THR))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep', type=int); ap.add_argument('out')
    ap.add_argument('--src', action='append', required=True)
    ap.add_argument('--modes', default='lib,scan')
    ap.add_argument('--lib', default='/home/user/v2d-track3/meshes/library_v3')
    ap.add_argument('--alt_points', type=int, default=0)
    ap.add_argument('--pf', default=None)
    ap.add_argument('--tshift', default='', help='comma-separated frame shifts k: score path[t + k] vs mocap[t] '
                    'after aligning the unshifted path at frame 0 (frame-indexing test)')
    ap.add_argument('--seed_offset', type=int, default=0, help='added to the kit registration seed (sensitivity test; 0 = the kit seed)')
    a = ap.parse_args()
    t0 = time.time()
    names, gpos, grot = load_gt(a.ep)
    T, B = gpos.shape[:2]
    # host stand-in
    H = []
    for s, n in enumerate(names):
        m = trimesh.load(scan_file(n), force='mesh')
        v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
        c = area_centroid(v, f)
        if a.alt_points:
            X = trimesh.sample.sample_surface(trimesh.Trimesh(v, f, process=False), a.alt_points, seed=12345 + s)[0] - c
        else:
            X = _sample_mesh_surface(v, f, 1000, 7 + s) - c
        Xa = _sample_mesh_surface(v, f, 1000, 7 + s) - c            # axis always from the kit-seed sample
        order = SYM_ORDER.get(n, 0); axis = np.zeros(3)
        if order:
            w, U = np.linalg.eigh(np.cov(Xa.T))
            k = 0 if order == 2 else int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis = U[:, k]
        H.append(dict(v=v, f=f, c=c, X=X, axis=axis, order=order))
    # registrations (cached per mesh kind)
    reg = {}
    def get_reg(s, kind):
        if (s, kind) not in reg:
            n = names[s]
            cand = budget_mesh(scan_file(n) if kind == 'scan' else f'{a.lib}/{n}.glb', 4096, 4096)
            reg[(s, kind)] = _register_object_body(cand, (H[s]['v'], H[s]['f']), H[s]['c'], 1_000_003 * a.ep + 101 * s + a.seed_offset)
        return reg[(s, kind)]
    # sources
    S = {}
    for spec in a.src:
        nm, rest = spec.split('=', 1); kind, path = rest.split(':', 1)
        for tag, val in load_src(kind, path, names, T).items():
            S[nm + tag] = val
    res = dict(ep=a.ep, objects=names, frames=T, lib=a.lib, alt_points=a.alt_points, seed_offset=a.seed_offset, sources={k: v for k, v in
               (s.split('=', 1) for s in a.src)}, scores={}, registration={})
    PF = {}
    for mode in a.modes.split(','):
        kinds = ['ours' if (mode == 'lib' or mode == f'ours:{n}') else 'scan' for n in names]
        regs = [get_reg(s, 'lib' if k == 'ours' else 'scan') for s, k in enumerate(kinds)]
        res['registration'][mode] = {n: dict(kind=kinds[s], rot_deg=round(float(np.degrees(Rot.from_matrix(regs[s][1]).magnitude())), 3),
                                             anchor_shift_cm=round(float(np.linalg.norm(regs[s][0] - H[s]['c']) * 100), 3))
                                     for s, n in enumerate(names)}
        for sn, val in S.items():
            pos, rot = val[0], val[1]
            fr = val[2] if len(val) > 2 else np.arange(T)
            gp, gr = gpos[fr], grot[fr]
            # convert to the hidden anchor / scan axes
            ap_ = np.stack([pos[:, s] + np.einsum('tij,j->ti', rot[:, s], regs[s][0]) for s in range(B)], 1)
            ar_ = np.stack([np.einsum('tij,kj->tik', rot[:, s], regs[s][1]) for s in range(B)], 1)    # R @ Rb^T
            rp = np.stack([gp[:, s] + np.einsum('tij,j->ti', gr[:, s], H[s]['c']) for s in range(B)], 1)
            # frame-0 scene alignment
            fixed = [s for s in range(B) if not H[s]['order']]
            if fixed or B == 1:
                k = fixed[0] if fixed else 0
                Ral = gr[0, k] @ ar_[0, k].T
            else:
                def basis(ax, d):
                    p = d - ax * (ax @ d); p /= np.linalg.norm(p)
                    return np.column_stack((p, np.cross(ax, p), ax))
                ax_r = gr[0, 0] @ H[0]['axis']; ax_a = ar_[0, 0] @ H[0]['axis']
                Ral = basis(ax_r, rp[0, 1] - rp[0, 0]) @ basis(ax_a, ap_[0, 1] - ap_[0, 0]).T
            off = rp[0, 0] - Ral @ ap_[0, 0]
            alp = ap_ @ Ral.T + off
            alr = np.einsum('ij,tbjk->tbik', Ral, ar_)
            for ks in ([0] if not a.tshift else [int(x) for x in a.tshift.split(',')]):
                # timing test: path frame t + ks against mocap row t, AFTER the frame-0 alignment of the unshifted path
                ix = np.clip(np.arange(len(fr)) + ks, 0, len(fr) - 1)
                per, adds, dz = {}, [], {}
                for s, n in enumerate(names):
                    add = sym_add(alp[ix, s], alr[ix, s], rp[:, s], gr[:, s], H[s]['X'], H[s]['axis'], H[s]['order'])
                    adds.append(add); per[n] = round(auc(add), 4)
                    dz[n] = round(float((alp[ix, s, 2] - rp[:, s, 2]).mean() * 100), 3)
                key = f'{mode}|{sn}' + (f'@{ks:+d}' if a.tshift else '')
                res['scores'][key] = dict(scene=round(float(np.mean(list(per.values()))), 4), per_obj=per,
                                          dz_err_cm=dz, n_frames=int(len(fr)))
                PF[key] = np.stack(adds, 1)
    res['sec'] = round(time.time() - t0, 1)
    json.dump(res, open(a.out, 'w'), indent=1)
    if a.pf:
        np.savez(a.pf, **{k.replace('|', '__').replace(':', '-'): v for k, v in PF.items()})
    for k, v in res['scores'].items():
        print(k, v['scene'], v['per_obj'], v['dz_err_cm'])
    print('sec', res['sec'])


if __name__ == '__main__':
    main()
