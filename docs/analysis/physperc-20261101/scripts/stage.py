"""Stage the 20 public perception tracks (GT-free) as world-frame poses_world_vo.npz (world_T_cam @ cam_T_<obj>),
exactly as bold-albattani's posefix stage_inputs.py. Reads only our own inference output.
Usage: python -I stage.py SCRATCH"""
import os, sys, numpy as np
S = sys.argv[1]
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
for e in EPS:
    P = np.load(f'{S}/data/sweep/ep{e}/poses.npz')
    W = np.asarray(P['world_T_cam'], np.float64)
    out = {k[6:]: np.einsum('tij,tjk->tik', W, np.asarray(P[k], np.float64)) for k in P.files if k.startswith('cam_T_')}
    os.makedirs(f'{S}/tracks/ep{e}', exist_ok=True)
    np.savez(f'{S}/tracks/ep{e}/poses_world_vo.npz', **out)
    print(e, list(out), len(W))
