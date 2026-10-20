"""Stage C retry: which principal-point convention is right for ego_cam_a? Epipolar test cam_a <-> cam_b (same ego
device, calibrated extrinsic). For each combination of K variants (as given 'n' / 180-deg flipped 'f' cx,cy + sign of
odd distortion terms) and extrinsic R (as given / conjugated by Rz180), compute the Sampson epipolar error of SIFT
matches (inliers of a model-free fundamental RANSAC) and the free relative rotation vs the calibrated one.
Research only (public videos, calibration). usage: python s33_kcheck.py ep[,ep..] frames(comma) [b|c]"""
import sys, json, numpy as np, cv2
from scipy.spatial.transform import Rotation as Rot
ROOT = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public"
C = json.load(open(f"{ROOT}/meta/camera_calibration.json"))["cameras"]
EPS = [int(x) for x in sys.argv[1].split(",")]; FR = [int(x) for x in sys.argv[2].split(",")]
OTHER = sys.argv[3] if len(sys.argv) > 3 else "b"
def cam(name, var):
    c = C[name]; W, H = c["resolution"]; K = np.array(c["intrinsic_matrix"], float); d = np.array(c["distortion_coefficients"], float)
    if var == "f":
        K = K.copy(); K[0, 2] = W - 1 - K[0, 2]; K[1, 2] = H - 1 - K[1, 2]; d = d.copy(); d[2:4] *= -1; d[8:14] *= -1
    return K, d
def ext(name, conj):
    M = np.array(C[name]["extrinsics_to_stereo_left"], float); R, t = M[:3, :3], M[:3, 3]
    if conj: F = np.diag([-1, -1, 1.0]); R, t = F @ R @ F, F @ t
    return R, t
def frames(ep, cn, idx):
    cap = cv2.VideoCapture(f"{ROOT}/videos/chunk-000/observation.images.ego_cam_{cn}/episode_{ep:06d}.mp4"); out = {}; k = 0
    while k <= max(idx):
        ok, f = cap.read()
        if not ok: break
        if k in idx: out[k] = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        k += 1
    return out
sift = cv2.SIFT_create(4000); bf = cv2.BFMatcher()
def match(ga, gb):
    s = 0.5; ha = cv2.resize(ga, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    ka, da = sift.detectAndCompute(ha, None); kb, db = sift.detectAndCompute(gb, None)
    if da is None or db is None: return None, None
    m = [p[0] for p in bf.knnMatch(da, db, k=2) if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(m) < 30: return None, None
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pa = (pa + 0.5) / s - 0.5; pb = np.float32([kb[x.trainIdx].pt for x in m])
    F, inl = cv2.findFundamentalMat(pa, pb, cv2.FM_RANSAC, 1.5, 0.999)
    if F is None: return None, None
    k = inl.ravel() > 0; return pa[k], pb[k]
def norm(p, K, d): return cv2.undistortPoints(p.reshape(-1, 1, 2).astype(np.float64), K, d).reshape(-1, 2)
def sampson(xa, xb, E):
    Xa = np.c_[xa, np.ones(len(xa))]; Xb = np.c_[xb, np.ones(len(xb))]
    Ex = Xa @ E.T; Etx = Xb @ E; num = np.sum(Xb * Ex, 1)
    return num / np.sqrt(Ex[:, 0]**2 + Ex[:, 1]**2 + Etx[:, 0]**2 + Etx[:, 1]**2)
skew = lambda t: np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])
ON = f"ego_cam_{OTHER}"
res = {}
for ep in EPS:
    A = frames(ep, "a", FR); B = frames(ep, OTHER, FR)
    for k in FR:
        if k not in A or k not in B: continue
        pa, pb = match(A[k], B[k])
        if pa is None: print(ep, k, "no match"); continue
        row = {}
        for va in "nf":
            for vb in "nf":
                xa = norm(pa, *cam("ego_cam_a", va)); xb = norm(pb, *cam(ON, vb))
                for conj in (0, 1):
                    if OTHER == "b": R, t = ext("ego_cam_a", conj)       # X_b = R X_a + t
                    else:  # X_c = Rc^T (X_b - tc), X_b = Ra X_a + ta
                        Ra, ta = ext("ego_cam_a", conj); Rc, tc = ext("ego_cam_c", conj); R = Rc.T @ Ra; t = Rc.T @ (ta - tc)
                    e = sampson(xa, xb, skew(t) @ R) * 1150.0  # px at cam_a full-res focal
                    row[f"a{va}{OTHER}{vb}{'_conj' if conj else ''}"] = (float(np.median(np.abs(e))), float(np.median(e)))
                Ef, m = cv2.findEssentialMat(xa, xb, np.eye(3), cv2.RANSAC, 0.999, 0.6 / 1150)
                if Ef is not None and Ef.shape == (3, 3):
                    _, Rf, tf, _ = cv2.recoverPose(Ef, xa, xb, np.eye(3), mask=m)
                    R0, _ = ext("ego_cam_a", 0) if OTHER == "b" else (None, None)
                    if R0 is not None:
                        row[f"rotdiff_a{va}b{vb}_deg_xyz"] = [round(float(x), 2) for x in np.degrees(Rot.from_matrix(Rf @ R0.T).as_rotvec())]
        res[f"{ep}_{k}"] = dict(n=int(len(pa)), **row)
        best = sorted([(v[0], kk) for kk, v in row.items() if not kk.startswith("rot")])
        print(f"ep {ep:2d} f{k:3d} n {len(pa):4d} | " + "  ".join(f"{kk}:{v:.2f}" for v, kk in best[:8]))
        print("       rot(free - calib) deg xyz:", {kk[8:12]: v for kk, v in row.items() if kk.startswith("rot")})
json.dump(res, open(f"s33_kcheck_{OTHER}_{sys.argv[1].replace(',', '-')}.json", "w"), indent=1)
keys = sorted({kk for r in res.values() for kk in r if kk not in ("n",) and not kk.startswith("rot")})
print("MEDIAN over frames of median|Sampson| (px @ f=1150) and median signed:")
for kk in sorted(keys, key=lambda kk: np.median([r[kk][0] for r in res.values() if kk in r])):
    print(f"  {kk:12s} {np.median([r[kk][0] for r in res.values() if kk in r]):6.2f}  signed {np.median([r[kk][1] for r in res.values() if kk in r]):+6.2f}")
