"""Does a standard-learner run's early score predict its final score? (2026-10-26, for the owner's question: train many
seeds and keep the ones that show early signs). GT-free: every number is sim_vs_ref (simulation vs OUR reference).

Inputs: docs/research/work/checkpoint-sweeps-2026-10-22.json (public-twin checkpoint sweeps, one official rollout per
checkpoint; rows [run, ref, ep-seed, step (None = final 250M), sim_vs_ref, floor]) plus today's eval-25 carve seeds
(runs 20261026-c25s42-feb0407 / -c25s43-, hard_ab_ep25s-s<seed>.log sweep lines; the final is the sweep's own
one-rollout score of the 250M checkpoint).
Usage: python early_predict.py"""
import collections, json, os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(f'{HERE}/../work/checkpoint-sweeps-2026-10-22.json'))
g = collections.defaultdict(dict)
for run, ref, es, step, s, fl in d:
    if s is not None:
        g[(run, ref, es)][250 if step is None else round(step / 1e6)] = s
cur = {}
for k, c in g.items():                                   # the same curve can appear under several runs: keep one
    if all(x in c for x in (100, 150, 250)):
        cur[(k[1], k[2], round(c[100], 4), round(c[250], 4))] = (k[2].split('-')[0], c)
C = list(cur.values())
C += [('ev25', {100: 0.4953, 150: 0.3582, 200: 0.422, 250: 0.8861}),     # c25s42 (5-eval mean of the final 0.792)
      ('ev25', {100: 0.4417, 150: 0.4963, 200: 0.471, 250: 0.4963})]     # c25s43 (chosen 150M, 5-eval mean 0.474)
y = np.array([c[250] for _, c in C]); l40 = np.array([c[100] for _, c in C]); l60 = np.array([c[150] for _, c in C])


def r2(X):
    X = np.c_[np.ones(len(y)), X]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    return round(float(1 - e.var() / y.var()), 3)


def rank(x):
    return np.argsort(np.argsort(x))


out = dict(n_curves=len(C), episodes=dict(collections.Counter(e for e, _ in C)),
           pearson_40_final=round(float(np.corrcoef(l40, y)[0, 1]), 3),
           spearman_40_final=round(float(np.corrcoef(rank(l40), rank(y))[0, 1]), 3),
           r2_level40=r2(l40), r2_slope40to60=r2(l60 - l40), r2_level40_plus_slope=r2(np.c_[l40, l60 - l40]),
           r2_level60=r2(l60))
by = collections.defaultdict(list)
for e, c in C:
    by[e].append(c)
for thr in (0.0, 0.05, 0.1):                             # same-episode pairs: does the 40 % leader finish ahead?
    ok = tot = 0
    for R in by.values():
        for i in range(len(R)):
            for j in range(i + 1, len(R)):
                if abs(R[i][100] - R[j][100]) > thr:
                    tot += 1; ok += (R[i][100] > R[j][100]) == (R[i][250] > R[j][250])
    out[f'leader_at_40_keeps_lead_gap_gt_{thr}'] = f'{ok}/{tot}'
out['late_jumps_gt_0.25'] = [(round(c[100], 2), round(c[250], 2), e) for e, c in C if c[250] - c[100] > 0.25]
print(json.dumps(out, indent=1))
