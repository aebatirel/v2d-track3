"""Integer frame-shift test between cam a and the mono pair: PnP of a_t against stereo(b,c)_{t+s}; the deviation of the
measured a->b transform from the calibrated extrinsic is minimal at the true shift."""
import sys, numpy as np, cv2
import lib17 as L
argv = sys.argv; sys.argv = [argv[0], argv[1]]
import vo17 as V
ep = int(argv[1]); step = int(argv[2]) if len(argv) > 2 else 3
Ka, da, _ = L.cam('a'); Tba = L.ext('a'); Tab = np.linalg.inv(Tba)
VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO)
va, vb, vc = L.Video(ep, 'a'), L.Video(ep, 'b'), L.Video(ep, 'c')
g = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.02)
S = {t: V.stereo(g(vb.get(t)), g(vc.get(t))) for t in range(T)}
res = {s: [] for s in (-2, -1, 0, 1, 2)}
for t in range(2, T - 2, step):
    A = cv2.resize(g(va.get(t)), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA); ka, Da = sift.detectAndCompute(A, None)
    pa = (np.array([k.pt for k in ka]) + 0.5) * 2 - 0.5; na = cv2.undistortPoints(pa.reshape(-1, 1, 2), Ka, da).reshape(-1, 2)
    for s in res:
        st = S[t + s]; m = V.bf.knnMatch(Da, st['Db'][st['sidx']], k=2)
        qm = [(x[0].queryIdx, x[0].trainIdx) for x in m if len(x) == 2 and x[0].distance < 0.8 * x[1].distance]
        if len(qm) < 15: continue
        qi, mi = map(np.array, zip(*qm)); X = st['X'][mi]; rv0, _ = cv2.Rodrigues(Tab[:3, :3])
        ok, rv, tv, inl = cv2.solvePnPRansac(X, na[qi], np.eye(3), None, rv0.copy(), Tab[:3, 3].reshape(3, 1).copy(), True, iterationsCount=500, reprojectionError=3.0 / Ka[0, 0])
        if not ok or inl is None or len(inl) < 30: continue
        inl = inl.ravel(); rv, tv = cv2.solvePnPRefineLM(X[inl], na[qi[inl]], np.eye(3), None, rv, tv)
        R, _ = cv2.Rodrigues(rv); dev = np.degrees(np.linalg.norm(cv2.Rodrigues(Tab[:3, :3].T @ R)[0]))
        pr = X[inl] @ R.T + tv.ravel(); e = np.median(np.linalg.norm(pr[:, :2] / pr[:, 2:3] - na[qi[inl]], axis=1)) * Ka[0, 0]
        res[s].append((t, dev, len(inl), e))
for s, r in res.items():
    r = np.array(r); print(f'ep {ep} shift b = a{s:+d}: n {len(r)}  rot deviation from calibrated ext: med {np.median(r[:,1]):.3f} rms {np.sqrt(np.mean(r[:,1]**2)):.3f} deg; inliers med {np.median(r[:,2]):.0f}; reproj med {np.median(r[:,3]):.2f} px')
