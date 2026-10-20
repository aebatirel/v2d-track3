"""VO drift check: chained keyframe tracking vs direct PnP of frame t against the frame-0 stereo map."""
import sys, numpy as np, cv2
import lib17 as L
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
import vo17 as V
ep = int(sys.argv[1]); split = sys.argv[2] if len(sys.argv) > 2 else 'public'
P = np.load(f'out/vo_{split}_{ep}.npy')
vb, vc = L.Video(ep, 'b', split), L.Video(ep, 'c', split)
g = lambda v, t: cv2.cvtColor(v.get(t), cv2.COLOR_BGR2GRAY)
s0 = V.stereo(g(vb, 0), g(vc, 0)); X0, D0 = s0['X'], s0['Db'][s0['sidx']]
rows = []
for t in range(10, len(P), 10):
    s = V.stereo(g(vb, t), g(vc, t)); m = V.bf.knnMatch(s['Db'], D0, k=2)
    qi, mi = zip(*[(x[0].queryIdx, x[0].trainIdx) for x in m if len(x) == 2 and x[0].distance < 0.8 * x[1].distance])
    qi, mi = np.array(qi), np.array(mi)
    ok, rv, tv, inl = cv2.solvePnPRansac(X0[mi], s['nb'][qi], np.eye(3), None, iterationsCount=500, reprojectionError=1.5 / V.Kb[0, 0], confidence=0.999)
    if not ok or inl is None or len(inl) < 60: rows.append((t, 0, np.nan, np.nan)); continue
    inl = inl.ravel(); rv, tv = cv2.solvePnPRefineLM(X0[mi[inl]], s['nb'][qi[inl]], np.eye(3), None, rv, tv)
    Rcw, _ = cv2.Rodrigues(rv); Tcw = np.eye(4); Tcw[:3, :3] = Rcw; Tcw[:3, 3] = tv.ravel(); Tw = np.linalg.inv(Tcw)
    dR = np.degrees(np.linalg.norm(cv2.Rodrigues(P[t][:3, :3].T @ Tw[:3, :3])[0])); dt = np.linalg.norm(P[t][:3, 3] - Tw[:3, 3]) * 1000
    rows.append((t, len(inl), dR, dt))
    print(f't {t} direct inliers {len(inl)} chained-vs-direct rot {dR:.3f} deg trans {dt:.1f} mm', flush=True)
r = np.array(rows, float); ok = np.isfinite(r[:, 2])
print(f'ep {ep}: {ok.sum()}/{len(r)} checks; rot diff med {np.median(r[ok,2]):.3f} max {r[ok,2].max():.3f} deg; trans diff med {np.median(r[ok,3]):.1f} max {r[ok,3].max():.1f} mm')
