# Stage A3b: localise a pairing slip to one interval + inspect per-stream |w| and MAD near it. No GT.
# Usage: a_slip.py <key> <s1_frames> <s2_frames> [ctrow]
import sys, numpy as np
from scipy.interpolate import CubicSpline
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts')
from a_sync import fit_shift
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
key = sys.argv[1]; s1, s2 = float(sys.argv[2]), float(sys.argv[3])
z = np.load(f'{OUT}/motion/{key}.npz'); wa, wb, wc = z['a_rv'], z['b_rv'], z['c_rv']
n = len(wa); _, _, R, _ = fit_shift(wa, wb)
k = np.arange(n, dtype=float); g = np.isfinite(wb).all(1)
spl = CubicSpline(k[g], wb[g], axis=0, extrapolate=False)
def r(s):
    q = k + s; e = np.full(n, np.nan); m = (q >= 0) & (q <= n - 1)
    e[m] = np.sum((wa[m] - spl(q[m]) @ R.T) ** 2, 1); return e
e1, e2 = r(s1), r(s2); m = np.isfinite(e1) & np.isfinite(e2)
d = np.where(m, e1 - e2, 0.0)   # >0 where s2 fits better
# changepoint: segment [0,j) uses s1, [j,n) uses s2 -> minimise sum e
cum = np.cumsum(d[::-1])[::-1]  # sum_{i>=j} d_i
j = int(np.argmax(cum)); print(key, 'slip: s1 before interval', j, 'then s2; gain', round(float(cum[j] / np.nansum(np.where(m, e1, 0))), 3))
deg = lambda w: np.degrees(np.linalg.norm(w, axis=1))
for i in range(max(0, j - 5), min(n, j + 5)):
    print(f'  int {i:3d}->{i+1:3d} |w| a {deg(wa)[i]:.3f} b {deg(wb)[i]:.3f} c {deg(wc)[i]:.3f} deg  MAD a {z["a_mad"][i]:.2f} b {z["b_mad"][i]:.2f} c {z["c_mad"][i]:.2f}  d {d[i]*1e6:+.2f}')
