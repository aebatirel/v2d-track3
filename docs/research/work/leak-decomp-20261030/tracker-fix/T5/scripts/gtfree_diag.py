"""GT-free readout: our board-2 world centroid displacement from frame 0 under each camera (our tracks, our meshes)."""
import sys, json, numpy as np, trimesh
out = sys.argv[1]; poses = sys.argv[2]; vs = sys.argv[3].split(',')
P = np.load(poses); W0 = P['world_T_cam']
m = trimesh.load('/home/user/v2d-track3/meshes/library_v3/wooden_piece_2.glb', force='mesh'); c = np.asarray(m.vertices).mean(0)
camT = P['cam_T_wooden_piece_2']
for v in vs:
    W = np.load(f'{out}/W_{v}.npy')
    O = np.einsum('tij,tjk->tik', W, camT); x = O[:, :3, :3] @ c + O[:, :3, 3]
    d = np.linalg.norm(x - x[0], axis=1) * 100
    dc = np.linalg.norm(W[:, :3, 3] - W0[:, :3, 3], axis=1) * 100
    print(f'{v:10s} board2 |x(t)-x(0)| cm: f30 {d[30]:.2f} f36 {d[36]:.2f} f40 {d[40]:.2f} f50 {d[50]:.2f} f75 {d[75]:.2f} f100 {d[100]:.2f} f110 {d[110]:.2f} | max f0-110 {d[:111].max():.2f} | cam centre vs base f50 {dc[50]:.2f} f100 {dc[100]:.2f} end {dc[-1]:.2f}')
