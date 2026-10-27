"""Toy 1-D comparison: causal filters vs offline smoothers on a rest/lift/carry/place/rest trajectory.
Synthetic only (white noise + sparse outliers); not our data."""
import numpy as np
from scipy.signal import butter, filtfilt, savgol_filter

fs = 20.0; dt = 1 / fs; T = 13.0
t = np.arange(0, T, dt); N = len(t)

def minjerk(t, t0, t1, a, b):
    s = np.clip((t - t0) / (t1 - t0), 0, 1)
    return a + (b - a) * (10 * s**3 - 15 * s**4 + 6 * s**5)

def truth(lift_dur):
    z = np.zeros(N)
    z += minjerk(t, 3.0, 3.0 + lift_dur, 0, 0.15)
    z -= minjerk(t, 6.0, 6.0 + lift_dur, 0, 0.15)
    x = minjerk(t, 3.0 + lift_dur, 5.5, 0, 0.30)
    return z, x

def kf_cv(y, q, r, w=None):
    # constant-velocity KF + RTS; w: per-sample measurement weights (robust IRLS)
    F = np.array([[1, dt], [0, 1]]); H = np.array([[1.0, 0.0]])
    Q = q * np.array([[dt**3 / 3, dt**2 / 2], [dt**2 / 2, dt]])
    x = np.array([y[0], 0.0]); P = np.diag([r, 1.0])
    xs_p, Ps_p, xs_f, Ps_f = [], [], [], []
    for k in range(len(y)):
        if k > 0:
            x = F @ x; P = F @ P @ F.T + Q
        xs_p.append(x.copy()); Ps_p.append(P.copy())
        rk = r / (w[k] if w is not None else 1.0)
        S = H @ P @ H.T + rk; K = P @ H.T / S
        x = x + (K * (y[k] - H @ x)).ravel(); P = (np.eye(2) - K @ H) @ P
        xs_f.append(x.copy()); Ps_f.append(P.copy())
    xs_f = np.array(xs_f); xs_s = xs_f.copy(); Ps_s = list(Ps_f)
    for k in range(len(y) - 2, -1, -1):
        C = Ps_f[k] @ F.T @ np.linalg.inv(Ps_p[k + 1])
        xs_s[k] = xs_f[k] + C @ (xs_s[k + 1] - xs_p[k + 1])
        Ps_s[k] = Ps_f[k] + C @ (Ps_s[k + 1] - Ps_p[k + 1]) @ C.T
    return xs_f[:, 0], xs_s[:, 0], xs_s[:, 1]

def robust_rts(y, q, r, nu=4.0, iters=5):
    w = np.ones(len(y))
    for _ in range(iters):
        _, s, v = kf_cv(y, q, r, w)
        e2 = (y - s)**2 / r
        w = (nu + 1) / (nu + e2)  # Student-t IRLS weights
    return s, v

def one_euro(y, mincutoff=1.0, beta=0.0, dcutoff=1.0):
    def alpha(fc):
        tau = 1 / (2 * np.pi * fc); return 1 / (1 + tau / dt)
    out = np.zeros_like(y); xh = y[0]; dxh = 0.0
    for k in range(len(y)):
        if k == 0:
            out[k] = xh; continue
        dx = (y[k] - xh) / dt
        a_d = alpha(dcutoff); dxh = a_d * dx + (1 - a_d) * dxh
        fc = mincutoff + beta * abs(dxh); a = alpha(fc)
        xh = a * y[k] + (1 - a) * xh; out[k] = xh
    return out

def rest_snap(y, s, v, vthr=0.02, min_len=10):
    out = s.copy(); rest = np.abs(v) < vthr
    k = 0
    while k < len(y):
        if rest[k]:
            j = k
            while j < len(y) and rest[j]: j += 1
            if j - k >= min_len:
                # shrink 2 frames at each end to avoid eating motion onsets
                a, b = k + 2, j - 2
                if b > a: out[a:b] = np.median(y[a:b])
            k = j
        else:
            k += 1
    return out

def metrics(est, gt, motion):
    e = est - gt
    acc = np.diff(est, 2) / dt**2; acc_gt = np.diff(gt, 2) / dt**2
    return dict(rmse_mm=1e3 * np.sqrt(np.mean(e**2)),
                rest_rmse_mm=1e3 * np.sqrt(np.mean(e[~motion]**2)),
                motion_max_mm=1e3 * np.max(np.abs(e[motion])),
                acc_rms_err=np.sqrt(np.mean((acc - acc_gt)**2)),
                rest_path_mm=1e3*np.sum(np.abs(np.diff(est))[~motion[1:] & ~motion[:-1]]))

rng = np.random.default_rng(0)
results = {}
for lift_dur in [0.5, 0.25]:
    z, _ = truth(lift_dur)
    motion = (np.abs(np.gradient(z, dt)) > 1e-3)
    sig = 0.005
    agg = {}
    for trial in range(60):
        y = z + sig * rng.standard_normal(N)
        out_idx = rng.random(N) < 0.03
        y[out_idx] += 0.05 * rng.choice([-1, 1], out_idx.sum())
        cand = {'raw': y}
        for q in [0.03, 0.3, 3.0]:
            f, s, v = kf_cv(y, q, sig**2)
            cand[f'KF-CV q={q:g}'] = f; cand[f'RTS-CV q={q:g}'] = s
            rs, rv = robust_rts(y, q, sig**2)
            cand[f'robustRTS q={q:g}'] = rs
            cand[f'robustRTS+restsnap q={q:g}'] = rest_snap(y, rs, robust_rts(y, 0.03, sig**2)[1])
        for fc in [2.0, 4.0]:
            b, a = butter(2, fc / (fs / 2)); cand[f'filtfilt {fc:g}Hz'] = filtfilt(b, a, y)
        cand['savgol w9 p3'] = savgol_filter(y, 9, 3)
        cand['1euro fc=1 b=0'] = one_euro(y, 1.0, 0.0)
        cand['1euro fc=1 b=20'] = one_euro(y, 1.0, 20.0)
        for k_, v_ in cand.items():
            m = metrics(v_, z, motion)
            for mk, mv in m.items():
                agg.setdefault(k_, {}).setdefault(mk, []).append(mv)
    results[lift_dur] = {k: {mk: np.mean(mv) for mk, mv in d.items()} for k, d in agg.items()}

for lift_dur, res in results.items():
    print(f'\n== lift/place duration {lift_dur}s (0.15 m), noise 5 mm + 3% outliers of 5 cm, 20 fps, 200 trials ==')
    print(f"{'method':32s} {'RMSE':>7s} {'restRMSE':>9s} {'motionMax':>10s} {'accErrRMS':>10s} {'restPath':>9s}")
    for k, m in res.items():
        print(f"{k:32s} {m['rmse_mm']:7.2f} {m['rest_rmse_mm']:9.2f} {m['motion_max_mm']:10.1f} {m['acc_rms_err']:10.2f} {m['rest_path_mm']:9.0f}")
