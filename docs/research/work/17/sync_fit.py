"""Fit cam-a time offset delta (frames) and a corrected a->b extrinsic from per-frame a-vs-b_t PnP (a_pnp.py output):
T_meas(t) = VO(t)^-1 VO(t - delta) T_ext, VO interpolated (slerp/linear)."""
import sys, json, numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot, Slerp
import lib17 as L
ep = int(sys.argv[1]); z = np.load(f'out/apnp_{ep}.npz'); Tm, n = z['T'], z['n']
VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO); Tba = L.ext('a')
ok = np.flatnonzero(np.isfinite(Tm[:, 0, 0]) & (n >= 40)); ok = ok[(ok >= 3) & (ok < T - 3)]
sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo(tau):
    tau = np.clip(tau, 0, T - 1); i = np.clip(np.floor(tau).astype(int), 0, T - 2); f = tau - i
    M = np.zeros((len(tau), 4, 4)); M[:, 3, 3] = 1; M[:, :3, :3] = sl(tau).as_matrix(); M[:, :3, 3] = (1 - f)[:, None] * VO[i, :3, 3] + f[:, None] * VO[i + 1, :3, 3]; return M
def res(x, rot_w=1.0, tr_w=0.01):
    d = x[0]; E = np.eye(4); E[:3, :3] = Rot.from_rotvec(x[1:4]).as_matrix() @ Tba[:3, :3]; E[:3, 3] = Tba[:3, 3] + x[4:7]
    P = np.linalg.inv(VO[ok]) @ vo(ok - d) @ E
    rr = Rot.from_matrix(np.transpose(P[:, :3, :3], (0, 2, 1)) @ Tm[ok, :3, :3]).as_rotvec()
    tt = (Tm[ok, :3, 3] - P[:, :3, 3])
    return np.r_[np.degrees(rr).ravel() / 0.05, tt.ravel() / 0.003]
best = None
for d0 in (-2, -1, 0, 1, 2):
    s = least_squares(res, np.r_[d0, np.zeros(6)], loss='soft_l1', f_scale=2.0)
    if best is None or s.cost < best.cost: best = s
x = best.x; r = best.fun.reshape(2, -1) if False else best.fun
nr = len(ok) * 3
rr = r[:nr].reshape(-1, 3) * 0.05; tt = r[nr:].reshape(-1, 3) * 3
J = best.jac; cov = np.linalg.inv(J.T @ J) * np.median(np.abs(r)) ** 2 * 2.2
sd = np.sqrt(np.diag(cov))
print(f'ep {ep}: n {len(ok)}; delta = {x[0]:+.3f} +- {sd[0]:.3f} frames ({x[0]*50:+.1f} ms; a captured delta earlier than b at the same index)')
print(f'  extrinsic correction rot (deg) {np.round(np.degrees(x[1:4]),3)} +- {np.round(np.degrees(sd[1:4]),3)}; trans (mm) {np.round(x[4:7]*1000,1)} +- {np.round(sd[4:7]*1000,1)}')
print(f'  per-frame residual sd: rot {np.round(rr.std(0),3)} deg, trans {np.round(tt.std(0),1)} mm')
# compare with zero-delta, calibrated
r0 = res(np.zeros(7)); print(f'  calibrated & delta 0: rot rms {np.sqrt(np.mean((r0[:nr]*0.05)**2)):.3f} deg; fitted: {np.sqrt(np.mean(rr**2)):.3f} deg')
json.dump(dict(ep=ep, delta=float(x[0]), delta_sd=float(sd[0]), drot=x[1:4].tolist(), dtr=x[4:7].tolist(), res_rot_sd=rr.std(0).tolist(), res_tr_sd_mm=tt.std(0).tolist()), open(f'out/sync_{ep}.json', 'w'))
