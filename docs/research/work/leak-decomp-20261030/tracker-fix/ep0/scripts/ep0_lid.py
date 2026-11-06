"""ORACLE DIAGNOSTIC ep0: structure of the P_o lid error (constant body offset?) vs mocap under G, by mocap phase."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
XF.kit(S + '/map/scoring/kit/v2d_submission_kit'); T3D = S + '/map/scoring/t3'
names, gt = XF.mocap(T3D, 0); N = len(gt[names[0]])
H = {n: XF.host_geometry(T3D, n, s) for s, n in enumerate(names)}
XG = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
X = {n: np.array(XG[n]['X_scan_T_lib']) for n in names}
R = S + '/leak/p1/oracle_roots'
d = np.load(f'{S}/leak/diag_ep0/out/perframe.npz'); G = d['G']
arms = {'Ps': {n: np.load(f'{R}/Ps_scan/ep0/poses_world_vo.npz')[n].astype(float) for n in names},
        'Po': {n: np.load(f'{R}/Po/ep0/poses_world_vo.npz')[n].astype(float) @ np.linalg.inv(X[n]) for n in names}}
n = 'white_pot_lid'; h = H[n]; c = h['anchor']; ax = h['axis']
Sflip = XF.about(ax, np.pi, c)
phase = np.zeros(N, int)  # from mocap: 0 on pot rest, 1 in hand/moving, 2 on table rest, 3 back on pot
rel = d['lid_rel_d']; v = d['mocap_speed_white_pot_lid']
phase[(rel > 15) & (v < 3)] = 2; phase[(v >= 3) | ((rel > 1) & (rel <= 15))] = 1; phase[(np.arange(N) > 200) & (rel < 1)] = 3
for a, T in arms.items():
    A = np.einsum('ij,njk->nik', G, T[n]); B = gt[n]
    E = np.stack([np.linalg.inv(B[i]) @ A[i] for i in range(N)])            # body-frame error (scan body)
    E2 = np.stack([np.linalg.inv(B[i] @ Sflip) @ A[i] for i in range(N)])   # vs the flipped-equivalent
    rot1 = Rot.from_matrix(E[:, :3, :3]).magnitude(); rot2 = Rot.from_matrix(E2[:, :3, :3]).magnitude()
    E = np.where((rot2 < rot1)[:, None, None], E2, E)
    off = (E[:, :3, :3] @ c + E[:, :3, 3]) - c                               # anchor displacement in the lid body frame (m)
    along = off @ ax * 100; perp = np.linalg.norm(off - np.outer(off @ ax, ax), axis=1) * 100
    tilt = np.degrees(np.arccos(np.clip((E[:, :3, :3] @ ax) @ ax, -1, 1)))
    print(a, 'flip-equivalent chosen in', int((rot2 < rot1).sum()), 'frames')
    for p, nm in enumerate(['on pot (start)', 'moving/in hand', 'on table', 'on pot (end)']):
        m = phase == p
        if m.sum() == 0: continue
        print(f'  {nm:16s} n={m.sum():3d}  along-normal {np.mean(along[m]):+.2f}±{np.std(along[m]):.2f} cm  in-plane {np.mean(perp[m]):.2f}±{np.std(perp[m]):.2f} cm  tilt {np.mean(tilt[m]):.1f}±{np.std(tilt[m]):.1f} deg  mean off(body) {np.round(off[m].mean(0)*100, 2)}')
# P_o lid relative to P_s lid (same world, both scan frames): constant?
A = arms['Po'][n]; B = arms['Ps'][n]
E = np.stack([np.linalg.inv(B[i]) @ A[i] for i in range(N)]); E2 = np.stack([np.linalg.inv(B[i] @ Sflip) @ A[i] for i in range(N)])
r1 = Rot.from_matrix(E[:, :3, :3]).magnitude(); r2 = Rot.from_matrix(E2[:, :3, :3]).magnitude(); E = np.where((r2 < r1)[:, None, None], E2, E)
off = (E[:, :3, :3] @ c + E[:, :3, 3]) - c
print('Po lid vs Ps lid (body frame of Ps): mean off cm', np.round(off.mean(0) * 100, 2), 'sd', np.round(off.std(0) * 100, 2), 'rot mean', round(float(np.degrees(np.minimum(r1, r2)).mean()), 2), 'sd', round(float(np.degrees(np.minimum(r1, r2)).std()), 2))
# lid relative to pot in each arm vs mocap, in the pot body frame, on-pot phases
for a, T in arms.items():
    Lr = np.stack([np.linalg.inv(T['white_pot'][i]) @ T[n][i] for i in range(N)]); Lg = np.stack([np.linalg.inv(gt['white_pot'][i]) @ gt[n][i] for i in range(N)])
    q = Lr[:, :3, :3] @ c + Lr[:, :3, 3]; qg = Lg[:, :3, :3] @ c + Lg[:, :3, 3]
    for p in (0, 3):
        m = phase == p
        print(a, 'lid-in-pot frame, phase', p, 'diff vs mocap (pot body, cm)', np.round((q[m] - qg[m]).mean(0) * 100, 2), 'norm', round(float(np.linalg.norm((q[m] - qg[m]).mean(0)) * 100), 2))
print('phase counts', np.bincount(phase), 'phase boundaries', [int(i) for i in np.nonzero(np.diff(phase))[0] + 1])
print('pot body axes: height = body x (smallest PCA var); lid normal axis (scan body):', np.round(ax, 3))
