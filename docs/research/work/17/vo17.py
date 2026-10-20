"""Stereo VO on the ego mono pair (b = right/reference, c = left; 75 mm baseline), metric, in the frame of b at f0.
Per frame: SIFT in b and c, b-c matches with the calibrated epipolar constraint, triangulation (metric). Tracking:
b_t keypoints matched to a keyframe map (3D in world=b0 coords) -> PnP RANSAC + LM refine. New keyframe when the
inlier count drops. Final: windowed refinement not done (raw tracking). Output: T_w_b[t] (4x4, b-frame pose in b0)."""
import sys, json, numpy as np, cv2, time
import lib17 as L
ep = int(sys.argv[1]); split = sys.argv[2] if len(sys.argv) > 2 else 'public'
Kb, db, _ = L.cam('b'); Kc, dc, _ = L.cam('c')
Tbc = L.ext('c'); Rbc, tbc = Tbc[:3, :3], Tbc[:3, 3]        # X_b = Rbc X_c + tbc
E = np.array([[0, -tbc[2], tbc[1]], [tbc[2], 0, -tbc[0]], [-tbc[1], tbc[0], 0]]) @ Rbc   # x_b^T E x_c = 0
Pb = np.hstack([np.eye(3), np.zeros((3, 1))]); Pc = np.hstack([Rbc.T, (-Rbc.T @ tbc)[:, None]])
sift = cv2.SIFT_create(nfeatures=4000, contrastThreshold=0.02)
bf = cv2.BFMatcher(cv2.NORM_L2)
def norm(K, d, pts): return cv2.undistortPoints(pts.reshape(-1, 1, 2).astype(np.float64), K, d).reshape(-1, 2)
def stereo(gb, gc):
    kb, Db = sift.detectAndCompute(gb, None); kc, Dc = sift.detectAndCompute(gc, None)
    pb = np.array([k.pt for k in kb]); pc = np.array([k.pt for k in kc])
    nb, nc = norm(Kb, db, pb), norm(Kc, dc, pc)
    m = bf.knnMatch(Db, Dc, k=2)
    ib, ic = [], []
    for x in m:
        if len(x) == 2 and x[0].distance < 0.8 * x[1].distance: ib.append(x[0].queryIdx); ic.append(x[0].trainIdx)
    ib, ic = np.array(ib), np.array(ic)
    xb = np.c_[nb[ib], np.ones(len(ib))]; xc = np.c_[nc[ic], np.ones(len(ic))]
    l = xc @ E.T  # epipolar lines in b for points in c: x_b^T (E x_c)
    dist = np.abs((xb * l).sum(1)) / np.linalg.norm(l[:, :2], axis=1) * Kb[0, 0]
    ok = dist < 1.5
    ib, ic = ib[ok], ic[ok]
    X = cv2.triangulatePoints(Pb, Pc, nb[ib].T, nc[ic].T); X = (X[:3] / X[3]).T
    # reprojection & depth checks
    rb = np.linalg.norm(X[:, :2] / X[:, 2:3] - nb[ib], axis=1) * Kb[0, 0]
    Xc = X @ Rbc - (Rbc.T @ tbc) * 0 - tbc @ Rbc  # X_c = Rbc^T (X_b - tbc)
    Xc = (X - tbc) @ Rbc
    rc = np.linalg.norm(Xc[:, :2] / Xc[:, 2:3] - nc[ic], axis=1) * Kc[0, 0]
    ok = (X[:, 2] > 0.2) & (X[:, 2] < 12) & (rb < 1.0) & (rc < 1.0) & (Xc[:, 2] > 0.2)
    return dict(kb=pb, nb=nb, Db=Db, sb=np.array([k.size for k in kb]), sidx=ib[ok], X=X[ok])
