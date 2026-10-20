"""Verifier: pooled cam-a rolling-shutter model from the independent band rotations (pan/tilt components only, rig R
fixed from the whole fit, slip clips restricted to constant-pairing segments)."""
import glob, json, numpy as np
from v_sync import *
SEG = {'p22': (60, 187), 'e20': (50, 200)}
def vec_xy(wx, wy, R, ks, rng=3.0):
    cs = CubicSpline(np.arange(len(wy)), wy, axis=0); best = (np.inf, 0)
    for s in np.arange(-rng, rng + 1e-9, 0.01):
        kk = ks[(ks + s >= 0) & (ks + s <= len(wy) - 1)]; Y = cs(kk + s) @ R.T
        cost = ((wx[kk, :2] - Y[:, :2]) ** 2).sum() / (wx[kk, :2] ** 2).sum()
        if cost < best[0]: best = (cost, s)
    return best[1]
X, Yv, keys, per = [], [], [], {}
for f in sorted(glob.glob(f'{OD}/*.npz')):
    key = f.split('/')[-1][:-4]; z = np.load(f); Wa, Ya, Wb = fill(z['Wa'][:, 0]), z['Ya'], fill(z['Wb'])
    ks = np.arange(len(Wb)) if key not in SEG else np.arange(*SEG[key])
    _, _, R = vec_offset(Wa, Wb, ks=None if key not in SEG else ks)
    offs = []; ys = []
    for i in (1, 2, 3):
        o = vec_xy(fill(z['Wa'][:, i]), Wb, R, ks) * 50; y = np.nanmean(Ya[ks, i]); offs.append(o); ys.append(y)
    n = int(round(-(np.mean(offs) + 10) / 50))     # integer pairing removed: a[k+n] ~ b[k]
    o2 = np.array(offs) + 50 * n; X += ys; Yv += list(o2); keys.append(key)
    sl = np.polyfit(ys, o2, 1); per[key] = dict(n=n, offs=offs, ys=ys, slope=sl[0], icpt=sl[1])
    print(f'{key:4s} n={n} bands ' + ' '.join(f'{o:+6.1f}@{y:.2f}' for o, y in zip(offs, ys)) + f' | slope {sl[0]:+5.1f} icpt {sl[1]:+5.1f}')
A = np.polyfit(X, Yv, 1); res = np.array(Yv) - np.polyval(A, X)
sl = np.array([per[k]['slope'] for k in keys]); ic = np.array([per[k]['icpt'] for k in keys])
print(f'POOLED (n={len(keys)} clips): t(a[k+n], y) - t(b[k]) = {A[1]:+.1f} + {A[0]:.1f} y ms; resid sd {res.std():.2f} ms; per-clip slope {sl.mean():.1f} +- {sl.std():.1f}, icpt {ic.mean():+.1f} +- {ic.std():.1f}')
json.dump(per, open(f'{OD}/../v_rs2.json', 'w'), default=float, indent=0)
