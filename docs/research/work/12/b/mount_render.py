"""Scan close-ups of each cup marker seen from outside (radial view), to see whether mount shapes differ per marker."""
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample, splat
from axis import frame_from_axis
AX = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
MK = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/markers2.json'))
rows = []
for n in ['beige_cup', 'blue_cup']:
    g, tex = load(n); P, C, N = sample(g, tex, 2500000, seed=11)
    p, a = np.array(AX[n]['p']), np.array(AX[n]['a']); e1, e2, a = frame_from_axis(a)
    tiles = []
    for th, h in zip(MK[n]['theta'], MK[n]['h']):
        t = np.radians(th); u = np.cos(t) * e1 + np.sin(t) * e2; tg = np.cross(a, u)
        c = p + a * h + u * 0.045
        sel = (np.linalg.norm(P - c, axis=1) < 0.035) & ((P - p) @ u > 0.02) & (N @ u > -0.2)
        R = np.stack([tg, a, -u])
        img = splat(P[sel], C[sel], R, size=240, center=c @ R.T, scale=240 / 0.06, psize=2)
        im = (np.clip(img, 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
        cv2.putText(im, f'{th:.0f}deg h{h*1000:.0f}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        tiles.append(im)
    while len(tiles) < 4: tiles.append(np.full_like(tiles[0], 255))
    rows.append(np.hstack(tiles))
cv2.imwrite('/Users/aebatirel/Documents/Code/v2d-research/work/12/b/cup_mounts_scan.png', np.vstack(rows)); print('ok')
