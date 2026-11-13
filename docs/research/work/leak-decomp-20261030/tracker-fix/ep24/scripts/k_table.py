"""Merge the rule-K runs and print the 20-episode table + summary (markdown)."""
import json, sys, numpy as np
D = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/out'
E = {}
for f in ('A', 'B', 'C'):
    E.update(json.load(open(f'{D}/vo_k_{f}.json'))['episodes'])
json.dump(dict(note='rule K (vo_anchor_test2.py), merged A/B/C runs; ORACLE scoring vs public mocap', episodes=E), open(f'{D}/vo_k_all.json', 'w'), indent=1)
keys = ['K_h3_r5_w2', 'K_h3_r5_w1', 'K_h3_r8_w2', 'K_h5_r5_w2', 'K_h5_r8_w2']
eps = sorted(E, key=int)
print('| ep | KF | P_o \\* base | P_o Δ\\* / Δlib (primary h3 r5 w2) | absorbed steps, |c| end cm | P_s \\* base | P_s Δ\\* | refine P Δ\\* / Δlib |')
print('|---|---|---|---|---|---|---|---|')
for e in eps:
    r = E[e]; po = r['Po']; k = po['K_h3_r5_w2']; ps = r.get('Ps'); pr = r['Pr']['K_h3_r5_w2']; prb = r['Pr']['base']
    print(f"| {e} | {po['keyframes']} | {po['base']['star']:.4f} | {k['star'] - po['base']['star']:+.4f} / {k['lib'] - po['base']['lib']:+.4f} | {k['n_absorb']}, {k['corr_cm_end']:.2f} | "
          + (f"{ps['base']['star']:.4f} | {ps['K_h3_r5_w2']['star'] - ps['base']['star']:+.4f}" if ps else '– | –')
          + f" | {pr['star'] - prb['star']:+.4f} / {pr['lib'] - prb['lib']:+.4f} |")
print()
print('| config | arm | conv | mean Δ (20) | w/o ep24 | min | max | + / − (|Δ| > 0.0005) | episodes < −0.01 |')
print('|---|---|---|---|---|---|---|---|---|')
for key in keys:
    for arm in ('Po', 'Pr', 'Ps'):
        for conv in ('star', 'lib'):
            d = {e: E[e][arm][key][conv] - E[e][arm]['base'][conv] for e in eps if arm in E[e] and E[e][arm]['base'][conv] is not None}
            if not d:
                continue
            v = np.array(list(d.values())); w = np.array([x for e, x in d.items() if e != '24'])
            bad = [f'{e} {x:+.3f}' for e, x in d.items() if x < -0.01]
            print(f"| {key[2:]} | {arm} | {'\\*' if conv == 'star' else 'lib'} | {v.mean():+.4f} | {w.mean():+.4f} | {v.min():+.4f} | {v.max():+.4f} | {(v > 0.0005).sum()} / {(v < -0.0005).sum()} | {', '.join(bad) or 'none'} |")
