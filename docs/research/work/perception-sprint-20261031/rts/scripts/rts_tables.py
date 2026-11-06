"""Tables for rts README from rts_score.py's output (no new scoring). Usage: python -I rts_tables.py SCORES_JSON OUT_MD SLIM_JSON"""
import json, sys

import numpy as np

d = json.load(open(sys.argv[1]))
E = d['episodes']
eps = sorted(E, key=int)
L = []
L.append('| ep | objects | S2 R_lib Po | ΔR_lib Po | ΔR_lib refineP | ΔR_* Po | S2 RPE_lib Po (cm) | ΔRPE_lib Po (cm) | '
         'near frames (share) | S13 change mean / max (cm), worst object |')
L.append('|---|---|---|---|---|---|---|---|---|---|')
for e in eps:
    x = E[e]
    po, rp = x['arms']['Po'], x['arms']['refineP']
    multi = len(x['names']) > 1
    s13 = po['s13']
    T = po['s13_T']
    near = ', '.join(f"{v['near_frames'] / T:.2f}" for v in s13.values())
    wo = max(s13, key=lambda n: s13[n]['change_cm_max'])
    L.append(f"| {e} | {', '.join(x['names'])} | {po['S2']['lib']['AUC']:.4f} | {po['delta']['lib']['AUC']:+.4f} | "
             f"{rp['delta']['lib']['AUC']:+.4f} | {po['delta']['star']['AUC']:+.4f} | "
             f"{po['S2']['lib']['RPE']:.3f} | {po['delta']['lib']['RPE']:+.3f} | {near} | "
             f"{max(v['change_cm_mean'] for v in s13.values()):.3f} / {s13[wo]['change_cm_max']:.2f}, {wo} f{s13[wo]['change_cm_max_frame']} |"
             if multi else
             f"| {e} | {', '.join(x['names'])} | {po['S2']['lib']['AUC']:.4f} | {po['delta']['lib']['AUC']:+.4f} | "
             f"{rp['delta']['lib']['AUC']:+.4f} | {po['delta']['star']['AUC']:+.4f} | – | – | {near} | "
             f"{max(v['change_cm_mean'] for v in s13.values()):.3f} / {s13[wo]['change_cm_max']:.2f}, {wo} f{s13[wo]['change_cm_max_frame']} |")
L.append('')
L.append('| arm | mean S2 R_lib | mean S13 R_lib | mean ΔR_lib | min ΔR_lib (ep) | better / worse | mean ΔR_* | min ΔR_* | '
         'mean RPE_lib S2 → S13 (multi-object) | mean ΔRPE_lib | ΔRPE > +0.5 cm | rule |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
for arm, r in (('Po', d['primary']), ('refineP', d['replication'])):
    L.append(f"| {arm} | {r['mean_R_lib_S2']:.4f} | {r['mean_R_lib_S13']:.4f} | {r['mean_dR_lib']:+.5f} | {r['min_dR_lib']:+.4f} "
             f"({r['worst_ep']}) | {r['better_worse_lib'][0]} / {r['better_worse_lib'][1]} | {r['mean_dR_star']:+.5f} | "
             f"{r['min_dR_star']:+.4f} | {r['mean_RPE_lib_S2_multi']:.3f} → {r['mean_RPE_lib_S13_multi']:.3f} | "
             f"{r['mean_dRPE_lib_multi']:+.4f} | {r['rpe_flags'] or 'none'} | {r['status']} |")
L.append('')
L.append(f"Verdict: **{d['verdict']}**")
# per-object deltas
L.append('')
L.append('| ep | per-object ΔAUC lib, Po |')
L.append('|---|---|')
for e in eps:
    po = E[e]['arms']['Po']
    L.append(f"| {e} | " + ', '.join(f'{n} {v:+.4f}' for n, v in po['delta']['lib']['per_obj_AUC'].items()) + ' |')
open(sys.argv[2], 'w').write('\n'.join(L) + '\n')
slim = dict(verdict=d['verdict'], rule=d['rule'], primary=d['primary'], replication=d['replication'],
            code_sha256_start=d['code_sha256_start'], code_sha256_end=d['code_sha256_end'],
            started_utc=d['started_utc'], finished_utc=d['finished_utc'],
            episodes={e: dict(names=E[e]['names'], arms={a: {k: E[e]['arms'][a][k] for k in ('input', 'S2', 'S13', 'delta', 's13', 's13_T')}
                                                         for a in E[e]['arms']}) for e in eps})
json.dump(slim, open(sys.argv[3], 'w'), indent=1)
print('\n'.join(L))
