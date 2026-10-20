# Round-2 verifier: statistics from y_ud_*.out (EDT union depth) vs floors (own y_floors.out and stage-B floors).
import re, os, numpy as np
D = '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/'; B = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/logs/'
rx = re.compile(r'^(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: A-in-B bnd\s+([\d.]+) all\s+([\d.]+) ph\s+([\d.]+) \| B-in-A bnd\s+([\d.]+) all\s+([\d.]+)')
V = {}; order = []; typ = {}
S = {'white_pot_lid': 'lid', 'white_pot': 'pot', 'plastic_dish_rack': 'rack', 'mini_sweeper': 'sweeper', 'blue_cup': 'blue', 'beige_cup': 'beige'}
for L in ['REC', 'V1', 'V0', 'V2', 'S60r120']:
    p = D + f'y_ud_{L}.out'
    if not os.path.exists(p): continue
    for l in open(p):
        m = rx.match(l)
        if m:
            k = (m[2], m[3]); V[(L, k)] = {'bnd': (float(m[6]), float(m[9])), 'all': (float(m[7]), float(m[10]))}
            typ[k] = (S[m[4]], S[m[5]]); order.append(k) if k not in order else None
F1 = {}; F0 = {}
for l in open(D + 'y_floors.out'):
    m = re.match(r'^FLOOR2 ep(\d+)\s+f(\d+).*A-in-B\s+([\d.]+) \| B-in-A\s+([\d.]+)', l); F1[(m[1], m[2])] = (float(m[3]), float(m[4]))
for fn in [B + 'eval_floors.out', B + 'eval2_floors.out']:
    for l in open(fn):
        m = re.match(r'^W2floor\s+ep(\d+)\s+f(\d+).*W2A-in-W2B max\s+([\d.]+).*W2B-in-W2A max\s+([\d.]+)', l)
        if m: F0[(m[1], m[2])] = (float(m[3]), float(m[4]))
labs = [L for L in ['V0', 'V2', 'V1', 'REC', 'S60r120'] if any((L, k) in V for k in order)]
for met in ['bnd', 'all']:
    for fl, F in (('ownfloor', F1), ('stageBfloor', F0)):
        print(f'== metric {met}, {fl}')
        for L in labs:
            ks = [k for k in order if (L, k) in V]
            for di, nm in ((0, 'A-in-B'), (1, 'B-in-A')):
                e = np.array([V[(L, k)][met][di] - F[k][di] for k in ks])
                print(f'  {L:8s} {nm}: n {len(e):2d} median {np.median(e):+.2f} max {e.max():+.2f} min {e.min():+.2f} n>1mm {(e > 1).sum()}')
# cause separation on identical geometry: prep = V2 - V1, concavity = V1 - floor (own floor, bnd metric)
if all(any((L, k) in V for k in order) for L in ('V1', 'V2', 'V0')):
    ks = [k for k in order if ('V1', k) in V and ('V2', k) in V and ('V0', k) in V]
    for met in ['bnd', 'all']:
        print(f'== cause separation, metric {met}, own floor (n {len(ks)})')
        for di, nm in ((0, 'A-in-B'), (1, 'B-in-A')):
            pr = np.array([V[('V2', k)][met][di] - V[('V1', k)][met][di] for k in ks]); co = np.array([V[('V1', k)][met][di] - F1[k][di] for k in ks])
            g = np.array([V[('V0', k)][met][di] - V[('V1', k)][met][di] for k in ks])
            print(f'  {nm}: prep(V2-V1) median {np.median(pr):+.2f} range {pr.min():+.1f}..{pr.max():+.1f} | concavity(V1-floor) median {np.median(co):+.2f} range {co.min():+.1f}..{co.max():+.1f} | '
                  f'V0-V1 median {np.median(g):+.2f} | rows conc>1.5x prep {(co > 1.5 * pr).sum()}, prep>1.5x conc {(pr > 1.5 * co).sum()}')
            for t in sorted(set(typ[k] for k in ks)):
                kk = [i for i, k in enumerate(ks) if typ[k] == t]
                a, b = (t if di == 0 else t[::-1])
                print(f'     {a:7s} in {b:7s}: prep {pr[kk].min():+.1f}..{pr[kk].max():+.1f} conc {co[kk].min():+.1f}..{co[kk].max():+.1f}')
