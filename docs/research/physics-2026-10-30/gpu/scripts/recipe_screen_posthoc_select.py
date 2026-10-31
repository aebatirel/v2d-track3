"""Post-hoc (NOT pre-registered) check on public episodes: does GT-free sim_vs_ref (10 draws, vs our reference) pick
the arm with the higher registered AUC? Reads merged recipe-screen cells + optional extra summaries."""
import json, sys, itertools
cells = json.load(open(sys.argv[1]))['cells']
for extra in sys.argv[2:]:
    for k, v in json.load(open(extra))['cells'].items():
        if v.get('auc') and (k not in cells or not cells[k].get('auc')): cells[k] = v
ok = lambda c: c and c.get('auc') and c['auc'].get('n', 0) >= 8
E, A, SEEDS = [2, 12, 18, 24], 'CKDS', [42, 43]
print('per (episode, seed): AUC / svr per arm')
for e in E:
    for s in SEEDS:
        row = []
        for a in A:
            c = cells.get(f'{a}/ep{e}-s{s}')
            row.append(f"{a} {c['auc']['mean']:.3f}/{c['sim_vs_ref']['mean']:.3f}" if ok(c) else f"{a} --")
        print(f'ep{e:<2} s{s}  ' + '   '.join(row))
print('\npairwise: does higher svr pick higher AUC? (per episode x seed, both cells present)')
for a, b in itertools.combinations(A, 2):
    agree = n = 0; miss = []
    for e in E:
        for s in SEEDS:
            ca, cb = cells.get(f'{a}/ep{e}-s{s}'), cells.get(f'{b}/ep{e}-s{s}')
            if not (ok(ca) and ok(cb)): continue
            n += 1; g = (ca['sim_vs_ref']['mean'] - cb['sim_vs_ref']['mean']) * (ca['auc']['mean'] - cb['auc']['mean']) > 0
            agree += g
            if not g: miss.append(f"ep{e}s{s} dAUC {ca['auc']['mean']-cb['auc']['mean']:+.3f}")
    print(f'{a} vs {b}: {agree}/{n}  misses: {miss}')
print('\nselector "per episode x seed, max svr over arms" vs C alone (AUC)')
for arms in ['CD', 'CS', 'CDS', 'CKDS']:
    gains = []
    for e in E:
        for s in SEEDS:
            cs = [cells.get(f'{a}/ep{e}-s{s}') for a in arms]
            if not all(ok(c) for c in cs): continue
            pick = max(cs, key=lambda c: c['sim_vs_ref']['mean'])
            gains.append((e, s, pick['arm'], pick['auc']['mean'] - cs[0]['auc']['mean'], pick['auc']['sd'], cs[0]['auc']['sd']))
    m = sum(g[3] for g in gains) / max(len(gains), 1)
    print(f"{arms}: mean gain {m:+.4f} over {len(gains)} cells; " + ', '.join(f"ep{e}s{s}->{p} {g:+.3f} (sd {sp:.3f} vs {sc:.3f})" for e, s, p, g, sp, sc in gains))
