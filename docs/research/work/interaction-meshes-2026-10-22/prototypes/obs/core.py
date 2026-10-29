# GT-free: how much of the coarse (12 mm) solid has no fine (4 mm / 6 mm) observation = thickness not measured.
import sys, json, numpy as np
for g in sys.argv[1:]:
    z = np.load(g); vx = float(z['voxel']); c = lambda M: round(float(M.sum()) * vx ** 3 * 1e6, 1)
    m12 = np.where(z['W12'] > 0, z['S12'] / np.maximum(z['W12'], 1), 1); in12 = (z['W12'] >= 3) & (m12 < 0)
    r = dict(inside12_cm3=c(in12))
    for t in (4, 6):
        W = z[f'W{t}']; m = np.where(W > 0, z[f'S{t}'] / np.maximum(W, 1), 1)
        r[f'core_unobs{t}_cm3'] = c(in12 & (W < 3)); r[f'pos{t}_in12_cm3'] = c(in12 & (W >= 3) & (m > 0)); r[f'inside{t}_cm3'] = c((W >= 3) & (m < 0))
    print(g.split('/')[-1], json.dumps(r))