if __name__ == '__main__':
    vb, vc = L.Video(ep, 'b', split), L.Video(ep, 'c', split)
    T = int(vb.cap.get(cv2.CAP_PROP_FRAME_COUNT)); poses = [np.eye(4)]; log = []
    gb, gc = cv2.cvtColor(vb.get(0), cv2.COLOR_BGR2GRAY), cv2.cvtColor(vc.get(0), cv2.COLOR_BGR2GRAY)
    s = stereo(gb, gc); kf = dict(t=0, Tw=np.eye(4), Xw=s['X'], D=s['Db'][s['sidx']]); kfs = [kf]
    t0 = time.time()
    for t in range(1, T):
        gb, gc = cv2.cvtColor(vb.get(t), cv2.COLOR_BGR2GRAY), cv2.cvtColor(vc.get(t), cv2.COLOR_BGR2GRAY)
        s = stereo(gb, gc)
        Tprev = poses[-1]; best = None
        for kfc in [kf] + [k for k in reversed(kfs[-4:]) if k['t'] != kf['t']]:
            m = bf.knnMatch(s['Db'], kfc['D'], k=2)
            qm = [(x[0].queryIdx, x[0].trainIdx) for x in m if len(x) == 2 and x[0].distance < 0.8 * x[1].distance]
            if len(qm) < 12: continue
            qi, mi = map(np.array, zip(*qm))
            ok, rv, tv, inl = cv2.solvePnPRansac(kfc['Xw'][mi], s['nb'][qi], np.eye(3), None, iterationsCount=500,
                                                  reprojectionError=2.5 / Kb[0, 0], confidence=0.999, flags=cv2.SOLVEPNP_AP3P)
            ninl = 0 if (inl is None or not ok) else len(inl)
            if ninl >= 30:
                inl = inl.ravel(); rv, tv = cv2.solvePnPRefineLM(kfc['Xw'][mi[inl]], s['nb'][qi[inl]], np.eye(3), None, rv, tv)
                Rcw, _ = cv2.Rodrigues(rv); pr = kfc['Xw'][mi] @ Rcw.T + tv.ravel()
                e = np.linalg.norm(pr[:, :2] / pr[:, 2:3] - s['nb'][qi], axis=1) * Kb[0, 0]; inl = np.flatnonzero(e < 1.5)
                if len(inl) >= 30:
                    rv, tv = cv2.solvePnPRefineLM(kfc['Xw'][mi[inl]], s['nb'][qi[inl]], np.eye(3), None, rv, tv)
                    Rcw, _ = cv2.Rodrigues(rv); pr = kfc['Xw'][mi[inl]] @ Rcw.T + tv.ravel()
                    med = float(np.median(np.linalg.norm(pr[:, :2] / pr[:, 2:3] - s['nb'][qi[inl]], axis=1) * Kb[0, 0]))
                    Tcw = np.eye(4); Tcw[:3, :3] = Rcw; Tcw[:3, 3] = tv.ravel()
                    if best is None or len(inl) > best[1]: best = (np.linalg.inv(Tcw), len(inl), med, len(qi), kfc['t'])
                    if len(inl) >= 0.5 * len(kfc['Xw']): break
        if best is not None: Tw, ninl, med, nm, kft = best; okf = True
        else: Tw, ninl, med, nm, kft = Tprev, 0, np.nan, 0, -1; okf = False
        poses.append(Tw)
        log.append(dict(t=t, nmatch=nm, ninl=ninl, med_px=med, nstereo=len(s['X']), kf=kft, ok=okf))
        if okf and (ninl < 0.45 * len(kf['Xw']) or t - kf['t'] >= 40):
            kf = dict(t=t, Tw=Tw, Xw=s['X'] @ Tw[:3, :3].T + Tw[:3, 3], D=s['Db'][s['sidx']]); kfs.append(kf)
        if t % 20 == 0: print(t, log[-1], f'{time.time()-t0:.0f}s', flush=True)
    np.save(f'out/vo_{split}_{ep}.npy', np.array(poses)); json.dump(log, open(f'out/vo_{split}_{ep}.json', 'w'))
    print('done', time.time() - t0)
