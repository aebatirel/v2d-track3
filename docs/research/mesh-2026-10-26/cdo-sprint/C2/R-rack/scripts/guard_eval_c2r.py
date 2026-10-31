"""C2/R AUC guard verdict (PREREG C2/R-rack section 7): C0's guard_eval.py with OTW reduced to the rack and the
joint report removed; the rule is unchanged. Original docstring follows.
C0 AUC guard verdict (PREREG.md). Reads the score_registered.py JSONs of run_auc_guard.sh and applies the
pre-registered rule; no other selection. Metrics are the 'perception' entry of each JSON (the episode's registered
scores over all its objects, as the board scores an episode).

  dX_e = X(single/o, e) - X(base, e) for each twin e of o.
  o ADOPTED iff mean dAUC >= -0.005 AND min dAUC >= -0.02 AND mean dMPPE_cm <= +0.2 AND mean dRPE_cm <= +0.2.
  An object with a missing base or single result on any of its twins (after at most one unchanged re-run) is NOT
  adopted (missing data cannot pass the guard).
  C0-final = the adopted objects. Joint c0 - base deltas over all 15 twins are reported only. SP_SR, MP_SR reported.

Inputs are the 4-decimal values score_registered.py writes; deltas and their means are compared unrounded.
Usage: python -I guard_eval.py RUNS_DIR OUT.json
"""
import json
import os
import sys

import numpy as np

RUNS, OUT = sys.argv[1], sys.argv[2]
TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]
OTW = {'plastic_dish_rack': [12, 13, 26, 27, 31]}
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']
RULE = dict(mean_dAUC_min=-0.005, min_dAUC_min=-0.02, mean_dMPPE_cm_max=0.2, mean_dRPE_cm_max=0.2)
EPS = 1e-9    # float representation only: a value exactly at a threshold (4-decimal inputs) counts as inside


def load(tag, e):
    p = f'{RUNS}/{tag}/ep{e}.json'
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    return dict(r['perception'], registration=r['registration'])


def deltas(tag, eps):
    rows, missing = [], []
    for e in eps:
        b, s = load('base', e), load(tag, e)
        if b is None or s is None:
            missing.append(e)
            continue
        row = dict(ep=e, **{f'd{k}': float(s[k] - b[k]) for k in KEYS},
                   base={k: b[k] for k in KEYS}, swap={k: s[k] for k in KEYS},
                   per_obj_AUC_base=b['per_obj_AUC'], per_obj_AUC_swap=s['per_obj_AUC'],
                   registration_base=b['registration'], registration_swap=s['registration'])
        rows.append(row)
    agg = {}
    for k in KEYS:
        v = [r[f'd{k}'] for r in rows]
        agg[f'mean_d{k}'] = float(np.mean(v)) if v else None              # unrounded: the rule compares these
        agg[f'min_d{k}'] = float(np.min(v)) if v else None
        agg[f'max_d{k}'] = float(np.max(v)) if v else None
    return rows, missing, agg


res = dict(rule=RULE, objects={})
for o, eps in OTW.items():
    rows, missing, agg = deltas(f'single_{o}', eps)
    checks = dict(mean_dAUC=agg['mean_dAUC'] is not None and agg['mean_dAUC'] >= RULE['mean_dAUC_min'] - EPS,
                  min_dAUC=agg['min_dAUC'] is not None and agg['min_dAUC'] >= RULE['min_dAUC_min'] - EPS,
                  mean_dMPPE=agg['mean_dMPPE_cm'] is not None and agg['mean_dMPPE_cm'] <= RULE['mean_dMPPE_cm_max'] + EPS,
                  mean_dRPE=agg['mean_dRPE_cm'] is not None and agg['mean_dRPE_cm'] <= RULE['mean_dRPE_cm_max'] + EPS,
                  complete=not missing)
    res['objects'][o] = dict(twins=eps, missing=missing, adopted=all(checks.values()), checks=checks, **agg,
                             per_twin=rows)
res['c0_final'] = [o for o, v in res['objects'].items() if v['adopted']]
json.dump(res, open(OUT, 'w'), indent=1)
print('object             adopted  n  mean_dAUC  min_dAUC  mean_dMPPE  mean_dRPE  mean_dSP  mean_dMP  missing')
for o, v in res['objects'].items():
    f4 = lambda x: 'NA' if x is None else f'{x:+.4f}'
    print(f"{o:18s} {str(v['adopted']):7s} {len(v['per_twin']):2d}  {f4(v['mean_dAUC'])}  {f4(v['min_dAUC'])}  "
          f"{f4(v['mean_dMPPE_cm'])}  {f4(v['mean_dRPE_cm'])}  {f4(v['mean_dSP_SR'])}  {f4(v['mean_dMP_SR'])}  {v['missing']}")
print('C2/R guard adopted:', res['c0_final'])
