"""Expected-gain ranking [E] for the masses eval retrain (2026-10-31, PLAN.md section 3). Deterministic, GT-free inputs:
packed sim_vs_ref (pack 7 summary.txt), official multi-draw stats vs our reference (H5; c33B for eval 33; e1conf2 for
eval 1's carve base), masses, and how far OUR reference moves each object (motion.json).
  lift(e)   = L * wD * wR * wT     (L = the transfer check's mean gain; 0.03 / 0.05 / 0.10 shown)
  wD        = 1 if the largest |ln(m / 0.3)| over objects our reference moves > 3 cm is >= 0.7, 0.5 if >= 0.3, else 0.1
  wR        = 1 grasp lock (the recipe Round 3 and the transfer check measure), 0.5 standard learner (unmeasured)
  wT        = 0.5 eval 20 (carried pitcher HEAVIER than 0.3 kg: direction unmeasured); 0.25 eval 10 (reference
              geometry-limited, oracle twin C2); 0.25 sweeper / dust pan evals 19, 30, 38 (public ep18 gained only +0.011)
  new mean  = min(level + lift, max(0.99, level));  board gain = max(0, new mean - packed draw)
Usage: python -I rank.py h5_summary.json pack7_summary.txt motion.json
"""
import json, math, sys
h5 = json.load(open(sys.argv[1])); packed = json.loads(open(sys.argv[2]).readline()); mot = json.load(open(sys.argv[3]))
STD = {1, 19, 25, 28, 30}; SPOON = {3, 5, 6, 15, 16, 32, 33, 35, 36, 37}; TR = 0.76   # LB per sim_vs_ref, measured 0.74-0.78
lvl = {int(e): (v['mean'], v['sd']) for e, v in h5.items()}
lvl[33] = (0.934, 0.008)            # pack-7 policy rcB, c33B: 10 official draws
lvl[1] = (0.9241, 0.017)            # retrain base = the c01s43 carve recipe (pack-8 candidate), e1conf2: 20 official draws
bar = {int(e): v for e, v in packed.items()}; bar8 = dict(bar); bar8[1] = 0.9232     # pack 8's eval-1 draw
WT = {20: 0.5, 10: 0.25, 19: 0.25, 30: 0.25, 38: 0.25}
OPTS = {'glock_only': [20, 8, 33, 15], 'topk_wave1': [1, 20, 8, 33, 15], 'recommended': [1, 20, 8, 33, 15, 5, 32, 6, 3],
        'spoon_wave2': [5, 32, 6, 3], 'full20': sorted(bar)}
rows = {}
for e in sorted(bar):
    moved = [o for o in mot[str(e)]['objects'].values() if o['max_disp_cm'] > 3]
    D = max(abs(math.log(o['mass_kg'] / 0.3)) for o in moved)
    w = (1.0 if D >= 0.7 else 0.5 if D >= 0.3 else 0.1) * (0.5 if e in STD else 1.0) * WT.get(e, 1.0)
    m, sd = lvl[e]; r = dict(D=D, w=w, m=m, sd=sd)
    for L in (0.0, 0.03, 0.05, 0.10):
        mu = min(m + L * w, max(0.99, m)); r[L] = max(0.0, mu - bar8[e]); r[('p7', L)] = max(0.0, mu - bar[e])
    rows[e] = r
print('eval stratum learner  D     w      level+-sd        bar(p8) need    | g(L=0) g(.03) g(.05) g(.10) | g(.05) vs pack-7 bar')
for e in sorted(rows, key=lambda e: (-rows[e][0.05], -rows[e][0.10])):
    r = rows[e]
    print(f"{e:>4} {'spoon' if e in SPOON else '-':7} {'std' if e in STD else 'glock':6} {r['D']:.2f} {r['w']:.3f}  {r['m']:.4f}+-{r['sd']:.4f}  "
          f"{bar8[e]:.4f} {bar8[e] - r['m']:+.4f} | {r[0.0]:.4f} {r[0.03]:.4f} {r[0.05]:.4f} {r[0.10]:.4f} | {r[('p7', 0.05)]:.4f}")
for k, eps in OPTS.items():
    print(f'{k:12} {eps}: ' + '  '.join(f'L={L}: sim {sum(rows[e][L] for e in eps):.3f} LB {sum(rows[e][L] for e in eps) * TR / 20:.4f}'
                                        for L in (0.0, 0.03, 0.05, 0.10)))
