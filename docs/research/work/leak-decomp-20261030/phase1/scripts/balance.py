"""Split the 20 public episodes over 3 Phase-1 boxes, balanced by frame count x arms (o, s, plus o2 on REPEAT).
2026-10-30, second version: the first (exhaustive 3^19 search) did not finish; this one is greedy (largest first) plus
single moves and pair swaps until the spread stops shrinking. Also prints, per box, the perc2 seconds measured on the
cached-depth refine-input runs (perc_log_inference.txt: last 'tracked' line, GT-free; library templates) and the depth
GB to download. Usage: python3 -I balance.py INPUTS.tsv REFINE_IN"""
import itertools, re, sys
tsv, rin = sys.argv[1], sys.argv[2]
REPEAT = {2, 11, 12, 13, 18, 21, 24, 27, 31, 39}                     # the 10 Phase-2 twins (PLAN §3)
rows = [l.rstrip('\n').split('\t') for l in open(tsv)][1:]
T = {int(r[0]): int(r[1]) for r in rows}; GB = {int(r[0]): int(r[4]) / 1e9 for r in rows}
sec = {e: max(float(m.group(1)) for m in re.finditer(r'\[\s*([\d.]+)s\] tracked', open(f'{rin}/ep{e}/perc_log_inference.txt').read()))
       for e in T}
arms = {e: 3 if e in REPEAT else 2 for e in T}; w = {e: arms[e] * T[e] for e in T}
box = [[], [], []]
for e in sorted(T, key=lambda e: -w[e]):                               # largest first, onto the lightest box
    min(box, key=lambda b: sum(w[x] for x in b)).append(e)
load = lambda: [sum(w[x] for x in b) for b in box]
better = True
while better:
    better = False; s0 = max(load()) - min(load())
    for i, j in itertools.permutations(range(3), 2):
        for e in list(box[i]):                                         # move one episode
            box[i].remove(e); box[j].append(e)
            if max(load()) - min(load()) < s0:
                better = True; break
            box[j].remove(e); box[i].append(e)
        if better:
            break
        for e, f in itertools.product(list(box[i]), list(box[j])):     # swap two episodes
            box[i].remove(e); box[j].remove(f); box[i].append(f); box[j].append(e)
            if max(load()) - min(load()) < s0:
                better = True; break
            box[i].remove(f); box[j].remove(e); box[i].append(e); box[j].append(f)
        if better:
            break
box.sort(key=lambda b: min(b))
print('perc2 seconds to the last tracked line (cached depth, library templates) per episode:', {e: sec[e] for e in sorted(T)})
for k, b in enumerate(box):
    b.sort(key=lambda e: (e not in REPEAT, T[e]))                     # twins first, short first (GPU starts sooner)
    print(f'box {"abc"[k]}: EPS="{" ".join(map(str, b))}" REPEAT="{" ".join(str(e) for e in b if e in REPEAT)}" '
          f'frames {sum(T[e] for e in b)} arm-frames {sum(w[e] for e in b)} runs {sum(arms[e] for e in b)} '
          f'perc2 run-s (library) {sum(arms[e] * sec[e] for e in b):.0f} depth GB {sum(GB[e] for e in b):.1f}')
print('total frames', sum(T.values()), 'arm-frames', sum(w.values()), 'runs', sum(arms.values()),
      f'perc2 run-s {sum(arms[e] * sec[e] for e in T):.0f}', f'depth GB {sum(GB.values()):.1f}')
