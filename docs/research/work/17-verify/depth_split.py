"""Verifier (evaluation only): split prior and fused translation errors on fix frames into the component along the cam-b viewing
ray (depth) and the lateral part; regress fused error on prior error per direction (slope ~1 = markers do not correct that
direction, ~0 = fully corrected). Run with cwd work/17 (or a dir with out/ symlink). usage: depth_split.py npz ..."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
import ev17 as E, lib17 as L, det17lib as D
for fn in sys.argv[1:]:
    z, ep = E.load(fn); T = int(z['T']); gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json'))
    Cb = np.array([RG['cams_b'][t]['C'] for t in range(T)])
    for i, n in enumerate(z['objs']):
        j = gt['names'].index(n); st = z[f'status_{i}'][:T]; fx = np.where(st >= 2)[0]
        if len(fx) < 5: continue
        _, tf = E.to_mocap(z, ep, i, T); _, tq = E.to_mocap(z, ep, i, T, 'p')
        tg = np.array([D.gt_interp(gt, j, t - 0.5)[1] for t in range(T)])
        ray = tg - Cb; ray /= np.linalg.norm(ray, axis=1, keepdims=True)
        ef, ep_ = (tf - tg)[fx] * 1000, (tq - tg)[fx] * 1000; r = ray[fx]
        df, dp = np.sum(ef * r, 1), np.sum(ep_ * r, 1); lf, lp = ef - df[:, None] * r, ep_ - dp[:, None] * r
        slope_d = np.polyfit(dp, df, 1)[0]
        # lateral: project onto 2 fixed lateral axes per frame
        u = np.cross(r, [0, 0, 1.0]); u /= np.linalg.norm(u, axis=1, keepdims=True); v = np.cross(r, u)
        pf = np.r_[np.sum(lf * u, 1), np.sum(lf * v, 1)]; pp = np.r_[np.sum(lp * u, 1), np.sum(lp * v, 1)]
        slope_l = np.polyfit(pp, pf, 1)[0]
        print(f'{fn.split("/")[-1]} {n} fix {len(fx)} (3m {np.sum(st[fx]==3)}): depth |err| med prior {np.median(np.abs(dp)):.1f} -> fused {np.median(np.abs(df)):.1f} mm, slope {slope_d:.2f}, corr {np.corrcoef(dp, df)[0,1]:.2f}; lateral norm med prior {np.median(np.linalg.norm(lp,axis=1)):.1f} -> fused {np.median(np.linalg.norm(lf,axis=1)):.1f} mm, slope {slope_l:.2f}; fused mean depth bias {np.mean(df):+.1f}', flush=True)
