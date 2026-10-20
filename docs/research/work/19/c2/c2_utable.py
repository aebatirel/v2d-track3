# C21: union-depth table of the recommended recipe REC (rack S120, pot S120, blue CUP2, lid V1, beige V1, sweeper
# welded V1w) next to floor / V0 / V1 / S120 / S60r120 (inputs as b/b_utable2.py), plus REC - floor statistics.
import re, numpy as np
B = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
rx = re.compile(r'^(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: A-in-B per-hull\s+([\d.]+) union\s+([\d.]+) \| B-in-A per-hull\s+([\d.]+) union\s+([\d.]+)')
fx = re.compile(r'^W2floor\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: W2A-in-W2B max\s+([\d.]+).*W2B-in-W2A max\s+([\d.]+)')
S = {'white_pot_lid': 'lid', 'white_pot': 'pot', 'plastic_dish_rack': 'rack', 'mini_sweeper': 'sweeper', 'blue_cup': 'blue', 'beige_cup': 'beige'}
D = {}; F = {}; T = {}; order = []
for fn in [B + 'logs/uniondepth_V0V2.out', B + '../../19-verify/uniondepth_V1.out', B + '../../19-verify/uniondepth_S120.out',
           B + 'logs/uniondepth_S60r120.out', B + '../c2/logs/uniondepth_REC.out']:
    for l in open(fn):
        m = rx.match(l)
        if m:
            k = (m.group(2), m.group(3)); T[k] = (S[m.group(4)], S[m.group(5)]); D[(m.group(1), k)] = (float(m.group(7)), float(m.group(9)))
            if k not in order: order.append(k)
for fn in [B + 'logs/eval_floors.out', B + 'logs/eval2_floors.out']:
    for l in open(fn):
        m = fx.match(l)
        if m: F[(m.group(1), m.group(2))] = (float(m.group(5)), float(m.group(6)))
labs = ['floor', 'V0', 'V1', 'S120', 'S60r120', 'REC']
print('| contact (states) | ' + ' | '.join(labs) + ' | REC - floor |'); print('|---' * (len(labs) + 2) + '|')
groups = {}
for k in order: groups.setdefault(T[k], []).append(k)
ex = {0: [], 1: []}
for (a, b), ks in groups.items():
    for di, nm in ((0, f'{a} in {b}'), (1, f'{b} in {a}')):
        cells = []
        for L in labs:
            v = [F[k][di] if L == 'floor' else D[(L, k)][di] for k in ks]
            cells.append(f'{min(v):.1f}-{max(v):.1f}' if len(v) > 1 and min(v) != max(v) else f'{v[0]:.1f}')
        e = [D[('REC', k)][di] - F[k][di] for k in ks]; ex[di] += e
        cells.append(f'{min(e):+.1f}..{max(e):+.1f}')
        print(f'| {nm} ({len(ks)}) | ' + ' | '.join(cells) + ' |')
for di, nm in ((0, 'A-in-B'), (1, 'B-in-A')):
    e = np.array(ex[di]); print(f'REC - floor {nm}: median {np.median(e):+.2f}, range {e.min():+.1f}..{e.max():+.1f}, n>1mm {(e>1).sum()} of {len(e)}')
for L in ['V0', 'V1', 'S120', 'S60r120']:
    for di, nm in ((0, 'A-in-B'), (1, 'B-in-A')):
        e = np.array([D[(L, k)][di] - F[k][di] for k in order]); print(f'{L} - floor {nm}: median {np.median(e):+.2f}, max {e.max():+.1f}')
