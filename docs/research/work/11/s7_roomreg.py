"""Room memory: relative camera rotation between frame 0 of different episodes from static background
features (top 55% of the decoded, upright colour frame). Rotation about an approximate gravity axis =
change of camera heading. Research only; eval videos are inputs (no labels)."""
import cv2, json, numpy as np, subprocess, os, sys
from scipy.spatial.transform import Rotation as Rot
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
cal = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))["cameras"]["ego_cam_a"]
W, H = 2028, 1520
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "native"
fx, fy, cx, cy = cal["fx"], cal["fy"], cal["cx"], cal["cy"]
dist = np.array(cal["distortion_coefficients"], float)
if VARIANT == "flipped":
    cx, cy = W - 1 - cx, H - 1 - cy
    dist = dist.copy(); dist[2:4] *= -1; dist[8:14] *= -1
K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])

def frame(split, ep, n=0):
    p = f"{ROOT}/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4"
    if not os.path.exists(p): return None
    c = cv2.VideoCapture(p); c.set(cv2.CAP_PROP_POS_FRAMES, n); ok, f = c.read(); return cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if ok else None

sift = cv2.SIFT_create(6000)
def feats(img):
    m = np.zeros_like(img); m[: int(0.55 * H)] = 255
    k, d = sift.detectAndCompute(img, m); return np.array([x.pt for x in k], np.float32), d

def norm(pts):
    return cv2.undistortPoints(pts.reshape(-1, 1, 2), K, dist).reshape(-1, 2)

g_ref = np.array([0, np.cos(np.radians(15)), np.sin(np.radians(15))])  # approx gravity (down) in ref camera
REF = ("public", 12)
ref = frame(*REF); pr, dr = feats(ref); nr = norm(pr)
bf = cv2.BFMatcher()
out = {}
eps = [("public", e) for e in [0, 11, 13, 18, 21, 22, 26, 31, 41]] + [("evaluation", e) for e in [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]]
for split, ep in eps:
    img = frame(split, ep)
    if img is None: continue
    p, d = feats(img); n = norm(p)
    mm = bf.knnMatch(dr, d, k=2); good = [a for a, b in mm if a.distance < 0.75 * b.distance]
    a = nr[[g.queryIdx for g in good]]; b = n[[g.trainIdx for g in good]]
    A3 = np.c_[a, np.ones(len(a))]; A3 /= np.linalg.norm(A3, axis=1, keepdims=True)
    B3 = np.c_[b, np.ones(len(b))]; B3 /= np.linalg.norm(B3, axis=1, keepdims=True)
    rng = np.random.default_rng(0); best = (0, None); thr = np.cos(np.radians(0.35))
    def kabsch(X, Y):  # R with Y ~ R X
        U, S, Vt = np.linalg.svd(Y.T @ X); D = np.diag([1, 1, np.linalg.det(U @ Vt)]); return U @ D @ Vt
    for it in range(3000):
        idx = rng.choice(len(A3), 2, replace=False); Rc = kabsch(A3[idx], B3[idx])
        c = np.sum((A3 @ Rc.T) * B3, 1) > thr
        if c.sum() > best[0]: best = (c.sum(), c)
    inl2 = best[1]
    for _ in range(3):
        R = kabsch(A3[inl2], B3[inl2]); inl2 = np.sum((A3 @ R.T) * B3, 1) > thr
    t = np.zeros(3)
    rv = Rot.from_matrix(R.T).as_rotvec()  # x_cur = R x_ref
    heading = np.degrees(rv @ g_ref)
    tot = np.degrees(np.linalg.norm(rv))
    out[f"{split[:4]}{ep}"] = dict(n_match=len(good), inliers=int(inl2.sum() if inl2 is not None else 0), heading_deg=float(heading), total_deg=float(tot), t=t.ravel().tolist())
    print(f"{split[:4]}{ep:3d} matches {len(good):4d} inl {int((inl2>0).sum()):4d} heading {heading:7.2f} total {tot:6.2f} t {np.round(t.ravel(),2)}")
json.dump(out, open(f"s7_roomreg_{VARIANT}.json", "w"), indent=1)
