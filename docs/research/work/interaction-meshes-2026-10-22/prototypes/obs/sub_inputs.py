# Subsample our poses.npz and hands.npz to every 2nd frame (matching depth/ep<E>_s2.npy).
import sys, numpy as np
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
for E in sys.argv[1:]:
    P = np.load(f'{SP}/loc/perc/ep{E}/poses.npz'); N = len(P['world_T_cam'])
    np.savez(f'{SP}/interact/obs/depth/ep{E}_s2_poses.npz', **{k: P[k][::2] for k in P.files})
    H = np.load(f'{SP}/loc/refs/ep{E}/hands.npz')
    np.savez(f'{SP}/interact/obs/depth/ep{E}_s2_hands.npz', **{k: (H[k][::2] if H[k].ndim and H[k].shape[0] == N else H[k]) for k in H.files})
    print(E, N)
