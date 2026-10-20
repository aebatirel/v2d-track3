"""Render each cup's base (outside) from the scan: colour, colour detail x8, and normal shading of geometry."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample, splat, rot
A = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
rows = []
for n in ['blue_cup', 'beige_cup']:
    g, tex = load(n); P, C, N = sample(g, tex, 1500000, seed=3)
    p, a = np.array(A[n]['p']), np.array(A[n]['gt_up']); a /= np.linalg.norm(a)
    h = (P - p) @ a                     # up = toward rim; base at h.min()
    sel = (h < h.min() + 0.012) & (N @ a < -0.5)   # outward-facing base points
    Q, Cq, Nq = P[sel], C[sel], N[sel]
    R = rot([1, 0, 0], np.pi) if a[2] < 0 else np.eye(3)   # put base toward the -z viewer
    R = R  # base normal (-a) -> view: verify sign by nearest ordering
    img = splat(Q, Cq, R, size=500, center=(p @ R.T), scale=500 / 0.11, psize=2)
    sh = np.clip(0.5 + 0.5 * (Nq @ np.array([0.5, 0.5, 0.0]) / 0.707) * 0.8, 0, 1)
    gim = splat(Q, np.repeat(sh[:, None], 3, 1), R, size=500, center=(p @ R.T), scale=500 / 0.11, psize=2)
    det = img - cv2.GaussianBlur(img, (0, 0), 8); det = np.clip(0.5 + 8 * det, 0, 1)
    rows.append(np.hstack([img, det, gim]))
    print(n, 'base pts', sel.sum())
out = (np.clip(np.vstack(rows), 0, 1) * 255).astype(np.uint8)[..., ::-1]
cv2.imwrite('/Users/aebatirel/Documents/Code/v2d-research/work/12/b/cup_bases_scan.png', out)
