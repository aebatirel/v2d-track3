#!/usr/bin/env python3
"""Apply the PREREG flags to the eval screen outputs and rank (inference side only).
Usage: python3 final.py SCREEN_EVAL.json DEPTH_EVAL.json EVENTS_EVAL.json ID_DIR OUT.json"""
import json
import sys

import numpy as np

scr, dep, evs, iddir, out = sys.argv[1:6]
S = json.load(open(scr))['items']
DP = {(r['mode'], r['ep'], r['obj']): r for r in json.load(open(dep))}
EV = {(e['ep'], e['obj']): e['events'] for e in json.load(open(evs))}


def maxrun(v):
    m = r = 0
    for x in v:
        r = r + 1 if x else 0
        m = max(m, r)
    return m


ident = {}
b = json.load(open(f'{iddir}/ev25_boards_ref.json'))
bp = json.load(open(f'{iddir}/ev25_boards_perc.json'))
for nm, src in (('ref', b), ('perc', bp)):
    d = [f['s_sw'] - f['s_as'] for f in src['frames']]
    run = maxrun([x < -20 for x in d])
    ident[('ref' if nm == 'ref' else 'perc', 25)] = dict(rule='knob d<-20 on >=5 consecutive sampled frames', longest_run=run,
                                                        flag=run >= 5)
for nm in ('ref', 'perc'):
    c = json.load(open(f'{iddir}/ev10_cups_{nm}.json'))
    w = [f['blue_cup']['grey'] - f['beige_cup']['grey'] for f in c['frames'] if f['t'] < 38 and 'blue_cup' in f and 'beige_cup' in f]
    ident[(nm, 10)] = dict(rule='median grey(blue)-grey(beige) over sampled frames < 38 (both cups within 2 cm of frame 0; '
                                'amended window, see README)', median=float(np.median(w)), n=len(w), flag=bool(np.median(w) > 0))

rows = []
for it in S:
    if 'error' in it:
        continue
    kind = it['kind']
    for nm, o in it['objects'].items():
        f = {}
        f['J'] = bool(o['jump_cm_max'] > 5 or o['jump_deg_max'] > 45)
        f['U'] = bool(o['n_below_3cm'] >= 3)
        pen = it.get('pen')
        f['X'] = bool(pen is not None and pen['max_cm'] > 2 and pen['share_gt2cm'] >= 0.10)
        dr = DP.get((kind, it['ep'], nm))
        f['D'] = bool(dr['flag_D']) if dr else None
        if kind == 'ref':
            f['RP'] = bool(o['n_refperc_gt5cm'] >= 10)
        idk = ident.get((kind, it['ep']))
        if idk and nm in ('wooden_piece_1', 'wooden_piece_2', 'blue_cup', 'beige_cup'):
            f['I'] = idk['flag']
        mag = dict(jump_cm=o['jump_cm_max'], jump_deg=o['jump_deg_max'], below_cm=o['below_cm_min'],
                   pen_cm=pen['max_cm'] if pen else 0.0,
                   depth_bad_share=dr['bad_share'] if dr else None, depth_longest_run=dr['longest_run'] if dr else None,
                   depth_runs=dr['runs_ge5'] if dr else None)
        if kind == 'ref':
            mag.update(refperc_cm_max=o['refperc_cm_max'], refperc_deg_max=o['refperc_deg_max'])
        score = max(o['jump_cm_max'] / 5, o['jump_deg_max'] / 45, (dr['bad_share'] / 0.25) if dr else 0,
                    (dr['longest_run'] / 50) if dr else 0)
        rows.append(dict(ep=it['ep'], obj=nm, kind=kind, T=it['T'], flags=[k for k, v in f.items() if v],
                         n_flags=sum(1 for v in f.values() if v), max_ratio=round(score, 2), magnitudes=mag,
                         jump_events=EV.get((it['ep'], nm)) if kind == 'ref' else None))
ref_rows = sorted([r for r in rows if r['kind'] == 'ref'], key=lambda r: (-r['n_flags'], -r['max_ratio']))
perc_only = []
for r in rows:
    if r['kind'] == 'perc' and r['n_flags']:
        rr = [x for x in ref_rows if x['ep'] == r['ep'] and x['obj'] == r['obj']][0]
        extra = sorted(set(r['flags']) - set(rr['flags']))
        if extra:
            perc_only.append(dict(ep=r['ep'], obj=r['obj'], flags_on_P_not_R=extra))
json.dump(dict(identity=[dict(kind=k[0], ep=k[1], **v) for k, v in ident.items()], ranked_reference=ref_rows,
               perception_only_flags=perc_only, all_rows=rows), open(out, 'w'), indent=1)
print('RANKED (policy reference R):')
for r in ref_rows:
    if r['n_flags']:
        m = r['magnitudes']
        print(f"ev{r['ep']:>2} {r['obj']:18s} flags={','.join(r['flags']):8s} ratio={r['max_ratio']:5.2f} jump={m['jump_cm']:.1f}cm/{m['jump_deg']:.0f}deg "
              f"depth_bad={m['depth_bad_share']} run={m['depth_longest_run']} runs={m['depth_runs']}")
print('flags on P only:', perc_only)
print('identity:', json.dumps([dict(kind=k[0], ep=k[1], **v) for k, v in ident.items()]))
print('unflagged reference objects:', sum(1 for r in ref_rows if not r['n_flags']), 'of', len(ref_rows))
