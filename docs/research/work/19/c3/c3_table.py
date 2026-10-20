# Stage C3: union depth on MuJoCo-capped sets (c3/logs/ud_cap_*.out) vs the uncapped round-2 runs (r2/y_ud_*.out)
# and the round-2 own floors (r2/y_floors.out); 'bnd' metric (A's union boundary), as Y15/Y16.
import re, os, numpy as np
R2 = '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/'; C = '/Users/aebatirel/Documents/Code/v2d-research/work/19/c3/logs/'
rx = re.compile(r'^(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: A-in-B bnd\s+([\d.]+) all\s+([\d.]+) ph\s+([\d.]+) \| B-in-A bnd\s+([\d.]+)')
S = {'white_pot_lid': 'lid', 'white_pot': 'pot', 'plastic_dish_rack': 'rack', 'mini_sweeper': 'sweeper', 'blue_cup': 'blue', 'beige_cup': 'beige'}
V = {}; typ = {}; order = []
def read(path, L):
    if not os.path.exists(path): return
    for l in open(path):
        m = rx.match(l)
        if m:
            k = (int(m[2]), int(m[3])); V[(L, k)] = (float(m[6]), float(m[9])); typ[k] = (S[m[4]], S[m[5]])
            if k not in order: order.append(k)
for L in ['V0', 'V1', 'REC', 'S60r120']:
    read(R2 + f'y_ud_{L}.out', L); read(C + f'ud_cap_{L}.out', L + 'cap')
F = {}
for l in open(R2 + 'y_floors.out'):
    m = re.match(r'^FLOOR2 ep(\d+)\s+f(\d+).*A-in-B\s+([\d.]+) \| B-in-A\s+([\d.]+)', l); F[(int(m[1]), int(m[2]))] = (float(m[3]), float(m[4]))
print('== excess over own floor (bnd), and capped - uncapped (same rows)')
for L in ['V0', 'V1', 'REC', 'S60r120']:
    for X in (L, L + 'cap'):
        ks = [k for k in order if (X, k) in V]
        if not ks: continue
        for di, nm in ((0, 'A-in-B'), (1, 'B-in-A')):
            e = np.array([V[(X, k)][di] - F[k][di] for k in ks]); s = f'  {X:10s} {nm}: n {len(e):2d} median {np.median(e):+.2f} max {e.max():+.2f} min {e.min():+.2f} n>1mm {(e > 1).sum():2d}'
            if X.endswith('cap'):
                dd = np.array([V[(X, k)][di] - V[(L, k)][di] for k in ks]); s += f' | cap-uncap median {np.median(dd):+.2f} range {dd.min():+.2f}..{dd.max():+.2f}'
            print(s)
print('== per contact type, absolute depth ranges mm: floor / V0cap / V1cap / RECcap / S60r120cap  (uncapped REC in brackets)')
for t in sorted(set(typ.values())):
    ks = [k for k in order if typ[k] == t]
    for di in (0, 1):
        a, b = t if di == 0 else t[::-1]
        def rg(X):
            v = [V[(X, k)][di] for k in ks if (X, k) in V]
            return f'{min(v):.1f}-{max(v):.1f}' if v else '  n/a  '
        fl = [F[k][di] for k in ks]
        print(f'  {a:7s} in {b:7s} (n {len(ks)}): floor {min(fl):.1f}-{max(fl):.1f} | V0cap {rg("V0cap")} | V1cap {rg("V1cap")} | RECcap {rg("RECcap")} | S60r120cap {rg("S60r120cap")}  [REC {rg("REC")}, V0 {rg("V0")}, V1 {rg("V1")}]')
