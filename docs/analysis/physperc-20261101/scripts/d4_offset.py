"""D4 (DIAGNOSTIC / ORACLE, reads public mocap): decompose the constant per-object offset that the scorer sees.
Replicates pipeline/score_registered.py's score() (kit registration, conversion, alignment) and, per object, the
mean residual r = mean_t(ref - ach) of the kit anchor position in the aligned (mocap) frame, split into
  vertical (mocap z), along the camera ray at f0 (our camera centre = world origin, mapped by the alignment), lateral.
Oracle AUC of removing (full | vertical | ray | lateral) offsets, all objects. Usage: d4_offset.py SCRATCH TRACKS OUT"""
import sys, json, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
S, TR, OUT = sys.argv[1:4]
sys.path.insert(0, f'{S}/kit/v2d_submission_kit')
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
import trimesh
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def scan_path(n):
    import os
    q = f'{S}/t3/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{S}/t3/mesh/{n}/{n}_visual.glb'


def load_vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


res = {}
for e in EPS:
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet').to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)
    H = []
    for s, n in enumerate(names):
        v, f = load_vf(scan_path(n)); c, _ = _surface_moments(v, f)
        pts = _sample_mesh_surface(v, f, 1000, 7 + s) - c
        axis, order = np.zeros(3), 0
        if n in SYM:
            w, U = np.linalg.eigh(np.cov(pts.T))
            if SYM[n] == 'half':
                axis, order = U[:, 0], 2
            else:
                k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
        H.append(dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order))
    REG = [T3._register_object_body(budget_mesh(f'{S}/mesh9a/{n}.glb', 4096, 4096), H[s]['mesh'], H[s]['anchor'],
                                    1_000_003 * e + 101 * s) for s, n in enumerate(names)]
    P = np.load(f'{TR}/ep{e}/poses_world_vo.npz'); T = len(P[names[0]])
    ach0 = np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()] for n in names] for i in range(T)])
    gt = np.stack([[np.r_[q[:3], q[4:7], q[3]] for q in [np.array([o for o in tab['observation.objects'].iloc[fr]
                    if o['name'] == n][0]['pose'], float) for n in names]] for fr in range(T)])
    ach = ach0[:, None].copy(); ref = gt[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    cam = ach[:1, :, :1].copy(); cam[..., :3] = 0.0; cam[..., 3:] = [0, 0, 0, 1]   # camera centre at f0
    al = T3._align_registered_scene(ach, ref, axes)
    # alignment as a map: apply the same transform to the camera centre
    tmp = np.concatenate([ach, np.repeat(cam, len(ach), 0)], 2)
    alc = T3._align_registered_scene(tmp, np.concatenate([ref, np.repeat(ref[:, :, :1], 1, 2)], 2), axes + [np.zeros(3)])
    C0 = alc[0, 0, -1, :3]
    def auc(a):
        return float(T3._registered_pose_metric('add_auc', a, ref, pts, axes, orders))
    base = auc(al)
    out = dict(objects=names, base=round(base, 4), obj={})
    arms = {k: al.copy() for k in ('full', 'vert', 'ray', 'lat')}
    for s, n in enumerate(names):
        r = (ref[:, 0, s, :3] - al[:, 0, s, :3]).mean(0)
        ray = al[0, 0, s, :3] - C0; ray /= np.linalg.norm(ray)
        z = np.array([0, 0, 1.0])
        rv = (r @ z) * z
        rr = (r @ ray) * ray
        rl = r - rr
        out['obj'][n] = dict(off_mm=np.round(r * 1000, 1).tolist(), norm_mm=round(float(np.linalg.norm(r) * 1000), 1),
                             vert_mm=round(float(r @ z * 1000), 1), ray_mm=round(float(r @ ray * 1000), 1),
                             lat_mm=round(float(np.linalg.norm(rl) * 1000), 1), ray_dot_z=round(float(ray @ z), 3))
        arms['full'][:, 0, s, :3] += r; arms['vert'][:, 0, s, :3] += rv
        arms['ray'][:, 0, s, :3] += rr; arms['lat'][:, 0, s, :3] += rl
    out['oracle_dAUC'] = {k: round(auc(v) - base, 4) for k, v in arms.items()}
    res[e] = out
    print(e, out['base'], out['oracle_dAUC'], {n: (o['norm_mm'], o['vert_mm'], o['ray_mm'], o['lat_mm']) for n, o in out['obj'].items()}, flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
m = {k: round(float(np.mean([r['oracle_dAUC'][k] for r in res.values()])), 4) for k in ('full', 'vert', 'ray', 'lat')}
print('MEAN oracle dAUC', m)
