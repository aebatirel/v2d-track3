"""Tables and the pre-registered verdicts of the offset experiment from off_scores.json (README §0). No new data read.
Usage: python -I off_tables.py off_scores.json"""
import json, sys
import numpy as np

R = json.load(open(sys.argv[1]))
EPS = sorted(R, key=int)
ARMS = ['Po', 'refineP']
VARS = {'V1': 'mf/whole (primary)', 'V2': 'f0/whole', 'V3': 'f0/prefix'}
NO_OUT = [e for e in EPS if e not in ('0', '23')]


def rule(d):
    d = np.asarray(d)
    m, better, worst = float(d.mean()), int((d >= 0.0001).sum()), float(d.min())
    ok = m >= 0.010 and better >= 12 and worst >= -0.010
    return m, better, worst, ok


print('### Verdicts (lib decisive; rule: mean >= +0.010, >= 12/20 better (>= +0.0001), no episode < -0.010; both arms)\n')
print('| variant | arm | mean dR lib | better / worse / 0 | worst (ep) | rule | mean dR * | mean dR * w/o ep0, ep23 | '
      'share of trk ceiling lib / * | vs Phase-1 0.025 (*, w/o ep0, ep23) |')
print('|---|---|---|---|---|---|---|---|---|---|')
verdict = {}
for v, lab in VARS.items():
    oks = []
    for arm in ARMS:
        dl = [R[e]['arms'][arm][v]['d']['lib'] for e in EPS]
        ds = [R[e]['arms'][arm][v]['d']['star'] for e in EPS]
        m, b, w, ok = rule(dl)
        oks.append(ok)
        we = EPS[int(np.argmin(dl))]
        worse = int((np.asarray(dl) <= -0.0001).sum())
        cl = np.mean([R[e]['arms'][arm]['input_trk']['trk'] - R[e]['arms'][arm]['input_trk']['lib'] for e in EPS])
        cs = np.mean([R[e]['arms'][arm]['input_trk']['trk'] - R[e]['arms'][arm]['input_trk']['star'] for e in EPS])
        ds18 = np.mean([R[e]['arms'][arm][v]['d']['star'] for e in NO_OUT])
        print(f'| {v} {lab} | {arm} | {m:+.4f} | {b} / {worse} / {20 - b - worse} | {w:+.4f} (ep{we}) | '
              f'{"PASS" if ok else "fail"} | {np.mean(ds):+.4f} | {ds18:+.4f} | {m / cl:+.0%} of {cl:.4f} / '
              f'{np.mean(ds) / cs:+.0%} of {cs:.4f} | {ds18 / 0.0246:+.0%} |')
    verdict[v] = all(oks)
print()
for v in VARS:
    print(f'- {v}: {"PASS on both arms" if verdict[v] else "NOT adopted (fails on at least one arm)"}')
print()

print('### Per episode, dR = R(S11,S2) - R(S2) (lib / *) [M]\n')
print('| ep | objects | ' + ' | '.join(f'{arm} S2 lib / *' for arm in ARMS) + ' | '
      + ' | '.join(f'{arm} {v}' for arm in ARMS for v in VARS) + ' |')
print('|---|---|' + '---|' * (len(ARMS) + len(ARMS) * len(VARS)))
for e in EPS:
    r = R[e]
    row = [e, ' + '.join(r['names'])]
    for arm in ARMS:
        row.append(f'{r["arms"][arm]["S2"]["lib"]["AUC"]:.4f} / {r["arms"][arm]["S2"]["star"]["AUC"]:.4f}')
    for arm in ARMS:
        for v in VARS:
            d = r['arms'][arm][v]['d']
            row.append(f'{d["lib"]:+.4f} / {d["star"]:+.4f}')
    print('| ' + ' | '.join(row) + ' |')
print()

print('Geometric share vs the oracle constant offset: geo_share.py (cups measured on their axis points).\n')
ident = all(R[e]['arms'][a]['S2_identical_to_T1'] for e in EPS for a in ARMS)
print(f'S2 baseline byte-identical to T1 S2 outputs on all 20 episodes x 2 arms: {ident}')
