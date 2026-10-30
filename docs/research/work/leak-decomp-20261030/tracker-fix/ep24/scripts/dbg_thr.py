import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
import numpy as np
import vo_anchor_test as V
XF = V.XF
ep = int(sys.argv[1])
names, gt = XF.mocap(V.T3D, ep, None)
H = [XF.host_geometry(V.T3D, n, s) for s, n in enumerate(names)]
REGs = [XF.reg_of_X(np.asarray(V.XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
Vv = np.load(f'{V.ROOT}/Po/ep{ep}/poses_world_vo.npz'); T = {n: Vv[n].astype(float) for n in names}; N = len(T[names[0]])
g = {n: gt[n][:N] for n in names}
for d in (0.0005, 0.001, 0.002):
    for ax in range(3):
        M = np.eye(4); M[ax, 3] = d
        T2 = {n: np.concatenate([T[n][:40], np.einsum('ij,njk->nik', M, T[n][40:])]) for n in names}
        print(d, ax, XF.score_track(names, T2, g, H, REGs))
