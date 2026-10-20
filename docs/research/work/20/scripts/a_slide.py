# Stage A3: time-resolved a-b offset (sliding window) to locate frame-pairing slips. No GT.
# Usage: a_slide.py <key> [W=15] ; writes out/slide_<key>.npz and prints segments.
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts')
from a_sync import fit_shift
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
key = sys.argv[1]; W = int(sys.argv[2]) if len(sys.argv) > 2 else 15
X = sys.argv[3] if len(sys.argv) > 3 else 'a'
z = np.load(f'{OUT}/motion/{key}.npz'); wX, wY = z[f'{X}_rv'], z['b_rv']
n = len(wX); grid = np.arange(-3.5, 1.0001, 0.02)
# global R from the whole-episode fit (robust to slips: R is a constant rig rotation)
s0, c0, R, _ = fit_shift(wX, wY, grid=grid)
cs = []; ss = []; es = []
for k in range(n):
    idx = np.arange(max(0, k - W), min(n, k + W + 1))
    s, c, _, costs = fit_shift(wX, wY, grid=grid, fixR=R, idx=idx)
    en = np.degrees(np.sqrt(np.nanmean(np.sum(wX[idx] ** 2, 1)))) * 20
    ss.append(s * 50); cs.append(c); es.append(en)
ss = np.array(ss); cs = np.array(cs); es = np.array(es)
np.savez(f'{OUT}/slide_{key}{"" if X=="a" else X}.npz', s_ms=ss, cost=cs, energy=es)
q = np.round(ss / 50).astype(int)
good = (cs < 0.1) & (es > 1.0)
# print run-length segments of integer pairing among good windows
segs = []; cur = None
for k in range(n):
    if not good[k]: continue
    if cur is None or q[k] != cur[0]: cur = [q[k], k, k]; segs.append(cur)
    else: cur[2] = k
print(key, X, 'global', round(s0 * 50, 1), '| segments (frames, first, last):', [(int(a), b, c) for a, b, c in segs],
      '| frac good', round(good.mean(), 2), '| sub-frame resid median', round(float(np.median((ss - 50 * q)[good])), 2))
