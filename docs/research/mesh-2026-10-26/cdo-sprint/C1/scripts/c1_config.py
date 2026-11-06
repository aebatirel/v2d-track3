"""C1 report: twin numbers for the configuration "pack 9a + C1 swaps" (pot, lid, rack from C0; beige cup = T1
lathe; mini dust pan = T2 placed pick; blue cup and everything else library_v3), rebuilt from stored
score_registered.py run JSONs. No new scoring, no scan or parquet read: it only reads our own run JSONs.

Per twin, the stored run whose meshes equal this configuration for every object in that episode:
  - the 15 C0 twins without beige_cup     -> the run pack9a_config.py picks (c0 / base / single_<obj>)
  - ep11 (blue_cup + beige_cup; no pot, lid or rack) -> T1 single_ep11 (base + beige lathe)
  - ep18, ep39, ep40 (dust-pan twins)      -> T2 single_mini_dust_pan_ep<e>
The script fails if a twin holds an object combination that no stored run covers. Deltas are (that run) - base, as in
guard_eval.py. Reported only, as a [D] diagnostic of the configuration; it selects nothing.

Usage: python -I c1_config.py CDO_SPRINT_DIR OUT.json
"""
import json
import sys

import numpy as np

D, OUT = sys.argv[1], sys.argv[2]
C0A = f'{D}/C0/auc'
T1A = f'{D}/C1/T1-beige-lathe/results/auc'
T2A = f'{D}/C1/T2-probe-picks/results/auc'
C0_TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]
DP_TWINS = [18, 39, 40]
SWAP9A = {'white_pot', 'white_pot_lid', 'plastic_dish_rack'}
SWAPC1 = {'beige_cup', 'mini_dust_pan'}
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']


def js(p):
    return json.load(open(p))


rows = []
for e in C0_TWINS + DP_TWINS:
    if e in C0_TWINS:
        b = js(f'{C0A}/base/ep{e}.json')
    else:
        b = js(f'{T2A}/base_ep{e}.json')
    objs = set(b['objects'])
    sw9 = objs & SWAP9A
    sw1 = objs & SWAPC1
    if sw1 == {'beige_cup'}:
        assert e == 11 and not sw9, e
        b1 = js(f'{T1A}/base_ep11.json')
        assert b1['objects'] == b['objects'] and b1['perception'] == b['perception'], 'T1 base != C0 base on ep11'
        s, src = js(f'{T1A}/single_ep11.json'), 'C1/T1 single_ep11'
    elif sw1 == {'mini_dust_pan'}:
        assert e in DP_TWINS and not sw9 and 'blue_cup' not in objs, e
        s, src = js(f'{T2A}/single_mini_dust_pan_ep{e}.json'), f'C1/T2 single_mini_dust_pan_ep{e}'
    elif not sw1:
        assert e in C0_TWINS, e
        if 'blue_cup' not in objs:
            tag = 'c0'
        elif not sw9:
            tag = 'base'
        elif len(sw9) == 1:
            tag = f'single_{next(iter(sw9))}'
        else:
            raise SystemExit(f'ep{e}: no stored run matches (objects {sorted(objs)})')
        s, src = js(f'{C0A}/{tag}/ep{e}.json'), f'C0 {tag}/ep{e}'
    else:
        raise SystemExit(f'ep{e}: both C1 objects present, no stored run (objects {sorted(objs)})')
    assert s['objects'] == b['objects'], e
    rows.append(dict(ep=e, objects=b['objects'], run=src, swapped=sorted(sw9 | sw1),
                     **{f'd{k}': float(s['perception'][k] - b['perception'][k]) for k in KEYS}))


def agg(rr):
    out = dict(n=len(rr), eps=[r['ep'] for r in rr])
    for k in KEYS:
        v = [r[f'd{k}'] for r in rr]
        out[f'mean_d{k}'] = round(float(np.mean(v)), 5)
        out[f'min_d{k}'] = round(float(np.min(v)), 5)
        out[f'max_d{k}'] = round(float(np.max(v)), 5)
    out['argmin_dAUC_ep'] = rr[int(np.argmin([r['dAUC'] for r in rr]))]['ep']
    return out


res = dict(note='[D] configuration pack 9a + C1 (beige T1 lathe, dust pan T2 placed pick; blue cup library_v3), '
                'rebuilt from stored run JSONs; reported only, not a selection',
           all_18=agg(rows), touched=agg([r for r in rows if r['swapped']]),
           c1_only=agg([r for r in rows if set(r['swapped']) & SWAPC1]), per_twin=rows)
json.dump(res, open(OUT, 'w'), indent=1)
for r in rows:
    print(f"ep{r['ep']:<3d} {r['run']:34s} {','.join(r['objects']):45s} dAUC {r['dAUC']:+.4f} "
          f"dMPPE {r['dMPPE_cm']:+.4f} dRPE {r['dRPE_cm']:+.4f} dSP {r['dSP_SR']:+.1f} dMP {r['dMP_SR']:+.1f}")
for k in ('all_18', 'touched', 'c1_only'):
    a = res[k]
    print(f"{k:8s} n={a['n']:2d} mean dAUC {a['mean_dAUC']:+.4f} min {a['min_dAUC']:+.4f} (ep{a['argmin_dAUC_ep']}) "
          f"mean dMPPE {a['mean_dMPPE_cm']:+.4f} mean dRPE {a['mean_dRPE_cm']:+.4f} mean dSP {a['mean_dSP_SR']:+.4f} "
          f"mean dMP {a['mean_dMP_SR']:+.4f}")
