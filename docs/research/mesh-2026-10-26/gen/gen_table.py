"""Batch-2 generative probe: per-object table of the one-shot scan scores [D] (2026-10-29).
Usage: gen_table.py SCORES.jsonl [OUT.md]
"""
import json, sys
from collections import defaultdict

LIB = dict(white_pot=0.437, blue_cup=0.523, plastic_dish_rack=0.555, beige_cup=0.856, mini_sweeper=0.317,
           mini_dust_pan=0.331, white_pot_lid=0.421, water_pitcher=0.894, wooden_piece_1=0.222, wooden_piece_2=0.216)
BEST = dict(white_pot=0.342, white_pot_lid=0.220, plastic_dish_rack=0.456, blue_cup=0.291)
MODELS = ['pixal_mv', 'pixal_v1', 'trellis2', 'triposg', 'hy21', 'sam3d']
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
by = defaultdict(list)
for r in rows:
    if 'error' in r:
        continue
    by[(r['object'], r['group'])].append(r)
objs = list(LIB)
out = ['| object | library_v3 | best hand-built | ' + ' | '.join(MODELS) + ' |',
       '|---|---|---|' + '---|' * len(MODELS)]
for o in objs:
    cells = []
    for m in MODELS:
        rs = by.get((o, m), [])
        if not rs:
            cells.append('-'); continue
        c = [r['cdo_eval'] if r.get('cdo_eval') is not None else r['cdo_all'] for r in rs]
        cells.append(f'{sum(c) / len(c):.3f} ({min(c):.3f}-{max(c):.3f}, n={len(c)})')
    out.append(f'| {o} | {LIB[o]:.3f} | {BEST.get(o, "-")} | ' + ' | '.join(cells) + ' |')
out += ['', 'ADD (mm, mean over seeds of add_eval) and flips (all scorer seeds) per mesh:', '',
        '| label | CD-O eval | ADD eval mm | flips | amb mm |', '|---|---|---|---|---|']
for r in sorted(rows, key=lambda r: (r.get('object', ''), r.get('group', ''), r.get('label', ''))):
    if 'error' in r:
        out.append(f'| {r["label"]} | ERROR {r["error"][:60]} | | | |'); continue
    out.append(f'| {r["label"]} | {r.get("cdo_eval") if r.get("cdo_eval") is not None else r.get("cdo_all"):.3f} | '
               f'{(r.get("add_eval") or r.get("add_all") or 0):.1f} | {r.get("flips_all")}/{r.get("n_seeds")} | '
               f'{r.get("amb_mm", float("nan")):.2f} |')
txt = '\n'.join(out) + '\n'
print(txt)
if len(sys.argv) > 2:
    open(sys.argv[2], 'w').write(txt)
