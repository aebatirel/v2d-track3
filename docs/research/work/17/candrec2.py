"""Candidate recall of full-frame HoughCircles ALT (and DoG with loose matching). usage: candrec2.py ep step p2 [halfa]"""
import sys, json, time, numpy as np, cv2
import lib17 as L, det17lib as D, seg17
import os; UP = int(os.environ.get('UP', 1)); CAMS = os.environ.get('CAMS', 'abc')
ep, step, p2 = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]); halfa = len(sys.argv) > 4 and sys.argv[4] == '1'; SH = -0.5
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); z = np.load(f'out/census_{ep}.npz'); seg = seg17.segments(gt)[0]
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a']); N = len(gt['names'])
vids = {c: L.Video(ep, c) for c in 'abc'}; res = []; ncand = {c: [] for c in 'abc'}; t0 = time.time()
def hough(G, c):
    sc = 2.0 if (c == 'a' and halfa) else (1.0 / UP if c != 'a' else 1.0)
    g = cv2.resize(G, None, fx=1 / sc, fy=1 / sc, interpolation=cv2.INTER_AREA if sc > 1 else cv2.INTER_CUBIC) if sc != 1 else G
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    rmin, rmax = (6, 40) if ((c == 'a' and not halfa) or (c != 'a' and UP == 2)) else (3, 20)
    cs = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=3, param1=40, param2=p2, minRadius=rmin, maxRadius=rmax)
    return np.zeros((0, 3)) if cs is None else cs[0] * sc
for t in range(0, T, step):
    for ci, c in enumerate('abc'):
        if c not in CAMS: continue
        G = cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY); H = hough(G, c); ncand[c].append(len(H))
        R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); tau = t + SH - (RG['delta'] if c == 'a' else 0)
        for j in range(N):
            uv, zz, rp = D.project_markers(gt, j, tau, R, C, c)
            for k in range(len(uv)):
                if not z['VIS'][t, ci, j, k]: continue
                rad = max(0.5 * rp[k], 3.0 if c == 'a' else 2.0)
                d = np.hypot(H[:, 0] - uv[k, 0], H[:, 1] - uv[k, 1]) if len(H) else np.array([np.inf])
                res.append((ci, seg[t, j], rp[k], d.min() / rp[k], (d < rad).any(), (d < rp[k]).any()))
print(f'{time.time()-t0:.0f}s; circles per image med', {c: int(np.median(v)) for c, v in ncand.items() if v})
A = np.array(res, float)
for ci, c in enumerate('abc'):
    for s in range(3):
        m = (A[:, 0] == ci) & (A[:, 1] == s)
        if m.any(): print(f'cam {c} seg {s} n {m.sum():4d} recall(<max(.5r,3px)) {A[m,4].mean():.2f} recall(<r) {A[m,5].mean():.2f}; med rpx {np.median(A[m,2]):.1f}')
