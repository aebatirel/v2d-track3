"""Proxy for a table-plane (height-only) camera constraint on public ep24: the rule-K correction projected onto our
frame-0 table normal (GT-free plane from our depth0), i.e. what a perfect 1-DoF height correction would recover.
Scoring is ORACLE (mocap). Usage: python -I normal_proxy24.py
"""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import numpy as np
import vo_anchor_test2 as V
import det_rules
XF = V.XF; S = V.S; ep = 24
names, gt = XF.mocap(V.T3D, ep, None)
H = [XF.host_geometry(V.T3D, n, s) for s, n in enumerate(names)]
REGs = [XF.reg_of_X(np.asarray(V.XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
REGl = [XF.kit_X(f'{V.LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)]
d = np.load(f'{S}/refine/in/ep{ep}/depth0.npy'); hz = np.load(f'{S}/refine/in/ep{ep}/hands_refined.npz', allow_pickle=True)
pl = det_rules.table_plane(d[::2, ::2].astype(np.float32), np.diag([0.5, 0.5, 1.0]) @ hz['KR']); nrm = np.asarray(pl[0], float)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
Vv = np.load(f'{V.ROOT}/Po/ep{ep}/poses_world_vo.npz'); T = {n: Vv[n].astype(float) for n in names}; N = len(T[names[0]])
kfs = json.load(open(f'{S}/refine/in/ep{ep}/vo.json'))['keyframes']
P = {n: V.lib_pts(n) for n in names}
V.D_H, V.REST_MIN, V.KW = 0.03, 5, 2
cand, cen, dh, gap = V.windows(T, P, J, Jv, names, True)
C, log = V.correct(names, cand, cen, gap, kfs)
g = {n: gt[n][:N] for n in names}
out = {}
for lab, CC in (('none', np.zeros_like(C)), ('K_full', C), ('K_normal_only', (C @ nrm)[:, None] * nrm[None]), ('K_in_plane_only', C - (C @ nrm)[:, None] * nrm[None])):
    T2 = {n: T[n].copy() for n in names}
    for n in names:
        T2[n][:, :3, 3] += CC
    out[lab] = dict(star=XF.score_track(names, T2, g, H, REGs)['AUC'], lib=XF.score_track(names, T2, g, H, REGl)['AUC'])
print('table normal (camera f0)', np.round(nrm, 3), 'correction at end cm', np.round(C[-1] * 100, 2), 'normal part cm', round(float(C[-1] @ nrm * 100), 2))
print(json.dumps(out))
print('absorb log', log)
