"""Stage C: marker layout calibration in the GT body frame from public REST frames (training use of public GT).
For each rest frame (step S), camera and z-visible marker (stage-B census), HoughCircles in a +-W px (a-eq) window around the
GT projection (stage-A cameras), best LOEO-classifier candidate with score >= 0.3 and radius ratio 0.6-1.6 -> observation.
Per marker: body-frame point X minimising robust reprojection error over all observations (GT pose + stage-A camera).
Prints offsets vs the scan catalogue (mm) and per-camera residuals. -> c/calib_<ep>.json
usage: c/calib17.py ep [S=2] [W=14]"""
import sys, json, pickle, numpy as np, cv2
from scipy.optimize import least_squares
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D, seg17
cv2.setNumThreads(2)
ep = int(sys.argv[1]); S = int(sys.argv[2]) if len(sys.argv) > 2 else 2; W = float(sys.argv[3]) if len(sys.argv) > 3 else 14
gt = L.load_gt(ep); seg = seg17.segments(gt)[0]; RG = json.load(open(f'out/reg2_{ep}.json')); z = np.load(f'out/census_{ep}.npz'); VIS = z['VIS']
CLF = pickle.load(open(f'c/clf_{ep}.pkl', 'rb'))   # own models (c/train_loeo.py), target ep not in training
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a']); FA = L.cam('a')[0][0, 0]; DL = RG['delta']
vids = {c: L.Video(ep, c) for c in 'abc'}; OBS = []
def hough(G, c, rmin, rmax):
    up = 1 if c == 'a' else 2
    g = cv2.resize(G, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC) if up != 1 else G
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    cs = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=3, param1=40, param2=0.5, minRadius=max(int(rmin * up), 5 if c == 'a' else 6), maxRadius=min(int(np.ceil(rmax * up)) + 1, 40))
    if cs is None: return np.zeros((0, 3))
    cs = cs[0].astype(float); cs[:, :2] = (cs[:, :2] + 0.5) / up - 0.5; cs[:, 2] /= up; return cs
for t in range(0, T, S):
    for ci, c in enumerate('abc'):
        R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); tau = t - 0.5 - (DL if c == 'a' else 0)
        G = None
        for j, n in enumerate(gt['names']):
            if n not in L.CAT or seg[t, j] != 0: continue
            uv, zz, rp = D.project_markers(gt, j, tau, R, C, c)
            for k in range(len(uv)):
                if not VIS[t, ci, j, k]: continue
                if G is None: BGR = vids[c].get(t); G = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY)
                w = W * L.cam(c)[0][0, 0] / FA; m = w + 2.5 * rp[k] + 6
                x0, y0 = int(max(uv[k, 0] - m, 0)), int(max(uv[k, 1] - m, 0)); x1, y1 = int(min(uv[k, 0] + m, G.shape[1])), int(min(uv[k, 1] + m, G.shape[0]))
                if x1 - x0 < 12 or y1 - y0 < 12: continue
                cs = hough(G[y0:y1, x0:x1], c, 0.6 * rp[k], 1.6 * rp[k])
                if len(cs) == 0: continue
                d = np.hypot(cs[:, 0] + x0 - uv[k, 0], cs[:, 1] + y0 - uv[k, 1]); ok = (d <= w) & (cs[:, 2] / rp[k] > 0.6) & (cs[:, 2] / rp[k] < 1.6)
                if not ok.any(): continue
                cs = cs[ok]; P = D.prep_image(G[y0:y1, x0:x1], BGR[y0:y1, x0:x1] if c == 'a' else None)
                s = CLF['a' if c == 'a' else 'bc'].predict_proba(D.features2(P, cs.astype(np.float64)).astype(np.float16).astype(np.float32))[:, 1]
                b = int(np.argmax(s))
                if s[b] >= 0.3: OBS.append((t, ci, j, k, cs[b, 0] + x0, cs[b, 1] + y0, cs[b, 2], s[b], rp[k]))
    if t % 40 == 0: print('t', t, len(OBS), flush=True)
OBS = np.array(OBS); out = {}
for j, n in enumerate(gt['names']):
    if n not in L.CAT: continue
    M = np.array([q['c'] for q in L.CAT[n]]); out[n] = []
    for k in range(len(M)):
        o = OBS[(OBS[:, 2] == j) & (OBS[:, 3] == k)] if len(OBS) else np.zeros((0, 9))
        if len(o) < 6: out[n].append(None); print(f'{n} k{k}: {len(o)} obs (skip)'); continue
        poses = [D.gt_interp(gt, j, oo[0] - 0.5 - (DL if oo[1] == 0 else 0)) for oo in o]
        def res(X):
            r = []
            for oo, (Rj, tj) in zip(o, poses):
                c = 'abc'[int(oo[1])]; t = int(oo[0]); uv, _ = L.project((X @ Rj.T + tj)[None], np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']), c, own=True)
                sc = FA / L.cam(c)[0][0, 0]; r += [(uv[0, 0] - oo[4]) * sc, (uv[0, 1] - oo[5]) * sc]
            return np.array(r)
        r0 = res(M[k]); f = least_squares(res, M[k], loss='cauchy', f_scale=3.0); r1 = f.fun.reshape(-1, 2)
        dX = (f.x - M[k]) * 1000; ncam = [int(np.sum(o[:, 1] == ci)) for ci in range(3)]
        print(f'{n} k{k} ({L.CAT[n][k]["size"]}): n {len(o)} (a/b/c {ncam}), res a-eq px before {np.median(np.hypot(*r0.reshape(-1,2).T)):.2f} after {np.median(np.hypot(*r1.T)):.2f}; offset mm ({dX[0]:+.1f}, {dX[1]:+.1f}, {dX[2]:+.1f}) |{np.linalg.norm(dX):.1f}|', flush=True)
        out[n].append(dict(X=f.x.tolist(), n=len(o), ncam=ncam, off_mm=dX.tolist(), res_before=float(np.median(np.hypot(*r0.reshape(-1, 2).T))), res_after=float(np.median(np.hypot(*r1.T)))))
json.dump(out, open(f'c/calib_{ep}.json', 'w'), indent=1); np.save(f'c/calib_obs_{ep}.npy', OBS); print('done')
