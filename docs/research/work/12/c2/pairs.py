"""Rigid pair invariants of the scan marker constellations: 3D distance between every marker pair (independent of the
object pose), and how far each pair's distance is from the nearest *other* pair's distance (the identity margin a
stereo-triangulated pair has without any centre/axis prior). Also the pair of triplets for 3 markers."""
import numpy as np, sys, json, itertools
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
from selfsim import good_markers
out = {}
for n in ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']:
    M = good_markers(n); pr = list(itertools.combinations(range(len(M)), 2))
    d = np.array([np.linalg.norm(M[i] - M[j]) for i, j in pr]) * 1000
    rows = []
    for k, (i, j) in enumerate(pr):
        oth = np.delete(d, k); rows.append(((i, j), round(d[k], 1), round(np.abs(oth - d[k]).min(), 1)))
    out[n] = rows
    print(n, len(M), 'markers; pair: dist mm, margin to nearest other pair mm')
    for r in rows: print('   ', r)
json.dump({k: [[list(a), b, c] for a, b, c in v] for k, v in out.items()}, open('c2/pairs.json', 'w'), indent=1)
