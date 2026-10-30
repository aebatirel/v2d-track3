"""Split the 20 public episodes over 3 Phase-1 boxes, balanced by frame count x arms (o, s, plus o2 on REPEAT).
Also prints the per-run perc2 time measured on the cached-depth refine-input runs (perc_log_inference.txt: last
'tracked' line, GT-free) for the cost table. Usage: python3 -I balance.py INPUTS.tsv REFINE_IN"""
import itertools, re, sys
tsv, rin = sys.argv[1], sys.argv[2]
REPEAT = {2, 11, 12, 13, 18, 21, 24, 27, 31, 39}               # the 10 Phase-2 twins (PLAN §3)
rows = [l.rstrip('\n').split('\t') for l in open(tsv)][1:]
T = {int(r[0]): int(r[1]) for r in rows}; NO = {int(r[0]): len(r[2].split(',')) for r in rows}
sec = {}
for e in T:
    ts = [float(m.group(1)) for m in re.finditer(r'\[\s*([\d.]+)s\] tracked', open(f'{rin}/ep{e}/perc_log_inference.txt').read())]
    sec[e] = max(ts)
arms = {e: 3 if e in REPEAT else 2 for e in T}
w = {e: arms[e] * T[e] for e in T}
best = None
eps = sorted(T)
for a in itertools.product(range(3), repeat=len(eps) - 1):     # ep0 fixed on box 0 (symmetry)
    g = (0,) + a
    s = [sum(w[e] for e, b in zip(eps, g) if b == k) for k in range(3)]
    if best is None or max(s) - min(s) < best[0] or (max(s) - min(s) == best[0] and max(s) < best[1]):
        best = (max(s) - min(s), max(s), g)
g = best[2]
print('perc2 seconds to the last tracked line (cached depth) per episode:', {e: sec[e] for e in eps})
for k in range(3):
    E = [e for e, b in zip(eps, g) if b == k]
    E.sort(key=lambda e: (e not in REPEAT, T[e]))              # twins first, smaller first (GPU starts sooner)
    print(f'box {"abc"[k]}: EPS="{" ".join(map(str, E))}" REPEAT="{" ".join(str(e) for e in E if e in REPEAT)}" '
          f'frames {sum(T[e] for e in E)} arm-frames {sum(w[e] for e in E)} runs {sum(arms[e] for e in E)} '
          f'perc2 run-s {sum(arms[e] * sec[e] for e in E):.0f} depth GB {sum(T[e] for e in E) * 6.4e6 / 1e9:.1f}')
print('total frames', sum(T.values()), 'arm-frames', sum(w.values()), 'runs', sum(arms.values()))
