"""DIAGNOSTIC: is the held-phase error a timing offset? Writes the control track resampled at t + DELTA frames (linear
position, slerp rotation; ends clamped) to OUT/s<DELTA>/ep<e>/poses_world_vo.npz for score_registered.py.
Usage: shift_probe.py CTRL_DIR OUT DELTA EP..."""
import sys, os, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
C, OUT, D = sys.argv[1], sys.argv[2], float(sys.argv[3])
for e in map(int, sys.argv[4:]):
    P = dict(np.load(f'{C}/ep{e}/poses_world_vo.npz')); o = {}
    for n, M in P.items():
        N = len(M); t = np.clip(np.arange(N) + D, 0, N - 1); i0 = np.floor(t).astype(int); i1 = np.minimum(i0 + 1, N - 1); w = t - i0
        R = Rot.from_matrix(M[:, :3, :3]); X = M.copy()
        for k in range(N):
            X[k, :3, 3] = (1 - w[k]) * M[i0[k], :3, 3] + w[k] * M[i1[k], :3, 3]
            X[k, :3, :3] = Slerp([0, 1], R[[i0[k], i1[k]]])([w[k]]).as_matrix()[0]
        o[n] = X
    os.makedirs(f'{OUT}/s{D:+.1f}/ep{e}', exist_ok=True); np.savez(f'{OUT}/s{D:+.1f}/ep{e}/poses_world_vo.npz', **o)
