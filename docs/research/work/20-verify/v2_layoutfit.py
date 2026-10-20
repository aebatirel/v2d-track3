"""Verifier round 2 (B1): re-derive the bend and marker-asymmetry fits from the stored per-view values
(work/20/out/b2/rerun_summary.json 'views', produced by b2_cmpgeom.py). Model per clip-view:
  bowl_raw = bend + dH_eff * cot(alpha)               (as in the note)
  asym_raw(h_p=7.2) = asym_true - 2 * (h_axis - 7.2) * cot(alpha)   (axis line back-projected at the wrong height)
Clip means as the units (as in the note); LSQ with standard errors; leave-one-clip-out."""
import json, numpy as np
d = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/rerun_summary.json'))
V = d['views']; keys = sorted({(v['ep'], v['end']) for v in V}, key=str)
cm = []
for kk in keys:
    S = [v for v in V if (v['ep'], v['end']) == kk]
    cm.append((kk, np.mean([v['cot'] for v in S]), np.mean([v['bowl_raw_h72'] for v in S]), np.mean([v['asym_h72'] for v in S]), len(S)))
def fit(x, y):
    A = np.c_[np.ones(len(x)), x]; c, res, *_ = np.linalg.lstsq(A, y, rcond=None); r = y - A @ c
    s2 = r @ r / max(len(x) - 2, 1); cov = s2 * np.linalg.inv(A.T @ A); return c, np.sqrt(np.diag(cov)), np.sqrt(s2)
for lab, idx in (('bowl', 2), ('asym', 3)):
    for excl in ((), ((35, False),)):
        L = [c for c in cm if c[0] not in excl]; x = np.array([c[1] for c in L]); y = np.array([c[idx] for c in L])
        c, se, sd = fit(x, y)
        loo = [fit(np.delete(x, i), np.delete(y, i))[0][0] for i in range(len(x))]
        print(f'{lab} excl {excl}: n {len(x)} intercept {c[0]:+.2f} +- {se[0]:.2f}, slope {c[1]:+.2f} +- {se[1]:.2f} (resid sd {sd:.2f}); LOO intercept range {min(loo):+.2f}..{max(loo):+.2f}; mean y {y.mean():+.2f}')
    # implied axis-height error for asym: slope = -2*(h_axis-7.2)
for c in cm: print(c)
# frame-level fit as a check (views as units)
x = np.array([v['cot'] for v in V]); y = np.array([v['asym_h72'] for v in V]); c, se, sd = fit(x, y)
print(f'asym frame-level: intercept {c[0]:+.2f} +- {se[0]:.2f} slope {c[1]:+.2f} +- {se[1]:.2f} -> implied h_axis {7.2 - c[1]/2:.1f} mm (dy-field frame)')
