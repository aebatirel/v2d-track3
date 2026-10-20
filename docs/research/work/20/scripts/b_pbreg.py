# Pooled sensitivity of the mid-axis skew toward M2 (toM2) to the measured layout parameters (hl_* marker layouts).
import json, glob, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
X, y, pb = [], [], []
for f in glob.glob(f'{OUT}/pb_hl_bend*.jsonl'):
    for l in open(f):
        r = json.loads(l); p = r['p']; b = r['body']; x = list(r['res'].values())[0]
        X.append([1, p['w1'] - p['w2'], p.get('bend', 0), p['phi'], p['y3'], p['h1'], p['h2'], p['h3'], b['Db'] * 1e3, b['handle_off_x'] * 1e3,
                  b['th'] / (2 * b['we']), b['wb'] * 1e3, (p['z2'] - p['z1']) * 1e3]); y.append(x['toM2']); pb.append(x['PB_noisy_mid'])
X, y = np.array(X), np.array(y); names = ['const', 'asym(mm)', 'bend(mm)', 'roll(deg)', 'y3 M3 lat(mm)', 'h1', 'h2', 'h3', 'Db(mm)', 'handle_off_x(mm)', 'th/2we', 'wb(mm)', 'dz12(mm)']
Xs = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1); Xs[:, 0] = 1
cf = np.linalg.lstsq(X, y, rcond=None)[0]; cfs = np.linalg.lstsq(Xs, y, rcond=None)[0]; r = y - X @ cf
print(f'n {len(y)}  R2 {1 - r.var() / y.var():.3f}  resid sd {r.std():.4f}')
for n_, c, cs in zip(names, cf, cfs): print(f'  {n_:18s} coef {c:+.5f}   per-1sd {cs:+.4f}')
