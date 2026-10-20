"""Per-frame cam-a pose relative to the SAME-index b frame: SIFT(a, half-res) matched to b_t stereo points (metric, in b_t)
-> PnP. Compare with the calibrated extrinsic; regress the deviation on b's angular velocity -> a-vs-b time offset.
Output out/apnp_<ep>.npz: T_b_a[t] measured (4x4; X_b = T X_a), ninl, med px."""
import sys, json, numpy as np, cv2
import lib17 as L
sys_argv = sys.argv; sys.argv = [sys.argv[0], sys.argv[1]]
import vo17 as V
ep = int(sys_argv[1]); step = int(sys_argv[2]) if len(sys_argv) > 2 else 1
Ka, da, _ = L.cam('a'); Tba = L.ext('a')
VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO)
va, vb, vc = L.Video(ep, 'a'), L.Video(ep, 'b'), L.Video(ep, 'c')
sift = cv2.SIFT_create(nfeatures=6000, contrastThreshold=0.02)
out_T = np.full((T, 4, 4), np.nan); out_n = np.zeros(T, int); out_e = np.full(T, np.nan)
g = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
for t in range(0, T, step):
    s = V.stereo(g(vb.get(t)), g(vc.get(t)))
    A = cv2.resize(g(va.get(t)), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    ka, Da = sift.detectAndCompute(A, None)
    if Da is None: continue
    pa = (np.array([k.pt for k in ka]) + 0.5) * 2 - 0.5
    na = cv2.undistortPoints(pa.reshape(-1, 1, 2), Ka, da).reshape(-1, 2)
    m = V.bf.knnMatch(Da, s['Db'][s['sidx']], k=2)
    qm = [(x[0].queryIdx, x[0].trainIdx) for x in m if len(x) == 2 and x[0].distance < 0.8 * x[1].distance]
    if len(qm) < 15: continue
    qi, mi = map(np.array, zip(*qm)); X = s['X'][mi]  # in b_t frame
    # init from calibrated extrinsic: X_a = R^T (X_b - t)
    Tab = np.linalg.inv(Tba); rv0, _ = cv2.Rodrigues(Tab[:3, :3])
    ok, rv, tv, inl = cv2.solvePnPRansac(X, na[qi], np.eye(3), None, rv0.copy(), Tab[:3, 3].reshape(3, 1).copy(), True,
                                          iterationsCount=500, reprojectionError=3.0 / Ka[0, 0], confidence=0.999, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok or inl is None or len(inl) < 15: continue
    inl = inl.ravel(); rv, tv = cv2.solvePnPRefineLM(X[inl], na[qi[inl]], np.eye(3), None, rv, tv)
    R, _ = cv2.Rodrigues(rv); pr = X[inl] @ R.T + tv.ravel()
    e = np.linalg.norm(pr[:, :2] / pr[:, 2:3] - na[qi[inl]], axis=1) * Ka[0, 0]
    Tab_m = np.eye(4); Tab_m[:3, :3] = R; Tab_m[:3, 3] = tv.ravel()
    out_T[t] = np.linalg.inv(Tab_m); out_n[t] = len(inl); out_e[t] = np.median(e)
    if t % 30 == 0: print(t, 'inl', len(inl), 'med px %.2f' % np.median(e), flush=True)
np.savez(f'out/apnp_{ep}.npz', T=out_T, n=out_n, e=out_e)
# analysis: deviation rotation (measured T_b_a vs calibrated) vs angular velocity of b (from VO)
ok = np.flatnonzero(np.isfinite(out_T[:, 0, 0]) & (out_n >= 30))
dev = np.array([cv2.Rodrigues(Tba[:3, :3].T @ out_T[t][:3, :3])[0].ravel() for t in ok])  # in a frame
dtr = np.array([(out_T[t][:3, 3] - Tba[:3, 3]) for t in ok]) * 1000
# angular velocity of b in b frame (rad/frame), mapped to a frame
w = []
for t in ok:
    a, b = max(t - 1, 0), min(t + 1, T - 1)
    Rr = VO[a][:3, :3].T @ VO[b][:3, :3]; w.append(Tba[:3, :3].T @ cv2.Rodrigues(Rr)[0].ravel() / (b - a))
w = np.array(w)
k = np.sum(w * dev) / np.sum(w * w)
print(f'ep {ep}: n {len(ok)} frames; inliers med {np.median(out_n[ok]):.0f}; reproj med {np.nanmedian(out_e[ok]):.2f} px')
print(f'  rotation deviation from calibrated extrinsic: mean (deg) {np.round(np.degrees(dev.mean(0)),3)}, sd {np.round(np.degrees(dev.std(0)),3)}')
print(f'  translation deviation mm: mean {np.round(dtr.mean(0),1)} sd {np.round(dtr.std(0),1)}')
print(f'  dev = k * omega: k = {k:+.3f} frames ({k*50:+.1f} ms); rms dev before {np.degrees(np.sqrt(np.mean((dev-dev.mean(0))**2))):.3f} after {np.degrees(np.sqrt(np.mean((dev-dev.mean(0)-k*(w-w.mean(0)))**2))):.3f} deg; corr {np.corrcoef(w.ravel(), (dev-dev.mean(0)).ravel())[0,1]:+.2f}')
