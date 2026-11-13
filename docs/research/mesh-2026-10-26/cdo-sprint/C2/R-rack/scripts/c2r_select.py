#!/usr/bin/env python
"""C2/R pick (PREREG section 5), GT-free.

Eligible: raw watertight AND kit budget ok (c0b_check.py) AND a fidelity value. Pick = lowest sum_mm over all eligible
meshes of the 8 runs (base included); ties at the printed 3 decimals -> fewer raw faces -> label in byte order.
Gate: a pick from the base run means H-R is falsified GT-free (nothing scored). Writes OUT/selection.json and
OUT/fidelity_table.jsonl. Reads only our meshes, fidelity outputs, check outputs and the build records.
Usage: python -I c2r_select.py OUT
"""
import glob, json, os, sys

OUT = sys.argv[1]
rows = []
for f in sorted(glob.glob(f'{OUT}/fid/*.json')):
    t = os.path.basename(f)[:-5]
    k, b = t.split('__', 1)
    r = dict(label=t, set=k, mesh=b)
    try:
        j = [json.loads(l) for l in open(f) if l.startswith('{')][0]
        r.update(fid_o2m=j['obs_to_mesh_mm'], fid_m2o=j['mesh_to_obs_mm'], fid_sum=j['sum_mm'])
    except Exception:  # noqa: BLE001
        r['fid_sum'] = None
    c = f'{OUT}/check/{t}.json'
    if os.path.exists(c):
        cj = json.load(open(c))
        r.update(watertight_raw=cj['watertight_raw'], budget_ok=cj['budget_ok'], faces_raw=cj['faces_raw'],
                 sha256=cj['sha256'], sha1_16=cj['sha1_16'], path=cj['mesh'],
                 budget_faces=cj.get('budget', {}).get('faces'))
    else:
        r.update(watertight_raw=None, budget_ok=None)
    rec = f'{OUT}/cand/{k}/plastic_dish_rack/{"joint" if b.startswith("joint") else b.split("_")[0]}.json'
    if os.path.exists(rec):
        J = json.load(open(rec))
        inf = J['info']
        r['fitted'] = dict(s1=inf['outline_final'].get('s1'), s1e=inf['outline_final'].get('s1e'),
                           kappa=[p['kappa'] for p in inf['pegs']], gx=inf['cup_final'].get('gx'),
                           gy=inf['cup_final'].get('gy'), n_markers=inf.get('n_markers'))
    r['eligible'] = bool(r.get('watertight_raw') and r.get('budget_ok') and r.get('fid_sum') is not None)
    rows.append(r)
with open(f'{OUT}/fidelity_table.jsonl', 'w') as fh:
    for r in rows:
        fh.write(json.dumps(r) + '\n')
el = [r for r in rows if r['eligible']]
if not el:
    json.dump(dict(pick=None, reason='no eligible mesh'), open(f'{OUT}/selection.json', 'w'), indent=1)
    print('NO ELIGIBLE MESH'); sys.exit(1)
el.sort(key=lambda r: (round(r['fid_sum'], 3), r['faces_raw'], r['label'].encode()))
pick = el[0]
base = [r for r in el if r['set'] == 'base']
best_base = base[0] if base else None
sel = dict(pick=pick, gate='H-R falsified GT-free: the pick is a base mesh' if pick['set'] == 'base' else 'pass: the pick has a new part',
           best_base=best_base, n_meshes=len(rows), n_eligible=len(el),
           best_per_set={k: min((r for r in el if r['set'] == k), key=lambda r: r['fid_sum'])['label']
                         for k in sorted({r['set'] for r in el})})
json.dump(sel, open(f'{OUT}/selection.json', 'w'), indent=1)
for r in el[:15]:
    print(r['label'], r['fid_sum'], r['fid_o2m'], r['fid_m2o'], r['faces_raw'], r.get('fitted'))
print(json.dumps(dict(pick=pick['label'], fid=pick['fid_sum'], gate=sel['gate'],
                      best_base=best_base and (best_base['label'], best_base['fid_sum']))))
