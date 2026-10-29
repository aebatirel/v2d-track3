"""V3 (verify_systematics): lag drift with my own estimator. Model: our path ours(t) = gt(t - L(t)), L(t) = a + b t.
After a rigid fit, the residual e(t) ~ -(a + b t) v_gt(t); a and b by least squares over all moving objects,
iterated with the cubic-spline resampled path. Also a timestamp-grid test: resample mocap from its 'timestamp' grid
onto 'capture_time' and see whether the fit gets better or worse (H-drift says it gets better).
Perception paths, all public episodes except ep23 (identity swap). Usage: python -I v3_drift.py OUT.json"""
import json, os, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.interpolate import CubicSpline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V


def fit_ab(po, pg, iters=8):
    T = len(pg); t = np.arange(T); a = b = 0.0
    for _ in range(iters):
        L = a + b * t
        ps = np.stack([CubicSpline(t, po[:, k], axis=0)(np.clip(t + L, 0, T - 1)) for k in range(po.shape[1])], 1)
        _, Q, tt = V.kabsch(ps.reshape(-1, 3), pg.reshape(-1, 3))
        e = ps @ Q.T + tt - pg
        v = np.zeros_like(pg); v[1:-1] = (pg[2:] - pg[:-2]) / 2
        # e ~ (Lcur - Ltrue) v ; Ltrue = a' + b' t  =>  -e.v = (a'-a)|v|^2 + (b'-b) t |v|^2
        w = (v * v).sum(-1).sum(-1); y = -(e * v).sum(-1).sum(-1)
        da, db = np.linalg.solve(np.array([[w.sum(), (t * w).sum()], [(t * w).sum(), (t * t * w).sum()]]),
                                 np.array([y.sum(), (t * y).sum()]))
        a += da; b += db
    rms = float(np.sqrt((e ** 2).sum(-1).mean()) * 1000)
    return a, b, rms


out = {}
for ep in sorted(CE):
    if ep == 23:
        continue
    names, gt, _ = mocap(ep)
    d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
    Tt = np.load(tfp)['T_table_from_world']; P = perc(ep)
    ours = {n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}
    lib = V.LIB_PERC[ep]
    regs = [V.reg(ep, s, n, lib) for s, n in enumerate(names)]
    po = np.stack([ours[n][:, :3, :3] @ regs[s][0] + ours[n][:, :3, 3] for s, n in enumerate(names)], 1)
    pg = np.stack([gt[n][:, :3, :3] @ regs[s][2] + gt[n][:, :3, 3] for s, n in enumerate(names)], 1)
    mv = [s for s in range(len(names)) if np.linalg.norm(pg[:, s] - pg[0, s], axis=1).max() > 0.05]
    a, b, rms = fit_ab(po[:, mv], pg[:, mv])
    # H-drift test: mocap rows on the 'timestamp' grid, video frames on 'capture_time' => gt at capture times
    tb = pq.read_table(f'{T3D}/ep{ep}.parquet', columns=['timestamp', 'capture_time']).to_pandas()
    ts = tb.timestamp.values - tb.timestamp.values[0]; ct = tb.capture_time.values - tb.capture_time.values[0]
    pg_alt = CubicSpline(ts, pg, axis=0)(np.clip(ct, ts[0], ts[-1]))
    a2, b2, rms2 = fit_ab(po[:, mv], pg_alt[:, mv])
    T = len(pg)
    out[ep] = dict(T=T, moving=[names[s] for s in mv], lag_a=round(a, 3), drift_b_per100=round(b * 100, 3),
                   lag_mid=round(a + b * T / 2, 3), rms_mm=round(rms, 2),
                   if_mocap_on_timestamp_grid=dict(lag_a=round(a2, 3), drift_b_per100=round(b2 * 100, 3), rms_mm=round(rms2, 2)),
                   predicted_drift_per100=round(float((np.median(np.diff(tb.capture_time)) / np.median(np.diff(tb.timestamp)) - 1) * 100), 3))
    print(ep, out[ep], flush=True)
bs = np.array([v['drift_b_per100'] for v in out.values()]); b2 = np.array([v['if_mocap_on_timestamp_grid']['drift_b_per100'] for v in out.values()])
out['_summary'] = dict(n=len(bs), drift_per100_median=float(np.median(bs)), drift_per100_mean=float(bs.mean()), drift_se=float(bs.std(ddof=1) / np.sqrt(len(bs))),
                       alt_grid_drift_median=float(np.median(b2)),
                       rms_better_on_native_grid=int(sum(v['rms_mm'] <= v['if_mocap_on_timestamp_grid']['rms_mm'] for k, v in out.items() if k != '_summary')),
                       lag_mid_median=float(np.median([v['lag_mid'] for k, v in out.items() if k != '_summary'])))
print(out['_summary'])
json.dump(out, open(sys.argv[1], 'w'), indent=1)
