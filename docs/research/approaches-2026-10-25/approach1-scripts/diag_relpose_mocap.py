"""[D] DIAGNOSTIC ONLY (reads public mocap; never a method input). Approach-1 study, 2026-10-25.

For a public two-board episode: compare the relative pose of board 2 in board 1's frame, ours vs mocap, at frame 0
(both boards lying flat) and at the assembled frames; and each board's frame-0 orientation error after aligning our
world to the mocap world with board 1's frame-0 pose (the kit's slot-0 anchor convention) and with board 2's.
Pose layout in the public parquet: world_T_object [x y z qw qx qy qz] (scan frame = our mesh frame); checked below by
the quaternion norm. Usage: python diag_relpose_mocap.py EPISODE.parquet OUR_POSES.npz a:b (assembled frames)"""
import sys

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

ep, ours, asm = sys.argv[1:4]
a, b = map(int, asm.split(':'))
rows = pq.read_table(ep).to_pylist()
names = ['wooden_piece_1', 'wooden_piece_2']
G = {n: [] for n in names}
for r in rows:
    for o in r['observation.objects']:
        if o['name'] in G:
            G[o['name']].append(o['pose'])
G = {n: np.array(v, float) for n, v in G.items()}
print('quat norms (should be 1):', {n: round(float(np.linalg.norm(G[n][0, 3:])), 4) for n in names})


def T_of(p):  # public parquet: [x y z qw qx qy qz] (as census_gtdiag.py / pipeline/score_registered.py read it) -> 4x4
    T = np.tile(np.eye(4), (len(p), 1, 1)); T[:, :3, :3] = R.from_quat(p[:, [4, 5, 6, 3]]).as_matrix(); T[:, :3, 3] = p[:, :3]
    return T


TG = {n: T_of(G[n]) for n in names}
P = np.load(ours); TO = {n: P[f'cam_T_{n}'] for n in names}


def rel(TA, TB, t):
    return np.linalg.inv(TA[t]) @ TB[t]


for label, frames in [('frame 0', [0]), (f'assembled {a}-{b}', list(range(a, b)))]:
    dt, dr = [], []
    for t in frames:
        rg = rel(TG[names[0]], TG[names[1]], t); ro = rel(TO[names[0]], TO[names[1]], t)
        dt.append(np.linalg.norm(rg[:3, 3] - ro[:3, 3]) * 100)
        dr.append(R.from_matrix(rg[:3, :3].T @ ro[:3, :3]).magnitude() * 180 / np.pi)
    D = R.from_matrix(rg[:3, :3].T @ ro[:3, :3])
    print(f'{label}: relative pose ours vs mocap: |dt| median {np.median(dt):.2f} cm, rotation median {np.median(dr):.1f} deg; '
          f'last frame residual rotation axis in B frame {np.round(D.as_rotvec() / max(D.magnitude(), 1e-9), 2)}')
# absolute frame-0 orientation of each board after anchoring on the other board (kit uses slot 0 = board 1)
for anc, oth in [(names[0], names[1]), (names[1], names[0])]:
    W = TG[anc][0] @ np.linalg.inv(TO[anc][0])                 # maps our world (camera) frame to mocap world at f0
    for t in [0, a]:
        e = R.from_matrix(TG[oth][t][:3, :3].T @ (W @ TO[oth][t])[:3, :3])
        print(f'anchor {anc}: {oth} orientation error at f{t}: {e.magnitude() * 180 / np.pi:.1f} deg, axis (body) {np.round(e.as_rotvec() / max(e.magnitude(), 1e-9), 2)}; '
              f'position error {np.linalg.norm((W @ TO[oth][t])[:3, 3] - TG[oth][t][:3, 3]) * 100:.1f} cm')
