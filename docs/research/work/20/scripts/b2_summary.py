# Stage B re-run summary -> out/b2/rerun_summary.json: per rest/end-rest view, the straight-midline ('midpts') image offsets
# (b2_front), the table-plane bowl/marker values at h = 7.2 mm (re-computed here exactly as b2_cmpgeom), view coefficients,
# plus the bend regression and the P(B) table. Inputs: out/b2/frontrest_e*.jsonl, out/b/meas_e*.json, out/b2/pb_*.jsonl.
import json, glob, subprocess, re, numpy as np
O2 = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2'
PY = '/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python'; SC = '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'
views = [(36, k, '') for k in (0, 1)] + [(35, k, '') for k in (0, 1)] + [(37, k, '') for k in (0, 1)] + [(16, k, '') for k in (0, 1)] + \
        [(5, k, '--span=30') for k in (0, 1, 2)] + [(3, k, '--end --span=30') for k in (306, 310)] + [(35, k, '--end --span=30') for k in (412, 416)] + \
        [(37, k, '--end --span=30') for k in (142, 146)]
rows = []
for ep, k, fl in views:
    out = subprocess.run([PY, f'{SC}/b2_cmpgeom.py', str(ep), str(k)] + fl.split(), capture_output=True, text=True).stdout
    g = re.search(r'image-lateral = ([\d.]+) w \+ ([\d.]+) h ; cot ([\d.]+)', out)
    m = re.search(r'h 7\.2: midpts-axis: bowl ([+-][\d.]+) markers ([+-][\d.]+) ([+-][\d.]+) ([+-][\d.]+) asym ([+-][\d.]+)', out)
    if not (g and m): print('skip', ep, k, fl); continue
    rows.append(dict(ep=ep, k=k, end='--end' in fl, a=float(g[1]), b=float(g[2]), cot=float(g[3]), bowl_raw_h72=float(m[1]),
                     lat_M1=float(m[2]), lat_M2=float(m[3]), lat_M3=float(m[4]), asym_h72=float(m[5])))
    print(rows[-1])
# clip-view means and regression raw = bend + dH * cot
from collections import defaultdict
grp = defaultdict(list)
for r in rows: grp[(r['ep'], r['end'])].append(r)
cm = [(np.mean([r['cot'] for r in L]), np.mean([r['bowl_raw_h72'] for r in L]), np.mean([r['asym_h72'] for r in L]), key) for key, L in grp.items()]
def fit(sel):
    x = np.array([c[0] for c in sel]); y = np.array([c[1] for c in sel]); A = np.c_[np.ones_like(x), x]; cf, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ cf; s = np.sqrt(r @ r / (len(x) - 2)); cov = s * s * np.linalg.inv(A.T @ A); return cf, np.sqrt(np.diag(cov)), s
cf_all, se_all, s_all = fit(cm); cf_ex, se_ex, s_ex = fit([c for c in cm if c[3] != (35, False)])
asym72 = np.array([c[2] for c in cm]); asym82 = np.array([c[2] + 2 * c[0] * 1.0 for c in cm])
summ = dict(views=rows, clip_means=[dict(ep=c[3][0], end=c[3][1], cot=c[0], bowl_raw=c[1], asym_h72=c[2]) for c in cm],
            bend_fit_all=dict(bend=cf_all[0], bend_se=se_all[0], dH=cf_all[1], dH_se=se_all[1], resid_sd=s_all),
            bend_fit_ex_e35=dict(bend=cf_ex[0], bend_se=se_ex[0], dH=cf_ex[1], dH_se=se_ex[1], resid_sd=s_ex),
            asym_h72=dict(mean=float(asym72.mean()), sd=float(asym72.std(ddof=1))), asym_h82=dict(mean=float(asym82.mean()), sd=float(asym82.std(ddof=1))))
pb = {}
for f in glob.glob(f'{O2}/pb_*.jsonl'):
    lay = f.split('pb_')[1].rsplit('_', 1)[0]; X = [list(json.loads(l)['res'].values())[0] for l in open(f)]
    pb[lay] = dict(n=len(X), toM2_mean=float(np.mean([x['toM2'] for x in X])), PB_noisy_mid=float(np.mean([x['PB_noisy_mid'] for x in X])),
                   **{kk: float(np.mean([x[kk].startswith('B') for x in X])) for kk in ['n07_skew_y', 'n07_skew_x', 'n07_hybrid.02', 'n07_larger_abs', 'noisy_q10_y', 'noisy_-shalf_x', 'noisy_far3d_x']},
                   F2=float(np.mean([x['F2_shareB'] for x in X])), F2b=float(np.mean([x['F2b_shareB'] for x in X])), F3=float(np.mean([x['F3_shareB'] for x in X])))
summ['pb'] = pb
json.dump(summ, open(f'{O2}/rerun_summary.json', 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in summ.items() if k not in ('views',)}, indent=1, default=float))
