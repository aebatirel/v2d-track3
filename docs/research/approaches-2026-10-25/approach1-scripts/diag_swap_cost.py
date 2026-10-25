"""[D] DIAGNOSTIC ONLY (reads public mocap). Approach-1 study, 2026-10-25.

What does an identity swap of two near-identical boards cost on the kit's ADD-AUC? Public ep24, our own-mesh track
(which matches mocap) scored as is, with the two names swapped, and with only board 2 turned 180 deg about x or z.
Kit-like scoring: slot-0 anchor (one rigid transform at frame 0 from wooden_piece_1's pose), ADD over our mesh
vertices (our mesh frame = scan frame to about 3 mm / 3 deg for the boards), thresholds 1-9 cm, trapezoid, mean of
bodies. No mesh registration step (identity), so the absolute numbers are approximate; the differences are the point.
Usage: python diag_swap_cost.py EPISODE.parquet POSES_WORLD_VO.npz MESH_1 MESH_2"""
import sys

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.integrate import trapezoid
from scipy.spatial.transform import Rotation as R

ep, poses, m1, m2 = sys.argv[1:5]
names = ['wooden_piece_1', 'wooden_piece_2']
rows = pq.read_table(ep).to_pylist()
G = {n: [] for n in names}
for r in rows:
    for o in r['observation.objects']:
        if o['name'] in G:
            G[o['name']].append(o['pose'])


def T_of(p):
    p = np.array(p, float); T = np.tile(np.eye(4), (len(p), 1, 1))
    T[:, :3, :3] = R.from_quat(p[:, [4, 5, 6, 3]]).as_matrix(); T[:, :3, 3] = p[:, :3]
    return T


TG = {n: T_of(G[n]) for n in names}
P = np.load(poses); TO = {n: P[n] for n in names}                   # poses_world_vo.npz: world_T_object (VO world)
V = {n: np.asarray(trimesh.load(m, force='mesh').vertices)[::5] for n, m in zip(names, (m1, m2))}
TH = np.arange(0.01, 0.10, 0.01)


def auc(track):
    W = TG[names[0]][0] @ np.linalg.inv(track[names[0]][0])          # slot-0 anchor at frame 0
    out = []
    for n in names:
        A = W @ track[n]; Gt = TG[n]
        pa = np.einsum('tij,vj->tvi', A[:, :3, :3], V[n]) + A[:, None, :3, 3]
        pg = np.einsum('tij,vj->tvi', Gt[:, :3, :3], V[n]) + Gt[:, None, :3, 3]
        add = np.linalg.norm(pa - pg, axis=-1).mean(1)
        out.append(trapezoid([np.mean(add < t) for t in TH], x=np.linspace(0, 1, len(TH))))
    return np.round(out, 3), round(float(np.mean(out)), 3)


Fx = np.diag([1., -1, -1, 1]); Fz = np.diag([-1., -1, 1, 1])
print('as tracked             (b1, b2), mean:', auc(TO))
print('names swapped          (b1, b2), mean:', auc({names[0]: TO[names[1]], names[1]: TO[names[0]]}))
print('board 2 turned 180 x   (b1, b2), mean:', auc({names[0]: TO[names[0]], names[1]: TO[names[1]] @ Fx}))
print('board 2 turned 180 z   (b1, b2), mean:', auc({names[0]: TO[names[0]], names[1]: TO[names[1]] @ Fz}))
