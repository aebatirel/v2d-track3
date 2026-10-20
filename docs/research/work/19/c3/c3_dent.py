# Stage C3: does MuJoCo's 64-vertex cap open dents in the colliders? For each object: 200k surface samples of the
# exact solid (b/W2) + its vertices; for every sample outside all hulls of a set, its outside distance
# (min over hulls of the max plane distance; a lower bound of the Euclidean distance). Uncapped CoACD unions of V1
# contain W2 by construction, so any outside distance is a dent made by the cap (or, for split sets, by the cut caps).
# usage: c3_dent.py LABEL=dir ...
import sys, numpy as np, trimesh
from scipy.spatial import ConvexHull
W2 = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/W2/'
NAMES = ['white_pot_lid', 'white_pot', 'mini_sweeper', 'plastic_dish_rack', 'blue_cup', 'beige_cup']
def outside_dist(pts, hv):
    best = np.full(len(pts), np.inf)
    for v in hv:
        try: e = ConvexHull(v).equations
        except Exception: continue
        lo, hi = v.min(0) - 0.01, v.max(0) + 0.01
        k = np.where(np.all((pts >= lo) & (pts <= hi), 1))[0]   # only samples within 10 mm of the hull's box matter
        if len(k): best[k] = np.minimum(best[k], (pts[k] @ e[:, :3].T + e[:, 3]).max(1))
    return best
for arg in sys.argv[1:]:
    lab, d = arg.split('=')
    for n in NAMES:
        w = np.load(W2 + n + '.npz'); m = trimesh.Trimesh(w['v'], w['f'], process=False); np.random.seed(5)
        p = np.vstack([w['v'][::4], trimesh.sample.sample_surface(m, 200000)[0]])
        z = np.load(f'{d}/{n}.npz'); hv = [z[f'v{i}'] for i in range(int(z['n']))]
        od = outside_dist(p, hv) * 1e3; od[~np.isfinite(od)] = 10.0
        print(f'{lab:10s} {n:18s} samples {len(p)} | outside >0.5 mm {np.mean(od > 0.5) * 100:5.2f} % >1 mm {np.mean(od > 1) * 100:5.2f} % '
              f'>2 mm {np.mean(od > 2) * 100:5.2f} % | p99.9 {np.percentile(od, 99.9):4.2f} max {od.max():4.2f} mm', flush=True)
