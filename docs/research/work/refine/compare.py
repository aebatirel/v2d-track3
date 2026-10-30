"""Compare a scored refine arm with the baseline (SCORER SIDE: reads scores derived from mocap; never import from refine).
Prints per-episode lib/scan AUC, per-object lib AUC and deltas, the 20- and 19-episode (without ep23) means, and the
plan.md §1 gate-2 check (no episode down by more than 0.02 lib). Writes ARM/score/compare.json.
Usage: python3 -I compare.py ARM BASELINE_DIR [EPS...]   (BASELINE_DIR holds ep<N>.json from the baseline combine.py)"""
import json, os, sys
import numpy as np

arm, base = sys.argv[1], sys.argv[2]
eps = [int(x) for x in sys.argv[3:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
rows = []
for e in eps:
    b = json.load(open(f'{base}/ep{e}.json'))
    r = dict(ep=e)
    for k in ('lib', 'scan'):
        p = f'{arm}/score/ep{e}_{k}.json'
        if not os.path.exists(p):
            continue
        s = json.load(open(p))['perception']
        r[k] = s['AUC']; r[f'{k}_base'] = b[k]['AUC']; r[f'd_{k}'] = round(s['AUC'] - b[k]['AUC'], 4)
        r[f'{k}_obj'] = {n: (v, round(v - b[k]['per_obj_AUC'][n], 4)) for n, v in s['per_obj_AUC'].items()}
    rows.append(r)
print(f'{"ep":>3} {"lib":>7} {"Δlib":>8} {"scan":>7} {"Δscan":>8}  per-object lib (Δ)')
for r in rows:
    if 'lib' not in r:
        print(f'{r["ep"]:>3} (not scored)'); continue
    ob = ', '.join(f'{n} {v:.3f} ({d:+.3f})' for n, (v, d) in r['lib_obj'].items())
    print(f'{r["ep"]:>3} {r["lib"]:7.4f} {r["d_lib"]:+8.4f} {r.get("scan", float("nan")):7.4f} {r.get("d_scan", float("nan")):+8.4f}  {ob}')
summ = {}
for k in ('lib', 'scan'):
    rr = [r for r in rows if k in r]
    if not rr:
        continue
    m = lambda key, sel: round(float(np.mean([r[key] for r in sel])), 4) if sel else None  # noqa: E731
    no23 = [r for r in rr if r['ep'] != 23]
    summ[k] = dict(n=len(rr), mean=m(k, rr), base=m(f'{k}_base', rr), delta=m(f'd_{k}', rr),
                   mean_no23=m(k, no23), base_no23=m(f'{k}_base', no23), delta_no23=m(f'd_{k}', no23),
                   better=sum(r[f'd_{k}'] > 0 for r in rr), worse=sum(r[f'd_{k}'] < 0 for r in rr),
                   drops_gt_0p02=[r['ep'] for r in rr if r[f'd_{k}'] < -0.02])
    print(f'{k}: {json.dumps(summ[k])}')
json.dump(dict(rows=rows, summary=summ), open(f'{arm}/score/compare.json', 'w'), indent=1)
