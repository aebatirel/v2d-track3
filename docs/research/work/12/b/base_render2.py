"""Higher-res base renders with local contrast (CLAHE) on colour and on geometry shading (two light directions)."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample, splat, rot
A = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
cl = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
def u8(x): return (np.clip(x, 0, 1) * 255).astype(np.uint8)
rows = []
for n in ['blue_cup', 'beige_cup']:
    g, tex = load(n); P, C, N = sample(g, tex, 3000000, seed=5)
    p, a = np.array(A[n]['p']), np.array(A[n]['gt_up']); a /= np.linalg.norm(a)
    h = (P - p) @ a; sel = (h < h.min() + 0.010) & (N @ a < -0.7)
    Q, Cq, Nq = P[sel], C[sel], N[sel]
    R = rot([1, 0, 0], np.pi) if a[2] < 0 else np.eye(3)
    kw = dict(size=600, center=(p @ R.T), scale=600 / 0.10, psize=2)
    img = splat(Q, Cq, R, **kw)
    L = cv2.cvtColor(u8(img), cv2.COLOR_RGB2GRAY); L = cl.apply(cv2.medianBlur(L, 3))
    t = [np.clip(0.5 + 2.5 * (Nq @ (d / np.linalg.norm(d)) - (Nq @ (d / np.linalg.norm(d))).mean()), 0, 1) for d in (np.array([1., 0, 0.3]), np.array([0, 1., 0.3]))]
    G = [cl.apply(cv2.medianBlur(cv2.cvtColor(u8(splat(Q, np.repeat(s[:, None], 3, 1), R, **kw)), cv2.COLOR_RGB2GRAY), 3)) for s in t]
    rows.append(np.hstack([L] + G))
cv2.imwrite('/Users/aebatirel/Documents/Code/v2d-research/work/12/b/cup_bases_scan2.png', np.vstack(rows)); print('ok')
