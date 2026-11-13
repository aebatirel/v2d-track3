"""C1/T2 AUC guard verdict (PREREG.md s6; the C0 rule applied exactly). Reads the score_registered.py JSONs; metrics
are the 'perception' entry (the episode's registered scores over all its objects).
  base   = C0's runs/base/ep<e>.json where auc_prep.json says reusable (same library_v3 dir, same track file),
           else our runs/base/ep<e>.json.
  dX_e   = X(single_<o>, e) - X(base, e) for each twin e of o.
  PASS iff mean dAUC >= -0.005 AND min dAUC >= -0.02 AND mean dMPPE_cm <= +0.2 AND mean dRPE_cm <= +0.2, and no
  twin is missing. Deltas are compared unrounded on the 4-decimal outputs (a value at a threshold passes).
Usage: python -I guard_t2.py AUC_DIR OUT.json OBJ [OBJ ...]
"""
import json, os, sys
import numpy as np

D, OUT, objs = sys.argv[1], sys.argv[2], sys.argv[3:]
SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
OTW = {'water_pitcher': [21, 22], 'mini_dust_pan': [18, 39, 40], 'beige_cup': [11]}
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']
RULE = dict(mean_dAUC_min=-0.005, min_dAUC_min=-0.02, mean_dMPPE_cm_max=0.2, mean_dRPE_cm_max=0.2)
EPS = 1e-9
prep = json.load(open(f'{D}/auc_prep.json'))


def load(p):
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    return dict(r['perception'], registration=r['registration'], meshes=r.get('meshes'))


res = dict(rule=RULE, objects={})
for o in objs:
    rows, missing = [], []
    for e in OTW[o]:
        reuse = prep['c0_reuse'][str(e)]['reusable']
        bp = f'{SCR}/cdo_c0/runs/base/ep{e}.json' if reuse else f'{D}/runs/base/ep{e}.json'
        b, s = load(bp), load(f'{D}/runs/single_{o}/ep{e}.json')
        if b is None or s is None:
            missing.append(e)
            continue
        rows.append(dict(ep=e, base_source=bp, **{f'd{k}': float(s[k] - b[k]) for k in KEYS},
                         base={k: b[k] for k in KEYS}, swap={k: s[k] for k in KEYS},
                         per_obj_AUC_base=b['per_obj_AUC'], per_obj_AUC_swap=s['per_obj_AUC'],
                         registration_base=b['registration'].get(o), registration_swap=s['registration'].get(o)))
    agg = {}
    for k in KEYS:
        v = [r[f'd{k}'] for r in rows]
        agg[f'mean_d{k}'] = float(np.mean(v)) if v else None
        agg[f'min_d{k}'] = float(np.min(v)) if v else None
        agg[f'max_d{k}'] = float(np.max(v)) if v else None
    checks = dict(mean_dAUC=agg['mean_dAUC'] is not None and agg['mean_dAUC'] >= RULE['mean_dAUC_min'] - EPS,
                  min_dAUC=agg['min_dAUC'] is not None and agg['min_dAUC'] >= RULE['min_dAUC_min'] - EPS,
                  mean_dMPPE=agg['mean_dMPPE_cm'] is not None and agg['mean_dMPPE_cm'] <= RULE['mean_dMPPE_cm_max'] + EPS,
                  mean_dRPE=agg['mean_dRPE_cm'] is not None and agg['mean_dRPE_cm'] <= RULE['mean_dRPE_cm_max'] + EPS,
                  complete=not missing)
    res['objects'][o] = dict(twins=OTW[o], missing=missing, guard_pass=all(checks.values()), checks=checks, **agg,
                             per_twin=rows)
json.dump(res, open(OUT, 'w'), indent=1)
f4 = lambda x: 'NA' if x is None else f'{x:+.4f}'
print('object          pass   n  mean_dAUC  min_dAUC  mean_dMPPE  mean_dRPE  mean_dSP  mean_dMP  missing')
for o, v in res['objects'].items():
    print(f"{o:15s} {str(v['guard_pass']):6s} {len(v['per_twin']):2d}  {f4(v['mean_dAUC'])}  {f4(v['min_dAUC'])}  "
          f"{f4(v['mean_dMPPE_cm'])}  {f4(v['mean_dRPE_cm'])}  {f4(v['mean_dSP_SR'])}  {f4(v['mean_dMP_SR'])}  {v['missing']}")
    for r in v['per_twin']:
        print(f"   ep{r['ep']}: dAUC {r['dAUC']:+.4f} dMPPE {r['dMPPE_cm']:+.4f} dRPE {r['dRPE_cm']:+.4f} "
              f"obj AUC {r['per_obj_AUC_base'].get(o)} -> {r['per_obj_AUC_swap'].get(o)} "
              f"reg rot {r['registration_base']['rot_deg'] if r['registration_base'] else None} -> "
              f"{r['registration_swap']['rot_deg'] if r['registration_swap'] else None}")
