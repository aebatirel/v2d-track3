"""Verifier for dig-11 claims C1/C3: independent room registration (own code; AKAZE or SIFT, own rotation RANSAC,
own region mask) of frame 0 to the 4 reference public frames, transferring the GT-silhouette heading fits of s25.
Inference-side input: video frames only; reference side: s25 fits (public GT). usage: python v1_reg.py <native|flipped> <akaze|sift> <top_frac>"""
import sys, json, numpy as np, cv2
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"; W0, H0 = 2028, 1520
VAR, DET, TOP = sys.argv[1], sys.argv[2], float(sys.argv[3])
cal = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))["cameras"]["ego_cam_a"]
fx, fy, cx, cy = cal["fx"], cal["fy"], cal["cx"], cal["cy"]; dist = np.array(cal["distortion_coefficients"], float)
if VAR == "flipped":
    cx, cy = W0 - 1 - cx, H0 - 1 - cy; dist[2:4] *= -1; dist[8:14] *= -1
K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])
FITS = json.load(open(f"{ROOT}/work/11/s25_refine_{VAR}.json"))
REFS = [12, 13, 21, 0]; ALLFIT = [12, 13, 21, 0, 22, 26, 31]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
det = cv2.ORB_create(20000, fastThreshold=10) if DET == "orb" else cv2.SIFT_create(8000)


def Rwc(psi, th, ph):  # same parameterisation as the fits (camera x right, y down, z optical axis)
    p, t, r_ = np.radians([psi, th, ph]); f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    c, s = np.cos(r_), np.sin(r_)  # Rodrigues about f
    rot = lambda v: v * c + np.cross(f, v) * s + f * np.dot(f, v) * (1 - c)
    return np.column_stack([rot(r), rot(d), f])


def feats(split, ep):
    cap = cv2.VideoCapture(f"{ROOT}/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4")
    ok, img = cap.read(); g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); m = np.zeros_like(g); m[: int(TOP * H0)] = 255
    k, d = det.detectAndCompute(g, m); uv = np.array([p.pt for p in k], np.float64)
    n = cv2.undistortPoints(uv.reshape(-1, 1, 2), K, dist).reshape(-1, 2); b = np.c_[n, np.ones(len(n))]
    return b / np.linalg.norm(b, axis=1, keepdims=True), d


def rot_fit(X, Y, w=None):
    H = (Y * (w[:, None] if w is not None else 1)).T @ X; U, _, Vt = np.linalg.svd(H)
    return U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt


def register(A, B, thr_deg=0.25):
    (xa, da), (xb, db) = A, B
    norm = cv2.NORM_HAMMING if DET == "orb" else cv2.NORM_L2
    mt = cv2.BFMatcher(norm, crossCheck=True).match(da, db)
    X = xa[[m.queryIdx for m in mt]]; Y = xb[[m.trainIdx for m in mt]]
    rng = np.random.default_rng(1); ct = np.cos(np.radians(thr_deg)); best = None
    for _ in range(3000):
        i = rng.choice(len(X), 3, replace=False); R = rot_fit(X[i], Y[i]); inl = (X @ R.T * Y).sum(1) > ct
        if best is None or inl.sum() > best.sum(): best = inl
    for _ in range(5):
        R = rot_fit(X[best], Y[best]); best = (X @ R.T * Y).sum(1) > ct
    return R, int(best.sum()), len(X)


def heading(R):
    f = R[:, 2]; return float(np.degrees(np.arctan2(f[1], f[0])) % 360)


if __name__ == "__main__":
    F = {("p", e): feats("public", e) for e in ALLFIT}
    F.update({("e", e): feats("evaluation", e) for e in EV})
    out = {}
    for q in F:
        for p in REFS:
            if q == ("p", p): continue
            R, ni, nm = register(F[("p", p)], F[q])  # b_q = R b_p
            Rq = Rwc(FITS[str(p)]["psi"], FITS[str(p)]["th"], FITS[str(p)]["ph"]) @ R.T
            out[f"{q[0]}{q[1]}|{p}"] = dict(psi=heading(Rq), inl=ni, nm=nm)
    json.dump(out, open(f"v1_reg_{VAR}_{DET}_{TOP}.json", "w"), indent=1)
    w = lambda a: (a + 180) % 360 - 180
    res = []
    for q in REFS:
        pr = [out[f"p{q}|{p}"]["psi"] for p in REFS if p != q]; r = w(np.median(pr) - FITS[str(q)]["psi"]); res.append(r)
        print(f"LOO ref {q:2d}: fit {FITS[str(q)]['psi']:.2f} pred {np.median(pr):.2f} resid {r:+.2f} preds {np.round(pr, 2)} inl {[out[f'p{q}|{p}']['inl'] for p in REFS if p != q]}")
    print(f"LOO rms {np.sqrt(np.mean(np.square(res))):.2f}")
    for q in [22, 26, 31]:
        pr = [out[f"p{q}|{p}"]["psi"] for p in REFS]
        print(f"non-ref {q}: fit {FITS[str(q)]['psi']:.2f} pred {np.median(pr):.2f} resid {w(np.median(pr) - FITS[str(q)]['psi']):+.2f} spread {np.std(pr):.2f}")
    for q in EV:
        pr = [out[f"e{q}|{p}"]["psi"] for p in REFS]; inl = [out[f"e{q}|{p}"]["inl"] for p in REFS]
        print(f"eval {q:2d}: W {np.median(pr):7.2f} spread {np.std(pr):.2f} min inl {min(inl)}")
