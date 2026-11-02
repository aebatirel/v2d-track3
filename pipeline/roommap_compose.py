"""Recompose perc2 object trajectories with room-map camera poses, and measure perc2's camera drift (GT-free).

Reads perc2's poses.npz (world_T_cam = rectified-left camera chain, world = that camera at frame 0; cam_T_<obj>) and a
`roommap.py reloc` npz. Reads no ground truth.
  W_map(t) = map_T_rect(0)^-1 map_T_rect(t),  map_T_rect = map_T_c_gated . rect_T_c^-1
  world_T_obj(t) = W_map(t) . cam_T_obj(t)     -> OUT/poses_world_map.npz (same layout as perc2's poses_world_vo.npz)
Drift (OUT/drift.json): per object, |W_perc(t) p(t) - W_map(t) p(t)| in mm (p = cam_T_obj translation), camera
rotation gap in deg, and the camera-term bound 1 - AUC(perc2 world vs map world) with the kit's frame-0 warp / ADD /
AUC functions on mesh surface samples (no symmetry).
Usage: python roommap_compose.py POSES_NPZ RELOC_NPZ OUT_DIR [--meshes DIR] [--kit KIT]
"""
import argparse, json, os, sys
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser(); p.add_argument('poses'); p.add_argument('reloc'); p.add_argument('out')
p.add_argument('--meshes', default=None); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
P = np.load(a.poses); R = np.load(a.reloc)
W = P['world_T_cam']; names = [k[6:] for k in P.files if k.startswith('cam_T_')]
N = len(W)
fr = R['frames']; assert len(fr) >= N and (fr[:N] == np.arange(N)).all(), 'reloc must cover every frame (stride 1)'
rTc = R['rect_T_c']
mrect = np.stack([M @ np.linalg.inv(rTc) for M in R['map_T_c_gated'][:N]])
Wm = np.stack([np.linalg.inv(mrect[0]) @ M for M in mrect])
out = {n: np.stack([Wm[i] @ P[f'cam_T_{n}'][i] for i in range(N)]) for n in names}
np.savez(f'{a.out}/poses_world_map.npz', **out)
np.save(f'{a.out}/world_T_cam_map.npy', Wm)


def rotdeg(A, B):
    return np.degrees(np.linalg.norm(Rot.from_matrix(A[:3, :3].T @ B[:3, :3]).as_rotvec()))


res = dict(frames=N, objects=names, reloc_ok=float(R['ok'][:N].mean()),
           gate_rejected=float((R['ok'][:N] & ~R['gate_good'][:N]).mean()),
           inliers_min=int(R['inliers'][:N].min()), inliers_median=float(np.median(R['inliers'][:N])))
cam_pos = np.linalg.norm(W[:, :3, 3] - Wm[:, :3, 3], axis=1) * 1000
cam_rot = np.array([rotdeg(W[i], Wm[i]) for i in range(N)])
res['camera'] = dict(pos_mm_max=float(cam_pos.max()), pos_mm_final=float(cam_pos[-1]), rot_deg_max=float(cam_rot.max()),
                     rot_deg_final=float(cam_rot[-1]))
res['objects_mm'] = {}
for n in names:
    pc = P[f'cam_T_{n}'][:, :3, 3]
    d = np.array([np.linalg.norm(W[i, :3, :3] @ pc[i] + W[i, :3, 3] - Wm[i, :3, :3] @ pc[i] - Wm[i, :3, 3])
                  for i in range(N)]) * 1000
    res['objects_mm'][n] = dict(median=float(np.median(d)), p95=float(np.percentile(d, 95)), max=float(d.max()),
                                final=float(d[-1]))
res['max_obj_p95_mm'] = max(v['p95'] for v in res['objects_mm'].values())
# camera-term bound with the kit's functions (perc2 world scored against the map world)
sys.path.insert(0, f'{a.kit}/metric_code/track_3')
import importlib
A = importlib.import_module('AUC')


def verts(n):
    q = f'{a.meshes}/{n}.glb' if a.meshes else None
    m = trimesh.load(q, force='mesh')
    pts = trimesh.sample.sample_surface(m, 500, seed=0)[0]
    return np.asarray(pts)


def xyzw(M):
    return np.r_[M[:3, 3], Rot.from_matrix(M[:3, :3]).as_quat()]


if a.meshes:
    vo = {n: np.stack([W[i] @ P[f'cam_T_{n}'][i] for i in range(N)]) for n in names}
    ach = np.stack([[xyzw(vo[n][i]) for n in names] for i in range(N)])[:, None]
    ref = np.stack([[xyzw(out[n][i]) for n in names] for i in range(N)])[:, None]
    ach = A._warp_to_reference_start(ach, ref)
    add = A._object_add(ach, ref, np.stack([verts(n) for n in names]))
    res['camera_term_auc'] = float(A._add_auc(add)); res['camera_term_bound'] = 1 - res['camera_term_auc']
    res['camera_term_mppe_cm'] = float(A._mean_per_point_error_cm(ach, ref))
json.dump(res, open(f'{a.out}/drift.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'objects_mm'}))
