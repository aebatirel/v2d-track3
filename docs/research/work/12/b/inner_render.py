"""Inner bottom of each cup (seen looking down into an upright cup): colour + CLAHE."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample, splat, rot
A = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
cl = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
rows = []
for n in ['blue_cup', 'beige_cup']:
    g, tex = load(n); P, C, N = sample(g, tex, 3000000, seed=5)
    p, a = np.array(A[n]['p']), np.array(A[n]['gt_up']); a /= np.linalg.norm(a)
    h = (P - p) @ a; r = np.linalg.norm((P - p) - h[:, None] * a, axis=1)
    sel = (h < h.min() + 0.025) & (N @ a > 0.7) & (r < 0.034)      # floor of the interior, facing up
    print(n, 'inner floor pts', sel.sum(), 'floor h above base (mm)', round(1000 * (np.median(h[sel]) - h.min()), 1))
    R = rot([1, 0, 0], np.pi) if a[2] > 0 else np.eye(3)            # view from the rim side
    kw = dict(size=600, center=(p @ R.T), scale=600 / 0.10, psize=2)
    img = (np.clip(splat(P[sel], C[sel], R, **kw), 0, 1) * 255).astype(np.uint8)
    L = cl.apply(cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), 3))
    rows.append(np.hstack([img[..., ::-1], cv2.cvtColor(L, cv2.COLOR_GRAY2BGR)]))
cv2.imwrite('/Users/aebatirel/Documents/Code/v2d-research/work/12/b/cup_inner_floor_scan.png', np.vstack(rows))
