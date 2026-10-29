#!/usr/bin/env python3
"""Does a low early score gain from more training steps? Reads docs/research/work/checkpoint-sweeps-2026-10-22.json
(rows: run, reference, ep-seed, step (None = final 250M), sim_vs_ref, zero-action floor). Copies of the same base run
are de-duplicated by their curve values. GT-free: sim_vs_ref only. Usage: python3 curve_gain.py [json]"""
import collections, json, statistics as st, sys
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'docs/research/work/checkpoint-sweeps-2026-10-22.json'))
g = collections.defaultdict(dict)
for run, ref, es, step, s, fl in d:
    if s is not None:
        g[(run, ref, es)][250 if step is None else round(step / 1e6)] = (s, fl)
curves = {}
for k, c in g.items():
    if all(x in c for x in (100, 150, 200, 250)):
        curves[(k[1], k[2], tuple(round(c[x][0], 4) for x in (100, 150, 200, 250)))] = c[100][1]
rows = [(k[0], k[1], k[2], fl) for k, fl in curves.items()]
print('unique curves', len(rows))
for name, R in (('score@100M < 0.5', [r for r in rows if r[2][0] < 0.5]), ('score@100M >= 0.5', [r for r in rows if r[2][0] >= 0.5])):
    print(name, 'n', len(R), '| median 100->250M %+.3f' % st.median(r[2][3] - r[2][0] for r in R),
          '| ends >= 0.45: %d/%d' % (sum(r[2][3] >= 0.45 for r in R), len(R)),
          '| ends below its zero-action floor: %d/%d' % (sum(r[2][3] < (r[3] or 0) for r in R), len(R)))
for name, R in (('rising 150->200M by > 0.03', [r for r in rows if r[2][2] - r[2][1] > 0.03]),
                ('flat or falling 150->200M', [r for r in rows if r[2][2] - r[2][1] <= 0.03])):
    print(name, 'n', len(R), '| median 200->250M %+.3f' % st.median(r[2][3] - r[2][2] for r in R),
          '| rises again %d/%d' % (sum(r[2][3] > r[2][2] for r in R), len(R)))
for r in sorted(rows, key=lambda r: r[2][0]):
    print('%-11s %-8s floor %.2f  ' % (r[0], r[1], r[3] or 0) + ' '.join('%.2f' % x for x in r[2]))
