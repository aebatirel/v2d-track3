import json, sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/tools'); sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_11/scripts')
import diag11 as D
XF = D.XF; T3 = D.T3
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
n_pl = np.array([-0.097, -0.765, -0.637]); n_pl /= np.linalg.norm(n_pl); d_pl = 0.534   # perc log table plane (half-res K; normal is scale-free)
print('plane n', n_pl, 'd', d_pl)
def anc(M, s): return M[:, :3, 3] + np.einsum('nij,j->ni', M[:, :3, :3], H[s]['anchor'])
for arm in ('Po', 'Ps'):
    T = tr[arm]
    for s, n in enumerate(names):
        a = anc(T[n], s); ax = T[n][:, :3, :3] @ H[s]['axis']
        h = a @ n_pl + d_pl
        tilt = np.degrees(np.arccos(np.clip(np.abs(ax @ n_pl), -1, 1)))
        print(arm, n, 'f0 anchor height above plane cm %.2f' % (h[0] * 100), 'axis tilt vs plane deg %.2f' % tilt[0],
              '| f60 h %.2f tilt %.2f | f69 h %.2f | f130 h %.2f' % (h[60] * 100, tilt[60], h[69] * 100, h[130] * 100))
# mocap
up = np.array([0, 0, 1.0])
for s, n in enumerate(names):
    a = anc(gt[n], s); ax = gt[n][:, :3, :3] @ H[s]['axis']
    print('mocap', n, 'f0 anchor z cm %.2f' % (a[0, 2] * 100), 'axis tilt vs z deg %.2f' % np.degrees(np.arccos(abs(ax[0] @ up))), 'f130 z %.2f' % (a[130, 2] * 100))
# relative beige-blue in perception (along plane normal) vs mocap
for arm in ('Po', 'Ps'):
    T = tr[arm]; ab = anc(T['blue_cup'], 0); ag = anc(T['beige_cup'], 1)
    print(arm, 'beige-blue height diff along n cm f0 %.2f f130 %.2f; horizontal dist f0 %.2f' % (((ag - ab) @ n_pl)[0] * 100, ((ag - ab) @ n_pl)[130] * 100,
          np.linalg.norm((ag - ab)[0] - ((ag - ab)[0] @ n_pl) * n_pl) * 100))
ab = anc(gt['blue_cup'], 0); ag = anc(gt['beige_cup'], 1)
print('mocap beige-blue z diff f0 %.2f f130 %.2f; horiz f0 %.2f' % ((ag - ab)[0, 2] * 100, (ag - ab)[130, 2] * 100, np.linalg.norm((ag - ab)[0, :2]) * 100))
