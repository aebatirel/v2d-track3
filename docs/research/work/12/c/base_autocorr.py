"""Rotational self-similarity of the cup-base inscription in the scan texture (spin cue when the base faces the camera).
NCC of the band-passed base image vs its own rotation, inside r < r_in (excludes rim edge), markers masked out."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample, splat, rot
A = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
out = {}
for n in ['blue_cup', 'beige_cup']:
    g, tex = load(n); P, C, N = sample(g, tex, 2500000, seed=5)
    p, a = np.array(A[n]['p']), np.array(A[n]['gt_up']); a /= np.linalg.norm(a)
    h = (P - p) @ a; sel = (h < h.min() + 0.010) & (N @ a < -0.7)
    R = rot([1, 0, 0], np.pi) if a[2] < 0 else np.eye(3)
    S = 400; img = splat(P[sel], C[sel], R, size=S, center=(p @ R.T), scale=S / 0.10, psize=2)
    L = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    yy, xx = np.mgrid[0:S, 0:S]; r = np.hypot(xx - S / 2, yy - S / 2) / (S / 0.10) * 1000   # mm
    for sig_lo, sig_hi, tag in [(1.0, 6.0, 'bp_0.25-1.5mm'), (2.0, 12.0, 'bp_0.5-3mm')]:
        B = cv2.GaussianBlur(L, (0, 0), sig_lo) - cv2.GaussianBlur(L, (0, 0), sig_hi)
        res = {}
        for rin in (25, 30):
            m = (r < rin) & (L < 250)          # inside disc, not background
            cur = []
            for ang in range(0, 360, 2):
                M = cv2.getRotationMatrix2D((S / 2, S / 2), ang, 1.0)
                Br = cv2.warpAffine(B, M, (S, S)); mr = cv2.warpAffine(m.astype(np.uint8), M, (S, S)) > 0
                k = m & mr; x, y = B[k] - B[k].mean(), Br[k] - Br[k].mean()
                cur.append(float(x @ y / np.sqrt((x @ x) * (y @ y))))
            cur = np.array(cur); ang = np.arange(0, 360, 2)
            outside = np.abs((ang + 180) % 360 - 180) > 20
            hw = int(np.argmax(cur < 0.5)) * 2
            res[f'r<{rin}'] = dict(peak0=cur[0], half_width_deg=hw, max_outside_20=float(cur[outside].max()),
                                   at=int(ang[outside][cur[outside].argmax()]))
        out[f'{n}/{tag}'] = res
        print(n, tag, {k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in res.items()}, flush=True)
json.dump(out, open('/Users/aebatirel/Documents/Code/v2d-research/work/12/c/out/base_autocorr.json', 'w'), indent=1)
