"""GT-free check of eval 10's camera (VO) at frames 30/60/150 against frame 0, from our own stored stereo depth
(frames 0/30/60/150 already pulled by the earlier eval-10 depth check) and our own track: back-project each frame's depth
with the frame's world_T_cam, drop points within 12 cm of either cup's centre and within 8 cm of any measured hand
joint, keep points above the table plane band (> 3 cm off the plane, i.e. not the table top, which is blind to sliding
along it) and run a translation-only, then rigid, trimmed point-to-point ICP of frame t's background onto frame 0's.
If our VO were off by the blue cup's 4-5 cm horizontal step, the background would be offset by that much.
Usage: python -I e10_vo_bg.py DEPTH_NPY"""
import sys, numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
dp = sys.argv[1]; E.assert_inference_input(dp)
D = np.load(dp, mmap_mode='r'); frames = [0, 30, 60, 150]
I = E.inputs(10, False); det = np.load(I['det'], allow_pickle=True); K = det['K'].astype(float)
pl = E.plane_of(det); nrm, c0 = np.asarray(pl[0], float), float(pl[1])
P = np.load(I['poses']); W = P['world_T_cam'].astype(float); Wd = E.world(P)
cen = {n: Wd[n][:, :3, :3] @ np.asarray(E.mesh(f'{E.REPO}/meshes/library_v3/{n}.glb').vertices, float).mean(0) + Wd[n][:, :3, 3]
       for n in ('blue_cup', 'beige_cup')}
hz = np.load(I['hands'], allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
H, Wd_ = D.shape[1:]; s = 4
v, u = np.mgrid[0:H:s, 0:Wd_:s]
def cloud(k, t):
    z = np.asarray(D[k, ::s, ::s], float); ok = (z > 0.2) & (z < 2.5) & np.isfinite(z)
    X = np.stack([(u[ok] - K[0, 2]) / K[0, 0] * z[ok], (v[ok] - K[1, 2]) / K[1, 1] * z[ok], z[ok]], 1)
    Xw = X @ W[t][:3, :3].T + W[t][:3, 3]
    keep = np.abs(Xw @ nrm + c0) > 0.03
    for n in cen:
        keep &= np.linalg.norm(Xw - cen[n][t], axis=1) > 0.12
    if Jv[t].any():
        keep &= cKDTree(J[t][Jv[t]]).query(Xw)[0] > 0.08
    return Xw[keep]
def icp(A, B, rigid, it=300, trim=0.7):
    tree = cKDTree(B); R = np.eye(3); t = np.zeros(3)
    for _ in range(it):
        X = A @ R.T + t; d, j = tree.query(X); m = d <= np.quantile(d, trim); a, b = X[m], B[j[m]]
        if rigid:
            ca, cb = a.mean(0), b.mean(0); U, _, Vt = np.linalg.svd((a - ca).T @ (b - cb)); Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
            dR = Vt.T @ Dg @ U.T; dt = cb - dR @ ca
        else:
            dR = np.eye(3); dt = (b - a).mean(0)
        R, t = dR @ R, dR @ t + dt
    d = tree.query(A @ R.T + t)[0]
    return R, t, float(np.median(d))
C0 = cloud(0, 0)
print(f'eval 10 background points kept: f0 {len(C0)}; blue cup world step since f0 (cm):',
      {t: round(float(np.linalg.norm(cen["blue_cup"][t] - cen["blue_cup"][0]) * 100), 2) for t in frames})
for k, t in enumerate(frames[1:], 1):
    Ct = cloud(k, t); d0 = float(np.median(cKDTree(C0).query(Ct)[0]))
    _, tt, dt_ = icp(Ct, C0, False); R, tr, dr = icp(Ct, C0, True)
    ang = float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
    hz_ = tt - (tt @ nrm) * nrm
    print(f'f{t}: {len(Ct)} pts | median NN to f0 as composed by our VO {d0*100:.2f} cm | translation-only ICP correction '
          f'{np.linalg.norm(tt)*100:.2f} cm (horizontal {np.linalg.norm(hz_)*100:.2f}, vertical (+ up) {(tt @ nrm)*100:+.2f}; blue cup v(t) {((cen["blue_cup"][t]-cen["blue_cup"][0]) @ nrm)*100:+.2f}; along the blue step '
          f'{(tt @ ((cen["blue_cup"][t]-cen["blue_cup"][0]) / max(1e-9, np.linalg.norm(cen["blue_cup"][t]-cen["blue_cup"][0]))))*100:+.2f}) -> median {dt_*100:.2f} cm'
          f' | rigid ICP {np.linalg.norm(tr)*100:.2f} cm {ang:.2f} deg -> median {dr*100:.2f} cm')
# power check: if the camera at frame t were off by the blue cup's step, the composed background would be offset by it;
# shift frame t's background by that vector and confirm the same ICP finds it (recovered component along the step).
for k, t in ((2, 60), (3, 150)):
    Ct = cloud(k, t); step = cen['blue_cup'][t] - cen['blue_cup'][0]; ust = step / np.linalg.norm(step)
    _, tt, dt_ = icp(Ct + step, C0, False)
    print(f'power f{t}: background shifted by the blue step ({np.linalg.norm(step)*100:.2f} cm): median NN before ICP '
          f'{float(np.median(cKDTree(C0).query(Ct + step)[0]))*100:.2f} cm; ICP recovers {-(tt @ ust)*100:+.2f} cm along the step '
          f'(|t| {np.linalg.norm(tt)*100:.2f}) -> median {dt_*100:.2f} cm')
