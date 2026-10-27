"""Frame-indexing check (refcheck/verify_chain): write copies of a poses_world_vo.npz shifted in time by k frames
(P'[t] = P[clip(t + k, 0, T-1)]), so that scoring them shows whether perception frame t matches mocap row t (the AUC
should peak at k = 0 if there is no off-by-one). No ground truth is read here.
Usage: python -I shift.py IN.npz OUT_PREFIX k1 k2 ...
"""
import sys
import numpy as np

P = np.load(sys.argv[1]); pre = sys.argv[2]
for k in map(int, sys.argv[3:]):
    out = {}
    for n in P.files:
        A = P[n]; T = len(A)
        out[n] = A[np.clip(np.arange(T) + k, 0, T - 1)]
    np.savez(f'{pre}_shift{k:+d}.npz', **out)
    print(f'{pre}_shift{k:+d}.npz')
