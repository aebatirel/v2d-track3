"""Profile plot: observed points (r,h) by class, our lathe mesh section, and [D] the scan section (aligned)."""
import sys, numpy as np, cv2, trimesh
sys.path.insert(0, sys.argv[5])
import lathe_obs as L
Z = np.load(sys.argv[1]); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
rng = np.random.default_rng(0); s = rng.choice(len(P), min(120000, len(P)), replace=False); P, C = P[s], C[s]
cost, c, d, k = L.fit_axis(P[:60000], C[:60000])
h, r, th, (e1, e2, d) = L.cyl(P, c, d)
v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True); vr = (v @ e1) * np.cos(th) + (v @ e2) * np.sin(th)
lat = trimesh.load(sys.argv[2], force='mesh'); Lp = trimesh.sample.sample_surface(lat, 60000, seed=0)[0]
A = np.load(sys.argv[1].replace('.npz', '_align.npz')); scan = trimesh.load(sys.argv[3], force='mesh')
Sp = trimesh.sample.sample_surface(scan, 80000, seed=0)[0]; Sp = (Sp - A['t']) @ A['R']   # scan -> our frame
W, H = 900, 900; img = np.full((H, W, 3), 255, np.uint8)
hl, rl = (Lp - c) @ d, None
def rh(X):
    hh = (X - c) @ d; Q = X - c - hh[:, None] * d; return np.linalg.norm(Q, axis=1), hh
hmin, hmax = h.min() - 0.01, h.max() + 0.01; rmax = r.max() + 0.01
sc = min((W - 40) / rmax, (H - 40) / (hmax - hmin))
def put(rr, hh, col):
    x = (20 + rr * sc).astype(int); y = (H - 20 - (hh - hmin) * sc).astype(int)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H); img[y[ok], x[ok]] = col
put(r[vr > 0.3], h[vr > 0.3], (230, 180, 180)); put(r[vr < -0.3], h[vr < -0.3], (180, 180, 230))
put(*rh(Sp), (0, 150, 0)); put(*rh(Lp), (0, 0, 0))
cv2.putText(img, 'light: obs (blue outer, red inner); green: scan [D]; black: ours', (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
cv2.imwrite(sys.argv[4], img)
