"""Stage B guided (tracking-mode) detection: for every z-visible marker in the det_<ep> sample, search a window around a
PREDICTED centre for a circle of the predicted radius (HoughCircles ALT, param2 0.55, radius 0.7-1.4 r, crop = window + 2.5 r, b/c crops upsampled 2x).
Predictions: 'oracle' = projection at the best GT shift (b/c -0.5, a -0.25 - delta), and 'pred' = the oracle projection
plus a random offset of OFF px (cam-a eq.) to emulate a tracker prior. Windows W = 6 and 15 px (cam-a eq.; b/c half).
hit = nearest circle to the prediction lies within max(0.5 r, 3 px a / 2 px b,c) of the TRUE (oracle) centre.
null = the same search 3 r away from the marker (false-alarm rate: any circle found in the window).
usage: guided17.py ep  -> out/guided_<ep>.npz"""
import sys, json, time, numpy as np, cv2
cv2.setNumThreads(2)
import lib17 as L
ep = int(sys.argv[1]); d = np.load(f'out/det_{ep}.npz'); MK = d['MK']; SH = d['SHIFTS']; ns = len(SH)
ia, ib = int(np.argmin(np.abs(SH + 0.25))), int(np.argmin(np.abs(SH + 0.5)))
vids = {c: L.Video(ep, c) for c in 'abc'}; FA = L.cam('a')[0][0, 0]; rng = np.random.default_rng(ep); t0 = time.time()
UP = {'a': 1, 'b': 2, 'c': 2}   # b/c searched on a 2x-upsampled crop (small radii)
def circles(Gi, uv, r, win, c):
    h = win + 2.5 * r; x0, y0 = int(uv[0] - h), int(uv[1] - h); s = int(2 * h) + 1
    if x0 < 0 or y0 < 0 or x0 + s > Gi.shape[1] or y0 + s > Gi.shape[0]: return None
    up = UP[c]; P = Gi[y0:y0 + s, x0:x0 + s]
    if up > 1: P = cv2.resize(P, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    P = cv2.GaussianBlur(P, (0, 0), 1.0)
    cs = cv2.HoughCircles(P, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=max(r * up, 3), param1=50, param2=0.55, minRadius=max(int(0.7 * r * up), 2), maxRadius=int(1.4 * r * up) + 1)
    return np.zeros((0, 3)) if cs is None else np.array([((a + 0.5) / up - 0.5 + x0, (b + 0.5) / up - 0.5 + y0, rr / up) for a, b, rr in cs[0]])
out = []; Gc = {}
for m in MK:
    t, ci, j, k, r, s, spd = int(m[0]), int(m[1]), int(m[2]), int(m[3]), m[4], int(m[5]), m[6]; c = 'abc'[ci]
    if (t, c) not in Gc:
        Gc.clear(); Gc[(t, c)] = cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY)
    G = Gc[(t, c)]; q = ia if ci == 0 else ib; u, v = m[7 + q], m[7 + ns + q]; sc = FA / L.cam(c)[0][0, 0]
    tol = max(0.5 * r, 3.0 if ci == 0 else 2.0); res = [t, ci, j, k, r, s, spd]
    for win in (6, 15):
        w = max(win / sc, 2.5)
        for off in (0.0, win / sc * 0.6):            # prediction offset (own px)
            a = rng.uniform(0, 2 * np.pi); pu, pv = u + off * np.cos(a), v + off * np.sin(a)
            cs = circles(G, (pu, pv), r, w, c)
            if cs is None: res += [np.nan, np.nan]; continue
            dp = np.hypot(cs[:, 0] - pu, cs[:, 1] - pv) if len(cs) else np.array([])
            ok = dp <= w
            if ok.any():
                i = np.flatnonzero(ok)[np.argmin(dp[ok])]; dt = np.hypot(cs[i, 0] - u, cs[i, 1] - v); res += [float(dt <= tol), dt]
            else: res += [0.0, np.nan]
        a = rng.uniform(0, 2 * np.pi); nu, nv = u + 3 * r * np.cos(a), v + 3 * r * np.sin(a)
        cs = circles(G, (nu, nv), r, w, c)
        res += [np.nan if cs is None else float(len(cs) > 0 and np.min(np.hypot(cs[:, 0] - nu, cs[:, 1] - nv)) <= w)]
    out.append(res)
np.savez(f'out/guided_{ep}.npz', A=np.array(out, np.float32),
         cols=np.array(['t', 'cam', 'j', 'k', 'r', 'seg', 'spd', 'w6_hit', 'w6_d', 'w6o_hit', 'w6o_d', 'w6_null', 'w15_hit', 'w15_d', 'w15o_hit', 'w15o_d', 'w15_null']),
         names=np.load(f'out/census_{ep}.npz')['names'])
print('done', ep, len(out), f'{time.time()-t0:.0f}s')
