"""Anchor frame-0 pose test "A-f0" (pre-registered 2026-10-25 in docs/work-log.md; docs/research/spoon-2026-10-25/).
The kit aligns the whole achieved scene on the anchor object's frame-0 orientation (`_align_registered_scene`), so that
one orientation decides every later position. This scores stored official rollouts of a PUBLIC episode against mocap
(evaluation only, after inference) with the registered kit path of pipeline/score_registered.py, three ways:
  a  as stored (achieved frame 0 = our reference's frame 0);
  b  the anchor's achieved frame-0 orientation replaced by the raw tracker's (perc2 poses.npz) rest-averaged orientation
     (chordal mean over the anchor's frames before its first > 1 cm motion in the rollout's reference, at most 30),
     mapped into the reference world by the raw -> reference rotation (median over the frames after that rest);
  c  the same with the raw tracker's single frame-0 orientation.
Usage: python anchor_f0_test.py EP PERC2_POSES.npz ROLLOUT_DIR [ROLLOUT_DIR ...] --t3 T3 --kit KIT --meshes LIB [--out JSON]
"""
import argparse, json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser(); p.add_argument('ep', type=int); p.add_argument('perc'); p.add_argument('rollouts', nargs='+')
p.add_argument('--t3', required=True); p.add_argument('--kit', required=True); p.add_argument('--meshes', required=True)
p.add_argument('--out'); p.add_argument('--n_points', type=int, default=1000); p.add_argument('--rest_max', type=int, default=30)
a = p.parse_args()
sys.path.insert(0, a.kit)
from v2dlb import track3_pose as T3  # noqa: E402
from v2dlb.mesh_budget import budget_mesh  # noqa: E402
from v2dlb.object_mesh import _surface_moments  # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface  # noqa: E402
from v2dlb.submission_parquet import read_trajectory  # noqa: E402
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def host_geometry(n, slot):                                          # as pipeline/score_registered.py
    m = trimesh.load(scan_path(n), force='mesh'); v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f); pts = _sample_mesh_surface(v, f, a.n_points, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)
H = [host_geometry(n, s) for s, n in enumerate(names)]
REG = []
for s, n in enumerate(names):
    q = next(x for x in (f'{a.meshes}/{n}.glb', f'{a.meshes}/{n}.obj') if os.path.exists(x))
    REG.append(T3._register_object_body(budget_mesh(q, 4096, 4096), H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s))
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
fixed = [i for i, ax in enumerate(axes) if not np.any(ax)]; anc = fixed[0] if fixed else 0


def gt_traj(frames):
    def xyzw(o):
        q = np.array(o['pose'], float); return np.r_[q[:3], q[4:7], q[3]]
    return np.stack([[xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names] for fr in frames])


def score(ach, gt):
    ach = ach[:, None].copy(); ref = gt[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    ach = T3._align_registered_scene(ach, ref, axes)
    return round(float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders)), 4)


Pc = np.load(a.perc); key = f'cam_T_{names[anc]}'
raw = np.einsum('tij,tjk->tik', Pc['world_T_cam'], Pc[key]) if key in Pc.files else None
res = dict(ep=a.ep, objects=names, anchor=names[anc], rollouts={})
for rd in a.rollouts:
    tr = read_trajectory(os.path.join(rd, f'episode_{a.ep:06d}.parquet')); w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0])

    def grid(Q):
        G = np.full((len(frames), B, 7), np.nan)
        for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
            G[np.searchsorted(frames, fr), s] = q
        return G
    sim, refp = grid(tr.pose_xyzw), grid(tr.reference_xyzw); gt = gt_traj(frames)
    out = dict(a=score(sim, gt))
    if raw is not None:
        n_ = min(len(frames), len(raw)); ok = np.isfinite(raw[:n_]).all((1, 2))
        mv = np.nonzero(np.linalg.norm(refp[:, anc, :3] - refp[0, anc, :3], axis=1) > 0.01)[0]; on = int(mv[0]) if len(mv) else len(frames)
        rest = [i for i in range(min(on, a.rest_max)) if ok[i]]; after = [i for i in range(on + 10, n_) if ok[i]]
        if len(rest) >= 3 and len(after) >= 10:
            Rraw = Rot.from_matrix(raw[:n_, :3, :3][ok[:n_]]); idx = np.nonzero(ok[:n_])[0]; pos = {int(i): k for k, i in enumerate(idx)}
            Wm = (Rot.from_quat(refp[after, anc, 3:]) * Rraw[[pos[i] for i in after]].inv()).mean()
            for tag, Rnew in (('b', Wm * Rraw[[pos[i] for i in rest]].mean()), ('c', Wm * Rraw[pos[rest[0]]] if rest[0] == 0 else None)):
                if Rnew is None:
                    continue
                s2 = sim.copy(); s2[0, anc, 3:] = Rnew.as_quat(); out[tag] = score(s2, gt)
            out['rest_frames'] = len(rest); out['onset'] = on
            d0 = (Rot.from_quat(sim[0, anc, 3:]).inv() * Wm * Rraw[[pos[i] for i in rest]].mean()).as_rotvec()
            out['ref_f0_vs_rest_mean_deg'] = np.degrees(d0).round(1).tolist()
    res['rollouts'][os.path.basename(rd.rstrip('/'))] = out
    print(a.ep, os.path.basename(rd.rstrip('/')), json.dumps(out), flush=True)
for k in ('a', 'b', 'c'):
    v = [r[k] for r in res['rollouts'].values() if k in r]
    res[f'mean_{k}'] = round(float(np.mean(v)), 4) if v else None
print(json.dumps({k: res[k] for k in ('ep', 'anchor', 'mean_a', 'mean_b', 'mean_c')}))
if a.out:
    json.dump(res, open(a.out, 'w'), indent=1)
