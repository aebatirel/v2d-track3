"""Format the start-frame survey (f0_survey.py outputs) into a ranked markdown table and one JSON.
Also joins, read-only, the pack's own FlashCHORD zero-action rest checks [R] (tools/rest_check.py output stored with each
grasp-lock reference; objects within 5 mm / 2 deg until a hand comes for them) where they exist.
Usage: python -I f0_report.py F0OUT_DIR RESTCHECK_DIR OUT.json > f0_tables.md"""
import glob
import json
import os
import sys

src, rcd, outp = sys.argv[1:4]
E = {}
for p in sorted(glob.glob(f'{src}/ep*.json'), key=lambda s: int(os.path.basename(s)[2:-5])):
    d = json.load(open(p)); E[d['ep']] = d
RC = {}
for p in glob.glob(f'{rcd}/ep*.json'):
    RC[int(os.path.basename(p)[2:-5])] = json.load(open(p))
rows, rest_rows, bad = [], [], []
for e, d in E.items():
    if d['status'] != 'ok':
        bad.append((e, d['status'])); continue
    for fd in d['frames']:
        for n, o in fd['objects'].items():
            rc = RC.get(e, {}).get('objects', {}).get(n)
            r = dict(ep=e, object=n, frame=fd['frame'], kind=fd['kind'], mm=o['settle_mm'], deg=o['settle_deg'],
                     max_mm=o['max_mm'], max_deg=o['max_deg'], falls=o['falls_over'], moved=o['moved'],
                     j_mm_med=o['jitter16']['mm']['median'], j_mm_max=o['jitter16']['mm']['max'], j_falls=o['jitter16']['falls'],
                     hand=o['hand_mm'], pen=o['pen_mm'], pieces=d['objects'][n]['pieces'], flags=list(o['flags']),
                     support=o['support'], com_height_mm=o['com_height_mm'],
                     pairs={k: v for k, v in fd['pairs'].items() if n in k.split('|')},
                     fc_rest=None if rc is None else dict(until_frame=rc['until_frame'], max_mm=rc['max_mm'], max_deg=rc['max_deg'], ok=rc['ok']))
            m1 = o['support']['band1mm']['com_margin_mm']
            if r['moved'] and not r['flags'] and m1 is not None and m1 >= 0 and o['com_height_mm'] > 0:
                import math
                r['flags'].append(f"narrow footprint: COM {m1} mm inside the 1 mm band at {o['com_height_mm']} mm height "
                                  f"(tips past {math.degrees(math.atan(m1 / o['com_height_mm'])):.1f} deg)")
            r['kind'] = fd['kind']
            (rows if fd['frame'] == 0 else rest_rows).append(r)
key = lambda r: -(r['mm'] if r['mm'] is not None else 1e9)
rows.sort(key=key); rest_rows.sort(key=key)
json.dump(dict(f0=rows, first_H30_rest=rest_rows, not_reconstructed=bad, episodes=E, flashchord_rest_checks_R=RC),
          open(outp, 'w'), indent=1, default=float)


def fmt(r):
    pr = '; '.join(f"{k.replace(r['object'], '').strip('|')} {v}" for k, v in r['pairs'].items() if v > 0) or '0'
    fc = '-' if r['fc_rest'] is None else (f"{r['fc_rest']['max_mm']} / {r['fc_rest']['max_deg']} until f{r['fc_rest']['until_frame']}"
                                          f"{'' if r['fc_rest']['ok'] else ' (fail)'}")
    return (f"| {r['ep']} | {r['object']} | f{r['frame']} | **{r['mm']} / {r['deg']}** | {r['max_mm']} / {r['max_deg']} | "
            f"{'**yes**' if r['falls'] else 'no'} | {r['j_mm_med']} / {r['j_mm_max']} ({r['j_falls']}/16 fall) | {r['hand']} | "
            f"{r['pen']} | {pr} | {('; '.join(r['flags']) or '-') if r['moved'] else '-'} | {fc} |")


H = ('| Eval | Object | Frame | Settle at 2 s, mm / deg | Max during, mm / deg | Falls over | 16 jittered copies: median / max mm | '
     'Hand at frame, mm | Table pen., mm | Packed overlap, cm3 | Visible cause (heuristic) | FlashCHORD rest check [R], mm / deg |\n'
     '|---|---|---|---|---|---|---|---|---|---|---|---|')
print('## Start frame f0, ranked by displacement\n'); print(H); print('\n'.join(fmt(r) for r in rows))
print('\n## First H30 rest frame (report only; where an object has a hand within 30 mm at f0: that object\'s own first '
      'H30 rest run, and the first all-object one)\n'); print(H)
print('\n'.join(fmt(r) for r in rest_rows))
print('\n## Not reconstructed\n')
print('\n'.join(f'- eval {e}: {s}' for e, s in bad) or '- none')
