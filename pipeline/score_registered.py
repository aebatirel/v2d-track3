"""Official-style REGISTERED Track 3 scoring of a public episode (evaluation only, after inference).

The current kit's five pose scorers (metric_code/track_3/*.py, `_score_registered_track3`) first register the
submitted mesh of each object to the confidential scan, move the poses to the scan's hidden anchor point, align the
scene once at frame 0 (on the first object without a symmetry axis, else on object 0's axis and the direction to
object 1), and score with the declared symmetries (cups: any spin about the central axis; lid: 0/180 deg about its
normal). This script calls the kit's own functions (v2dlb.track3_pose) with a STAND-IN for the hidden geometry:
  scan    = the public scan (D/mesh/<obj>/<obj>.glb), the confidential one is assumed to match it;
  anchor  = the scan's surface centroid (guess; the host's anchor is not published);
  points  = 1000 scan surface samples about the anchor (the host's count is not published);
  axis    = cups: the scan's distinct principal axis (order 360); lid: its thinnest principal axis (order 2);
            everything else: none (full orientation scored).
Candidate meshes default to the public scans (registration ~ identity, i.e. the upper bound); pass --meshes DIR
(DIR/<obj>.glb or DIR/episode_XXXXXX/<obj>.glb) to score with our reconstructions, decimated with the packer's
budget_mesh (4096 faces / 4096 vertices), so the registration error of a reconstruction is part of the score.

Usage: python score_registered.py EP SOURCE [--meshes DIR] [--t3 /content/t3] [--kit KIT] [--out JSON]
  SOURCE = an evaluator results dir (episode_XXXXXX.parquet; scores the rollout, its reference and the floor) or a
           perception poses_world_vo.npz (4x4 per object name; scores the perception trajectory).
"""
import argparse, json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('ep', type=int)
p.add_argument('source')
p.add_argument('--meshes', default=None)
p.add_argument('--t3', default='/content/t3')
p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
p.add_argument('--out', default=None)
p.add_argument('--n_points', type=int, default=1000)
p.add_argument('--per_frame', help='also save per-frame, per-object position error (cm), plain ADD (cm) and the '
               'symmetric ADD used by the AUC (<src>_adds_cm: cups any spin, lid 180 deg) after the alignment')
a = p.parse_args()
sys.path.insert(0, a.kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
METRICS = [('AUC', 'add_auc'), ('SP_SR', 'spider_sr'), ('MP_SR', 'maniptrans_sr'), ('MPPE_cm', 'mppe_cm'),
           ('RPE_cm', 'rpe_cm')]


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def host_geometry(n, slot):
    v, f = load_vf(scan_path(n))
    c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, a.n_points, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))                           # ascending eigenvalues
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2                                   # thinnest direction = lid normal
        else:                                                          # cylinder: the eigenvalue unlike the other two
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


def candidate_mesh(n):
    if a.meshes is None:
        return budget_mesh(scan_path(n), 4096, 4096)
    for q in (f'{a.meshes}/episode_{a.ep:06d}/{n}.glb', f'{a.meshes}/{n}.glb', f'{a.meshes}/{n}.obj',
              f'{a.meshes}/{n}.ply'):
        if os.path.exists(q):
            return budget_mesh(q, 4096, 4096)
    raise SystemExit(f'no candidate mesh for {n} under {a.meshes}')


tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
B = len(names)


def gt_xyzw(o):
    q = np.array(o['pose'], float)
    return np.r_[q[:3], q[4:7], q[3]]                                  # parquet pose is x,y,z,qw,qx,qy,qz


trajs = {}
if a.source.endswith('.npz'):
    P = np.load(a.source)
    T = len(P[names[0]])
    trajs['perception'] = np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()]
                                     for n in names] for i in range(T)])
    frames = np.arange(T)
else:
    sys.path.insert(0, a.kit)
    from v2dlb.submission_parquet import read_trajectory
    tr = read_trajectory(os.path.join(a.source, f'episode_{a.ep:06d}.parquet'))
    w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0])

    def grid(Q):
        G = np.full((len(frames), B, 7), np.nan)
        for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
            G[np.searchsorted(frames, fr), s] = q
        return G
    trajs['sim'] = grid(tr.pose_xyzw)
    if tr.reference_xyzw is not None:
        trajs['reference'] = grid(tr.reference_xyzw)
    trajs['static_floor'] = np.repeat(trajs['sim'][:1], len(frames), 0)
gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names]
               for fr in frames])

H = [host_geometry(n, s) for s, n in enumerate(names)]
REG = []
for s, n in enumerate(names):
    cand = candidate_mesh(n)
    ca, R = T3._register_object_body(cand, H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s)
    REG.append((ca, R))


def score(ach):
    ach = ach[:, None].copy(); ref = gt[:, None].copy()                # [T, 1 world, B, 7]
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    out = {k: round(float(T3._registered_pose_metric(m, ach, ref, pts, axes, orders)), 4) for k, m in METRICS}
    out['per_obj_AUC'] = {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1],
                                                                   pts[s:s + 1], axes[s:s + 1], orders[s:s + 1])), 4)
                          for s, n in enumerate(names)}
    PF.append(dict(pos_cm=np.linalg.norm(ach[:, 0, :, :3] - ref[:, 0, :, :3], axis=-1) * 100,
                   add_cm=np.stack([np.linalg.norm((pts[s] @ T3._rotation_matrix(ach[:, 0, s, 3:]).transpose(0, 2, 1) + ach[:, 0, s, None, :3])
                                                   - (pts[s] @ T3._rotation_matrix(ref[:, 0, s, 3:]).transpose(0, 2, 1) + ref[:, 0, s, None, :3]),
                                                   axis=-1).mean(-1) for s in range(B)], 1) * 100))
    if a.per_frame:                                                    # symmetric ADD (the AUC's errors), per frame
        PF[-1]['adds_cm'] = np.stack([T3._symmetry_point_errors(ach[:, :, s], ref[:, :, s], pts[s], axes[s], orders[s])[:, 0]
                                      for s in range(B)], 1) * 100
    return out


PF = []


res = {'episode': a.ep, 'objects': names, 'frames': int(len(frames)), 'meshes': a.meshes or 'public scans',
       'registration': {n: {'rot_deg': round(float(np.degrees(Rot.from_matrix(REG[s][1]).magnitude())), 2),
                            'anchor_shift_cm': round(float(np.linalg.norm(REG[s][0] - H[s]['anchor']) * 100), 2),
                            'axis': np.round(H[s]['axis'], 3).tolist(), 'order': H[s]['order']}
                        for s, n in enumerate(names)}}
for k, v in trajs.items():
    res[k] = score(v)
print(json.dumps(res, indent=1))
out = a.out or (a.source.replace('.npz', '_registered.json') if a.source.endswith('.npz')
                else os.path.join(a.source, f'score_registered_ep{a.ep}.json'))
json.dump(res, open(out, 'w'), indent=1)
if a.per_frame:                                                        # diagnostic: where along the episode it fails
    np.savez(a.per_frame, names=np.array(names), frames=frames, **{f'{k}_{q}': PF[i][q] for i, k in enumerate(trajs) for q in PF[i]})
