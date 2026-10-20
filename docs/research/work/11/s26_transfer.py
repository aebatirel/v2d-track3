"""Stage C: transfer the mocap-world camera heading from fitted public frames to any frame 0 through background
(room) registration. Pairwise pure-rotation RANSAC on SIFT features in the top 55 % of the frame (as s7), K variant
given; R_wc,q|p = R_wc,p @ R_pq^T where bearings b_q = R_pq b_p. Inference-side inputs: eval video only; the
public side uses the s25 (or s24) GT-silhouette camera fits. usage: python s26_transfer.py <variant> <fits.json>"""
import sys, json, os, numpy as np, cv2
VAR, FITS = sys.argv[1], sys.argv[2]; sys.argv = [sys.argv[0], VAR]
import s24_campose as S
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"; H0 = 1520
fits = json.load(open(FITS))
PUB = [0, 11, 12, 13, 18, 21, 22, 23, 26, 31, 39, 41]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
sift = cv2.SIFT_create(6000); bf = cv2.BFMatcher()
def load(split, ep):
    p = f"{ROOT}/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4"
    c = cv2.VideoCapture(p); ok, f = c.read(); g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    m = np.zeros_like(g); m[: int(0.55 * H0)] = 255; k, d = sift.detectAndCompute(g, m)
    pts = np.array([x.pt for x in k], np.float32)
    n = cv2.undistortPoints(pts.reshape(-1, 1, 2), S.Kof(1.0), S.dist).reshape(-1, 2)
    b = np.c_[n, np.ones(len(n))]; return b / np.linalg.norm(b, axis=1, keepdims=True), d
def kabsch(X, Y):
    U, _, Vt = np.linalg.svd(Y.T @ X); D = np.diag([1, 1, np.linalg.det(U @ Vt)]); return U @ D @ Vt
def reg(A, B):
    (ba, da), (bb, db) = A, B
    mm = bf.knnMatch(da, db, k=2); good = [a for a, b in mm if a.distance < 0.75 * b.distance]
    X = ba[[g.queryIdx for g in good]]; Y = bb[[g.trainIdx for g in good]]
    rng = np.random.default_rng(0); thr = np.cos(np.radians(0.35)); best = (0, None)
    for _ in range(2000):
        i = rng.choice(len(X), 2, replace=False); R = kabsch(X[i], Y[i]); c = np.sum((X @ R.T) * Y, 1) > thr
        if c.sum() > best[0]: best = (c.sum(), c)
    c = best[1]
    for _ in range(3): R = kabsch(X[c], Y[c]); c = np.sum((X @ R.T) * Y, 1) > thr
    return R, int(c.sum()), len(good)
def hpr(Rwc):
    f = Rwc[:, 2]; r = Rwc[:, 0]
    psi = np.degrees(np.arctan2(f[1], f[0])); th = np.degrees(np.arcsin(-f[2]))
    r0 = np.cross(f, [0, 0, 1.0]); r0 /= np.linalg.norm(r0)
    ph = np.degrees(np.arctan2(np.dot(np.cross(r0, r), f), np.dot(r0, r))); return psi, th, ph
if __name__ == "__main__":
    F = {("p", e): load("public", e) for e in PUB}; F.update({("e", e): load("evaluation", e) for e in EV})
    fitted = [e for e in PUB if str(e) in fits]
    Rw = {e: S.Rwc(fits[str(e)]["psi"], fits[str(e)]["th"], fits[str(e)]["ph"]) for e in fitted}
    out = dict(pairs={}, pred={})
    for q in list(F):
        for p in fitted:
            if q == ("p", p): continue
            R, ninl, nm = reg(F[("p", p)], F[q])
            psi, th, ph = hpr(Rw[p] @ R.T)
            out["pairs"][f"{q[0]}{q[1]}|{p}"] = dict(psi=psi, th=th, ph=ph, inl=ninl, nm=nm)
        print(q, "done", flush=True)
    json.dump(out, open(f"s26_transfer_{VAR}_{os.path.basename(FITS).split('.')[0]}.json", "w"), indent=1)
