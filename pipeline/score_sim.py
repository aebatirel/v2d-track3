"""Score an official-evaluator rollout of a PUBLIC episode against mocap (evaluation only).

Reads <results>/episode_XXXXXX.parquet with the kit's own reader, pairs evaluator row k with source frame k
(timing rule: fps 20, motion_speed 1.0), and applies the kit Track 3 metric functions (one rigid warp from slot 0 at
frame 0, 500 surface samples per public mesh as a stand-in for the hidden vertex payload). Also reports the same
metrics for the policy's own reference (what the policy was asked to track) and the 'nothing moves' floor.
Usage: python score_sim.py EP RESULTS_DIR [REF_NPZ]
"""
import sys, os, json, importlib, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
EP = int(sys.argv[1]); RES = sys.argv[2]; D = '/content/t3'
KIT = '/content/kit/v2d_submission_kit'
sys.path.insert(0, KIT); sys.path.insert(0, f'{KIT}/metric_code/track_3')
from v2dlb.submission_parquet import read_trajectory
A = importlib.import_module('AUC')
tr = read_trajectory(os.path.join(RES, f'episode_{EP:06d}.parquet'))
tab = pq.read_table(f'{D}/ep{EP}.parquet').to_pandas()
names = [o['name'] for o in tab['observation.objects'].iloc[0]]
w0 = tr.world_index == tr.world_index.min()
frames = np.unique(tr.frame_index[w0]); B = len(names)
print('rows', len(tr.pose_xyzw), 'frames', len(frames), frames.min(), frames.max(), 'gt rows', len(tab), 'slots', np.unique(tr.object_slot))
def grid(P):
    G = np.full((len(frames), B, 7), np.nan)
    for f, s, p in zip(tr.frame_index[w0], tr.object_slot[w0], P[w0]): G[np.searchsorted(frames, f), s] = p
    return G
ach = grid(tr.pose_xyzw); refp = grid(tr.reference_xyzw) if tr.reference_xyzw is not None else None
def gt_xyzw(o):
    p = np.array(o['pose'], float); return np.r_[p[:3], p[4:7], p[3]]   # parquet pose is x,y,z,qw,qx,qy,qz
gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[f] if o['name'] == n][0]) for n in names] for f in frames])
def mp(n):
    p = f'{D}/mesh/{n}/{n}.glb'; p = p if os.path.exists(p) else f'{D}/mesh/{n}/{n}_visual.glb'
    return np.asarray(trimesh.sample.sample_surface(trimesh.load(p, force='mesh'), 500, seed=0)[0])
V = np.stack([mp(n) for n in names])
def score(a, r):
    a, r = a[:, None], r[:, None]
    a = A._warp_to_reference_start(a, r); add = A._object_add(a, r, V)
    return dict(AUC=round(A._add_auc(add), 4), SP_SR=float(np.mean(A._spider_success(a, r))),
                MP_SR=float(np.mean(A._maniptrans_success(a, r, np.arange(B)))), MPPE_cm=round(A._mean_per_point_error_cm(a, r), 3),
                RPE_cm=round(A._relative_position_error_cm(a, r), 3),
                per_obj={n: round(A._add_auc(add[:, :, b:b + 1]), 4) for b, n in enumerate(names)})
out = {'episode': EP, 'objects': names, 'frames': int(len(frames)),
       'sim_vs_mocap': score(ach, gt), 'static_floor': score(np.repeat(ach[:1], len(frames), 0), gt)}
if refp is not None:
    out['reference_vs_mocap'] = score(refp, gt); out['sim_vs_reference'] = score(ach, refp)
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(RES, f'score_ep{EP}.json'), 'w'), indent=1)
