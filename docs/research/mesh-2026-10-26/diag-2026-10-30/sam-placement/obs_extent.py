"""[D] Do our observed points extend beyond the scan along the scan's principal axes? (explains axial slides)"""
import json, sys
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa
dec = {}
for l in open(f'{OUT}/decomp_before.jsonl'):
    r = json.loads(l)
    if r['model'] == 'sam3d' and r['seed'] == 42:
        dec[r['obj']] = r
print('| object | axis | scan 1-99 % range mm | our points 1-99 % | library_v3 1-99 % | obs beyond scan (lo/hi) mm | obs->scan dist p50/p90 mm | frac obs > 10 mm from scan |')
print('|---|---|---|---|---|---|---|---|')
from scipy.spatial import cKDTree
for obj in OBJS:
    V = np.array(dec[obj]['scan_pca'])
    Y, _ = surf(load_scan(obj), 20000, seed=2)
    O = load_obs(obj, n=20000)['pts']
    L, _ = surf(load_mesh(f'{LIB}/{obj}.glb'), 20000, seed=3)
    c = Y.mean(0)
    d = cKDTree(Y).query(O)[0] * 1e3
    for k, name in enumerate(['long', 'mid', 'short']):
        p = lambda X: np.percentile((X - c) @ V[:, k], [1, 99]) * 1e3
        ys, os_, ls = p(Y), p(O), p(L)
        print(f'| {obj} | {name} | {ys[0]:.0f}..{ys[1]:.0f} | {os_[0]:.0f}..{os_[1]:.0f} | {ls[0]:.0f}..{ls[1]:.0f} | '
              f'{ys[0] - os_[0]:+.0f} / {os_[1] - ys[1]:+.0f} | ' + (f'{np.median(d):.1f} / {np.percentile(d, 90):.1f} | {(d > 10).mean():.3f} |' if k == 0 else ' | |'))
