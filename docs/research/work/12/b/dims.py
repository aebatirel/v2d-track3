"""Object dimensions about the GT spin axis (height, body radius percentiles, max radius = handle/spout reach)."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from meshlib import load, sample
A = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))
for n in ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']:
    g, tex = load(n); P, C, N = sample(g, tex, 200000)
    p, a = np.array(A[n]['p']), np.array(A[n]['gt_up']); a /= np.linalg.norm(a)
    h = (P - p) @ a; r = np.linalg.norm((P - p) - h[:, None] * a, axis=1)
    print(f"{n:14s} extents(mm) {np.round(g.extents*1000,1)}  height {1000*(h.max()-h.min()):.0f}  r p50 {1000*np.median(r):.0f} p90 {1000*np.percentile(r,90):.0f} p99 {1000*np.percentile(r,99):.0f} max {1000*r.max():.0f}")
