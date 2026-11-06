#!/usr/bin/env python
"""T3 AUC guard verdict (PREREG.md section 6; the C0 rule). Reads run_auc.sh's score_registered.py JSONs ('perception'
entry = the episode's registered scores over all its objects) and applies the rule; nothing else.
  dX_e = X(single_<o>, e) - X(base, e) for each twin e.
  PASS iff mean dAUC >= -0.005 AND min dAUC >= -0.02 AND mean dMPPE_cm <= +0.2 AND mean dRPE_cm <= +0.2.
  A missing base or single result on any twin fails the guard.
Usage: python -I guard.py RUNS_DIR OBJ OUT.json
"""
import json, os, sys
import numpy as np

RUNS, O, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
OTW = {'white_pot': [0, 2, 26, 27, 41, 42, 43, 44, 45], 'white_pot_lid': [0, 2], 'plastic_dish_rack': [12, 13, 26, 27, 31],
       'blue_cup': [11, 12, 13, 21, 22], 'beige_cup': [11], 'water_pitcher': [21, 22], 'mini_sweeper': [18, 31],
       'mini_dust_pan': [18, 39, 40], 'wooden_piece_1': [23, 24], 'wooden_piece_2': [23, 24]}
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']
EPS = 1e-9


def load(tag, e):
    p = f'{RUNS}/{tag}/ep{e}.json'
    return json.load(open(p))['perception'] if os.path.exists(p) else None


rows, missing = [], []
for e in OTW[O]:
    b, s = load('base', e), load(f'single_{O}', e)
    if b is None or s is None:
        missing.append(e); continue
    rows.append(dict(ep=e, base={k: b[k] for k in KEYS}, single={k: s[k] for k in KEYS},
                     d={k: s[k] - b[k] for k in KEYS}))
res = dict(object=O, twins=OTW[O], rows=rows, missing=missing)
if rows and not missing:
    dA = np.array([r['d']['AUC'] for r in rows])
    res.update(mean_dAUC=float(dA.mean()), min_dAUC=float(dA.min()),
               mean_dMPPE_cm=float(np.mean([r['d']['MPPE_cm'] for r in rows])),
               mean_dRPE_cm=float(np.mean([r['d']['RPE_cm'] for r in rows])),
               mean_dSP_SR=float(np.mean([r['d']['SP_SR'] for r in rows])),
               mean_dMP_SR=float(np.mean([r['d']['MP_SR'] for r in rows])))
    res['PASS'] = bool(res['mean_dAUC'] >= -0.005 - EPS and res['min_dAUC'] >= -0.02 - EPS
                       and res['mean_dMPPE_cm'] <= 0.2 + EPS and res['mean_dRPE_cm'] <= 0.2 + EPS)
else:
    res['PASS'] = False
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}))
