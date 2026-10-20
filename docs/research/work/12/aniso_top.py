"""Top view (looking down the spin axis) of colour and spin-specific detail (x8) for up-facing surface."""
import numpy as np, json, sys
from meshlib import *; from axis import cyl
from symm3 import bandpass, ring_remove
AX = json.load(open('out/axes2.json'))
for n in sys.argv[1:]:
    g, tex = load(n); P, C, N = sample(g, tex, 1000000, seed=22)
    p, a = np.array(AX[n]['p']), np.array(AX[n]['a'])
    X = ring_remove(P, bandpass(P, C), p, a)
    th, h, r, (e1, e2, _) = cyl(P, p, a)
    up = (N @ a) > 0.3
    S = 300; R = r.max() * 1.02; px = 2 * R / S
    order = np.argsort(h)          # paint low first, high last (top-most visible)
    o = order[up[order]]
    x = ((r[o] * np.cos(th[o]) + R) / px).astype(int).clip(0, S - 1); y = ((R - r[o] * np.sin(th[o])) / px).astype(int).clip(0, S - 1)
    col = np.ones((S, S, 3)); det = np.full((S, S, 3), 0.5)
    col[y, x] = C[o]; det[y, x] = np.clip(0.5 + 8 * X[o], 0, 1)
    save(np.repeat(np.repeat(np.concatenate([col, np.ones((S, 6, 3)), det], 1), 2, 0), 2, 1), f'out/{n}_aniso_top.png')
    print(n, 'top view saved; px mm %.2f' % (px * 1000))
