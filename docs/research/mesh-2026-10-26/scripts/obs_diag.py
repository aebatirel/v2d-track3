"""[D] diagnostic: observed points vs the public scan (after a rigid ICP from identity; our track frame ~ scan frame)."""
import sys, numpy as np, trimesh
from scipy.spatial import cKDTree
pts = np.load(sys.argv[1])['pts'].astype(np.float64); scan = trimesh.load(sys.argv[2], force='mesh')
rng = np.random.default_rng(0); P = pts[rng.choice(len(pts), min(200000, len(pts)), replace=False)]
S = trimesh.sample.sample_surface(scan, 300000, seed=0)[0]; tree = cKDTree(S)
R, t = np.eye(3), np.zeros(3)
for it in range(30):
    Q = P @ R.T + t; d, i = tree.query(Q)
    keep = d < np.percentile(d, 80)
    A, B = Q[keep], S[i[keep]]; ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb)); dR = Vt.T @ U.T
    if np.linalg.det(dR) < 0: Vt[-1] *= -1; dR = Vt.T @ U.T
    R, t = dR @ R, dR @ t + cb - dR @ ca
d = tree.query(P @ R.T + t)[0] * 1000
ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
print(f'{sys.argv[1]}: n={len(pts)} align rot {ang:.2f} deg trans {np.linalg.norm(t)*1000:.1f} mm; dist mm p50 {np.percentile(d,50):.2f} p75 {np.percentile(d,75):.2f} p90 {np.percentile(d,90):.2f} p95 {np.percentile(d,95):.2f} frac>5mm {np.mean(d>5):.3f}')
tp = cKDTree(P @ R.T + t); dc = tp.query(S[::10])[0] * 1000
print(f'  scan coverage: frac of scan surface within 3 mm of obs {np.mean(dc<3):.3f}, within 6 mm {np.mean(dc<6):.3f}')
np.savez(sys.argv[1].replace('.npz', '_align.npz'), R=R, t=t)
