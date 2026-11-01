"""C2/P AUC guard verdict: C0's guard_eval.py rule (C0 PREREG section 5) for one object, water_pitcher, twins 21 and
22. Metrics are the 'perception' entry of each score_registered.py JSON (the episode's registered scores over all its
objects, as the board scores an episode).
  dX_e = X(single_water_pitcher, e) - X(base, e);
  PASS iff mean dAUC >= -0.005 AND min dAUC >= -0.02 AND mean dMPPE_cm <= +0.2 AND mean dRPE_cm <= +0.2, both twins
  present (missing data cannot pass). Inputs are 4-decimal values; deltas and means are compared unrounded.
Usage: python -I guard_eval_p.py RUNS_DIR OUT.json
"""
import json, os, sys
import numpy as np

RUNS, OUT = sys.argv[1], sys.argv[2]
TW = [21, 22]
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']
RULE = dict(mean_dAUC_min=-0.005, min_dAUC_min=-0.02, mean_dMPPE_cm_max=0.2, mean_dRPE_cm_max=0.2)
EPS = 1e-9


def load(tag, e):
    p = f'{RUNS}/{tag}/ep{e}.json'
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    return dict(r['perception'], registration=r['registration'])


rows, missing = [], []
for e in TW:
    b, s = load('base', e), load('single_water_pitcher', e)
    if b is None or s is None:
        missing.append(e); continue
    rows.append(dict(ep=e, **{f'd{k}': float(s[k] - b[k]) for k in KEYS}, base={k: b[k] for k in KEYS},
                     swap={k: s[k] for k in KEYS}, per_obj_AUC_base=b['per_obj_AUC'], per_obj_AUC_swap=s['per_obj_AUC'],
                     registration_base=b['registration'], registration_swap=s['registration']))
agg = {}
for k in KEYS:
    v = [r[f'd{k}'] for r in rows]
    agg[f'mean_d{k}'] = float(np.mean(v)) if v else None
    agg[f'min_d{k}'] = float(np.min(v)) if v else None
checks = dict(mean_dAUC=agg['mean_dAUC'] is not None and agg['mean_dAUC'] >= RULE['mean_dAUC_min'] - EPS,
              min_dAUC=agg['min_dAUC'] is not None and agg['min_dAUC'] >= RULE['min_dAUC_min'] - EPS,
              mean_dMPPE=agg['mean_dMPPE_cm'] is not None and agg['mean_dMPPE_cm'] <= RULE['mean_dMPPE_cm_max'] + EPS,
              mean_dRPE=agg['mean_dRPE_cm'] is not None and agg['mean_dRPE_cm'] <= RULE['mean_dRPE_cm_max'] + EPS,
              complete=not missing)
res = dict(rule=RULE, object='water_pitcher', twins=TW, missing=missing, PASS=all(checks.values()), checks=checks,
           **agg, per_twin=rows)
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('PASS', 'checks', 'mean_dAUC', 'min_dAUC', 'mean_dMPPE_cm', 'mean_dRPE_cm',
                                      'mean_dSP_SR', 'mean_dMP_SR', 'missing')}, indent=1))
for r in rows:
    print(r['ep'], 'dAUC %+.4f' % r['dAUC'], 'pitcher AUC', r['per_obj_AUC_base'], '->', r['per_obj_AUC_swap'])
