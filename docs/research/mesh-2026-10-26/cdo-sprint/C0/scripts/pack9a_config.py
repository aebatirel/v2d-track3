"""C0 stage 4: twin numbers for the pack-9a configuration (pot, lid, rack swapped; blue cup kept at library_v3),
rebuilt from the 51 stored score_registered.py JSONs of the AUC guard. No new scoring, no scan or parquet read: it
only reads our own run JSONs in auc/.

For each of the 15 twins it picks the stored run whose meshes equal the pack-9a configuration for every object in
that episode:
  - episode has no blue_cup                  -> c0 (blue cup swap is irrelevant there)
  - episode has blue_cup and swaps none of
    pot/lid/rack                             -> base
  - episode has blue_cup and exactly one of
    pot/lid/rack                             -> single_<that object>
and fails if no stored run matches. Deltas are (that run) - base, as in guard_eval.py. Reported only: the PREREG
rule is applied per object by guard_eval.py; this is a [D] diagnostic of the configuration that ships.

Usage: python -I pack9a_config.py AUC_DIR OUT.json
"""
import json
import sys

import numpy as np

AUC, OUT = sys.argv[1], sys.argv[2]
TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]
SWAP9A = {'white_pot', 'white_pot_lid', 'plastic_dish_rack'}
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']


def load(tag, e):
    return json.load(open(f'{AUC}/{tag}/ep{e}.json'))


rows = []
for e in TWINS:
    b = load('base', e)
    objs = set(b['objects'])
    sw = objs & SWAP9A
    if 'blue_cup' not in objs:
        tag = 'c0'
    elif not sw:
        tag = 'base'
    elif len(sw) == 1:
        tag = f'single_{next(iter(sw))}'
    else:
        raise SystemExit(f'ep{e}: no stored run matches pack 9a (objects {sorted(objs)})')
    s = load(tag, e)
    assert s['objects'] == b['objects'], e
    rows.append(dict(ep=e, objects=b['objects'], run=tag, swapped_9a=sorted(sw),
                     **{f'd{k}': float(s['perception'][k] - b['perception'][k]) for k in KEYS},
                     per_obj_AUC_base=b['perception']['per_obj_AUC'], per_obj_AUC_9a=s['perception']['per_obj_AUC']))


def agg(rr):
    out = dict(n=len(rr), eps=[r['ep'] for r in rr])
    for k in KEYS:
        v = [r[f'd{k}'] for r in rr]
        out[f'mean_d{k}'] = float(np.mean(v))
        out[f'min_d{k}'] = float(np.min(v))
        out[f'max_d{k}'] = float(np.max(v))
    out['argmin_dAUC_ep'] = rr[int(np.argmin([r['dAUC'] for r in rr]))]['ep']
    return out


res = dict(note='[D] pack-9a configuration (pot, lid, rack swapped; blue cup library_v3) rebuilt from stored runs; '
                'reported only, not a selection',
           all_15=agg(rows), touched=agg([r for r in rows if r['swapped_9a']]), per_twin=rows)
json.dump(res, open(OUT, 'w'), indent=1)
for r in rows:
    print(f"ep{r['ep']:<3d} {r['run']:26s} {','.join(r['objects']):45s} dAUC {r['dAUC']:+.4f} dMPPE {r['dMPPE_cm']:+.4f} "
          f"dRPE {r['dRPE_cm']:+.4f} dSP {r['dSP_SR']:+.1f} dMP {r['dMP_SR']:+.1f}")
for k in ('all_15', 'touched'):
    a = res[k]
    print(f"{k:8s} n={a['n']:2d} mean dAUC {a['mean_dAUC']:+.4f} min {a['min_dAUC']:+.4f} (ep{a['argmin_dAUC_ep']}) "
          f"mean dMPPE {a['mean_dMPPE_cm']:+.4f} mean dRPE {a['mean_dRPE_cm']:+.4f} mean dSP {a['mean_dSP_SR']:+.4f} "
          f"mean dMP {a['mean_dMP_SR']:+.4f}")
