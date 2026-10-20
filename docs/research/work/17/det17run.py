"""Stage B automatic sphere detector, pass 1: candidates + labels + features (no pose prior at detection time).
Candidates: HoughCircles(HOUGH_GRADIENT_ALT, param2 P2) on the full-res grey image (cam a) or the 2x-upsampled
image (cams b/c), radius 5-40 px (a) / 3-20 px (b, c) (own px). Labels (analysis only, public GT): projected marker centres with GT
interpolated at t + SH (b/c clock; cam a also - delta) through the stage-A cameras; positive = within
max(0.5 r, 3 px a / 2 px b,c) and radius ratio 0.6-1.6 of a z-visible marker; ignore = within 1.2 r of any projected
marker that is not a positive match; else negative.
Saves all candidates (t, cam, x, y, r, label, marker id j*10+k, roi bitmask, seg, fullframe flag) and features (float16) for positives,
30 % of in-ROI negatives and 3 % of other negatives (fidx = row index, fw = inverse sampling weight).
MK: z-visible markers (t, cam, j, k, r, seg, speed, u at SHIFTS..., v at SHIFTS...); SHIFTS = absolute GT shift (b/c clock).
usage: [SH=-0.5 P2=0.5] det17run.py ep step   -> out/det_<ep>.npz"""
import sys, os, json, time, numpy as np, cv2
cv2.setNumThreads(2)
import lib17 as L, det17lib as D, seg17
ep, step = int(sys.argv[1]), int(sys.argv[2]); SH = float(os.environ.get('SH', -0.5)); P2 = float(os.environ.get('P2', 0.5))
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); z = np.load(f'out/census_{ep}.npz'); seg = seg17.segments(gt)[0]
VIS, SPD = z['VIS'], z['SPD']
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a']); N = len(gt['names'])
vids = {c: L.Video(ep, c) for c in 'abc'}; t0 = time.time()
def hough(G, c):
    up = 1 if c == 'a' else 2
    g = cv2.resize(G, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC) if up != 1 else G
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    cs = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=3, param1=40, param2=P2, minRadius=5 if c == "a" else 6, maxRadius=40)
    if cs is None: return np.zeros((0, 3))
    cs = cs[0].astype(float); cs[:, :2] = (cs[:, :2] + 0.5) / up - 0.5; cs[:, 2] /= up; return cs
SHIFTS = np.arange(-2.0, 1.01, 0.25) - SH; IS0 = int(np.argmin(np.abs(SHIFTS))); MK = []
rows, feats, fidx, fw = [], [], [], []; rng = np.random.default_rng(ep)
FF = int(os.environ.get('FF', 4))  # every FF-th sampled frame: full-frame Hough; otherwise Hough inside the union of object ROIs
for it, t in enumerate(range(0, T, step)):
    ff = (it % FF == 0)
    for ci, c in enumerate('abc'):
        BGR = vids[c].get(t); G = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY)
        R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); tau = t + SH - (RG['delta'] if c == 'a' else 0)
        W_, H_ = L.cam(c)[2]; boxes = []; proj = []
        for j in range(N):
            uv, zz, rp = D.project_markers(gt, j, tau, R, C, c); proj.append((uv, zz, rp))
            # object ROI: bbox of projected scan surface (subsampled), dilated by 3 x median marker radius
            Xs = L.surf(gt['names'][j])[::50]; Rj, tj = D.gt_interp(gt, j, tau)
            ps, zs = L.project(Xs @ Rj.T + tj, R, C, c, own=True); ps = ps[zs > 0.05]
            if len(ps):
                mg = 3 * np.median(rp); x0, y0 = ps.min(0) - mg; x1, y1 = ps.max(0) + mg; boxes.append((j, x0, y0, x1, y1))
        if ff: H = hough(G, c)
        else:
            vb = [b for b in boxes if b[3] > 0 and b[4] > 0 and b[1] < W_ and b[2] < H_]
            if not vb: continue
            X0 = int(max(min(b[1] for b in vb), 0)); Y0 = int(max(min(b[2] for b in vb), 0))
            X1 = int(min(max(b[3] for b in vb), W_)); Y1 = int(min(max(b[4] for b in vb), H_))
            if X1 - X0 < 16 or Y1 - Y0 < 16: continue
            H = hough(G[Y0:Y1, X0:X1], c)
            if len(H): H[:, 0] += X0; H[:, 1] += Y0
        if len(H) == 0: continue
        lab = np.zeros(len(H), int); mid = np.full(len(H), -1); best = np.full(len(H), np.inf); roi = np.zeros(len(H), int)
        for (j, x0, y0, x1, y1) in boxes:
            roi |= ((H[:, 0] >= x0) & (H[:, 0] <= x1) & (H[:, 1] >= y0) & (H[:, 1] <= y1)).astype(int) << j
        for j in range(N):
            uv, zz, rp = proj[j]
            for k in range(len(uv)):
                if not (zz[k] > 0.05): continue
                d = np.hypot(H[:, 0] - uv[k, 0], H[:, 1] - uv[k, 1]); rr = H[:, 2] / rp[k]
                vis = bool(VIS[t, ci, j, k])
                rad = max(0.5 * rp[k], 3.0 if c == 'a' else 2.0)
                ok = vis & (d < rad) & (rr > 0.6) & (rr < 1.6)
                upd = ok & (d < best); lab[upd] = 1; mid[upd] = j * 10 + k; best[upd] = d[upd]
                near = (d < 1.2 * rp[k]) & (lab != 1); lab[near] = -1
        # z-visible markers with projections at alternative GT shifts (for the GT-video time-offset test)
        for j in range(N):
            for k in range(z['nk'][j]):
                if not VIS[t, ci, j, k]: continue
                pr = [D.project_markers(gt, j, tau + ds, R, C, c) for ds in SHIFTS]
                MK.append(np.r_[t, ci, j, k, pr[IS0][2][k], seg[t, j], SPD[t, ci, j, k], [p[0][k, 0] for p in pr], [p[0][k, 1] for p in pr]])
        u = rng.random(len(H)); sel = (lab == 1) | ((lab == 0) & (roi > 0) & (u < 0.3)) | ((lab == 0) & (roi == 0) & (u < 0.03))
        F = D.features(G, BGR if c == 'a' else None, np.c_[H[sel], np.zeros(sel.sum()), np.ones(sel.sum())]).astype(np.float16)
        n0 = len(rows)
        for i in range(len(H)):
            rows.append((t, ci, H[i, 0], H[i, 1], H[i, 2], lab[i], mid[i], roi[i], seg[t, mid[i] // 10] if mid[i] >= 0 else -1, ff))
        feats.append(F); fidx.append(n0 + np.flatnonzero(sel)); fw.append(np.where(lab[sel] == 1, 1.0, np.where(roi[sel] > 0, 1 / 0.3, 1 / 0.03)))
    if t % (10 * step) == 0: print(f'ep {ep} t {t}/{T} rows {len(rows)} {time.time()-t0:.0f}s', flush=True)
np.savez_compressed(f'out/det_{ep}.npz', rows=np.array(rows, np.float32), F=np.vstack(feats), fidx=np.concatenate(fidx), fw=np.concatenate(fw), seg=seg, SH=SH, P2=P2, step=step, MK=np.array(MK, np.float32), SHIFTS=SHIFTS + SH)
print('done', time.time() - t0)
