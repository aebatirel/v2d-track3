import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
import numpy as np
import vo_anchor_test as V
XF = V.XF
ep = int(sys.argv[1]); arm = sys.argv[2] if len(sys.argv) > 2 else 'Po'; mode = sys.argv[3] if len(sys.argv) > 3 else 'T'
names, gt = XF.mocap(V.T3D, ep, None)
H = [XF.host_geometry(V.T3D, n, s) for s, n in enumerate(names)]
hz = np.load(f'{V.S}/refine/in/ep{ep}/hands_refined.npz', allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
Vv = np.load(f'{V.ROOT}/{arm}/ep{ep}/poses_world_vo.npz'); T = {n: Vv[n].astype(float) for n in names}
P = {n: V.lib_pts(n) for n in names}
cand, dh, gap = V.windows(T, P, J, Jv, names, True)
cd = {n: cand[n].copy() for n in names}
C, act = V.correct(T, P, names, cd, gap, mode)
for i in range(0, len(C), 3):
    print(i, [int(cand[n][i]) for n in names], [round(float(dh[n][i]) * 100, 1) for n in names], act[i], np.round(C[i, :3, 3] * 100, 2))
