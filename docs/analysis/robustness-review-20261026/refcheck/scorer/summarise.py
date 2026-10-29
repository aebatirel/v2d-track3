"""Tables for README.md from sens/ep*.json (score_variants.py outputs): AUC per variant and its change vs 'base'.
Usage: python -I summarise.py DIR_WITH_JSONS [trajectory=perception] > table.md
"""
import glob, json, os, sys
d = sys.argv[1]; traj = sys.argv[2] if len(sys.argv) > 2 else 'perception'
rows, allv = [], []
for f in sorted(glob.glob(f'{d}/ep*.json'), key=lambda x: int(os.path.basename(x)[2:-5].split('_')[0])):
    r = json.load(open(f)); v = r['variants']
    if 'base' not in v or traj not in v['base']:
        continue
    for k in v:
        if k not in allv:
            allv.append(k)
    rows.append((r['episode'], r['objects'], v))
print(f'| ep | objects | base AUC | ' + ' | '.join(f'{k} dAUC' for k in allv if k != 'base') + ' |')
print('|' + '---|' * (3 + len(allv) - 1))
deltas = {k: [] for k in allv}
for ep, objs, v in rows:
    b = v['base'][traj]['AUC']; cells = []
    for k in allv:
        if k == 'base':
            continue
        if k in v:
            dlt = v[k][traj]['AUC'] - b; deltas[k].append(dlt); cells.append(f'{dlt:+.4f}')
        else:
            cells.append('n/a')
    print(f'| {ep} | {" + ".join(objs)} | {b:.4f} | ' + ' | '.join(cells) + ' |')
print('| mean abs | | | ' + ' | '.join(f'{sum(abs(x) for x in deltas[k]) / max(len(deltas[k]), 1):.4f}' for k in allv if k != 'base') + ' |')
print('| mean signed | | | ' + ' | '.join(f'{sum(deltas[k]) / max(len(deltas[k]), 1):+.4f}' for k in allv if k != 'base') + ' |')
print()
print('Other metrics (base -> variant), SP_SR / MP_SR / MPPE_cm / RPE_cm:')
for ep, objs, v in rows:
    b = v['base'][traj]
    parts = []
    for k in allv:
        if k == 'base' or k not in v:
            continue
        x = v[k][traj]
        ch = [m for m in ('SP_SR', 'MP_SR') if x[m] != b[m]]
        parts.append(f'{k}: MPPE {x["MPPE_cm"] - b["MPPE_cm"]:+.2f} RPE {x["RPE_cm"] - b["RPE_cm"]:+.2f}' + (f' {ch} flips' if ch else ''))
    print(f'- ep{ep} (base SP {b["SP_SR"]}, MP {b["MP_SR"]}, MPPE {b["MPPE_cm"]}, RPE {b["RPE_cm"]}): ' + '; '.join(parts))
