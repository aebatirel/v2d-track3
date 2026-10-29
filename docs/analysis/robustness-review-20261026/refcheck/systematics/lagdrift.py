"""refcheck/systematics, check 2b: does the time offset between our object path and mocap DRIFT along the episode?

The public parquet carries two clocks: 'timestamp' on a uniform 0.049373 s grid (20.254 Hz) and 'capture_time' with
a 0.050 s median step (20.0 Hz, 1.2 ms jitter), so capture_time - timestamp grows by ~0.63 ms per frame (~0.19 s over
300 frames). Hypothesis H-drift: mocap row i is sampled on the 'timestamp' grid while video frame i is captured at
'capture_time', so our path (from video) lags mocap by (capture_i - timestamp_i)/dt + const frames: a lag slope of
~+0.0127 frames per frame. Falsified if the windowed lag has no slope (|slope| << 0.0127).
Estimator: speed profiles (scan-centroid speed, ours via the kit registration anchor, Gaussian sigma 1 frame), windows of
60 frames every 15 frames with mocap peak speed > 5 mm/frame, cross-correlation peak (parabolic sub-frame) per window.
Usage: python -I lagdrift.py OUT.json [--source auto|perc]
"""
import argparse, json, os, sys
import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sysload import *                                                     # noqa: E402,F401
import systematics as S                                                   # noqa: E402


def main():
    p = argparse.ArgumentParser(); p.add_argument('out'); p.add_argument('--source', default='auto')
    p.add_argument('--win', type=int, default=60); p.add_argument('--step', type=int, default=15)
    a = p.parse_args()
    C = canon(); rows = []; per_ep = {}
    for ep, e in sorted(C.items()):
        names, gt = load_gt(ep)
        tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['timestamp', 'capture_time']).to_pandas()
        off = (tab.capture_time.values - tab.timestamp.values) / np.median(np.diff(tab.timestamp.values))   # frames
        fin, _, _ = ref_files(e)
        if a.source == 'auto' and fin:
            ours, lib, src = load_ref_parquet(fin), REF_LIB[ep], 'ref'
        else:
            ours, lib, src = load_npz(f"{STORE}/{e['perception_path']}"), PERC_LIB[ep], 'perc'
        H = [S.host_geometry(n, s) for s, n in enumerate(names)]
        REG = [S.registration(ep, s, n, our_mesh_path(lib, n)) for s, n in enumerate(names)]
        T = len(gt[names[0]]); ep_rows = []
        for s, n in enumerate(names):
            po = centre_path(ours[n], REG[s]['anchor']); pg = centre_path(gt[n], H[s]['anchor'])
            vo, vg = S.speed(po), S.speed(pg)
            for st in range(0, max(1, T - a.win + 1), a.step):
                sl = slice(st, min(T, st + a.win))
                if vg[sl].max() < 0.005:
                    continue
                L, cmax, _ = S.xcorr_lag(vo[sl], vg[sl], maxlag=8)
                if cmax < 0.8:
                    continue
                c = st + a.win / 2
                ep_rows.append(dict(ep=ep, obj=n, centre=c, lag=L, peak=cmax, clock_offset_frames=float(off[int(min(T - 1, c))])))
        rows += ep_rows
        if ep_rows:
            c = np.array([r['centre'] for r in ep_rows]); L = np.array([r['lag'] for r in ep_rows])
            sl = float(np.polyfit(c, L, 1)[0]) if len(set(c)) > 2 else None
            per_ep[ep] = dict(source=src, windows=len(ep_rows), lag_median=round(float(np.median(L)), 2),
                              lag_first_half=round(float(np.median(L[c < T / 2])), 2) if (c < T / 2).any() else None,
                              lag_second_half=round(float(np.median(L[c >= T / 2])), 2) if (c >= T / 2).any() else None,
                              slope_frames_per_100=round(sl * 100, 3) if sl is not None else None, T=T,
                              clock_offset_slope_per_100=round(float(np.polyfit(np.arange(T), off, 1)[0] * 100), 3))
            print(ep, per_ep[ep], flush=True)
    c = np.array([r['centre'] for r in rows]); L = np.array([r['lag'] for r in rows]); w = np.array([r['peak'] for r in rows])
    eps = np.array([r['ep'] for r in rows])
    # pooled slope with a per-episode intercept (within-episode drift only)
    Lc = L.copy(); cc = c.copy()
    for ep in np.unique(eps):
        m = eps == ep; Lc[m] -= np.average(L[m], weights=w[m]); cc[m] -= np.average(c[m], weights=w[m])
    slope = float((w * cc * Lc).sum() / (w * cc * cc).sum())
    resid = Lc - slope * cc
    se = float(np.sqrt((w * resid ** 2).sum() / (w.sum() - 2) / (w * cc * cc).sum()))
    out = dict(source=a.source, windows=len(rows), pooled_within_episode_slope_frames_per_100=round(slope * 100, 3),
               slope_se_per_100=round(se * 100, 3), predicted_slope_if_mocap_on_timestamp_grid_per_100=1.27,
               lag_median_all_windows=round(float(np.median(L)), 2), lag_iqr=[round(float(q), 2) for q in np.percentile(L, [25, 75])],
               per_episode=per_ep, windows_list=rows)
    print({k: v for k, v in out.items() if k not in ('per_episode', 'windows_list')})
    json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
