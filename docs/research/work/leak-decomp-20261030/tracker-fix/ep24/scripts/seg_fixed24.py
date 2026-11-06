"""ep24: per-segment kit-aligned ADD of the P_o / P_s tracks after the GT-free rule-K camera correction (oracle scoring)."""
import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
import numpy as np
import diag24 as D
import vo_anchor_test2 as V
XF = D.XF; S = D.S
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
hz = np.load(f'{S}/refine/in/ep24/hands_refined.npz', allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
kfs = json.load(open(f'{S}/refine/in/ep24/vo.json'))['keyframes']
V.D_H, V.REST_MIN, V.KW = 0.03, 5, 2
segs = [('A', 0, 33), ('B', 33, 52), ('C', 52, 111), ('D', 111, 164), ('E', 164, 220), ('F', 220, 275), ('all', 0, 275)]
for arm in ('Po', 'Ps'):
    Vv = np.load(f'{V.ROOT}/Po/ep24/poses_world_vo.npz') if arm == 'Po' else np.load(f'{V.ROOT}/Ps_scan/ep24/poses_world_vo.npz')
    Tl = {n: Vv[n].astype(float) for n in names}
    P = {n: V.lib_pts(n) for n in names} if arm == 'Po' else {n: H[s]['points'][::5] + H[s]['anchor'] for s, n in enumerate(names)}
    V._GEOM.clear()
    cand, cen, dh, gap = V.windows(Tl, P, J, Jv, names, True)
    C, log = V.correct(names, cand, cen, gap, kfs)
    T = {n: tr[arm][n].copy() for n in names}
    for n in names:
        T[n][:, :3, 3] += C
    al, ref, ach, _ = D.chain(names, T, gt, H)
    pf = D.per_frame(al, ref, H, names)
    for n in names:
        e = pf[n]['add']
        print(arm, n, ' '.join(f'{lab}:{np.median(e[a:b]) * 100:.2f}/{e[a:b].max() * 100:.2f}/{D.auc_of(e[a:b]):.3f}' for lab, a, b in segs),
              'rot med %.1f max %.1f' % (np.median(pf[n]['rot']), pf[n]['rot'].max()))
