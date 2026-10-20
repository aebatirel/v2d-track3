"""Spin axis per object: revolution-axis fit vs GT rest up vector; extents along axis."""
import numpy as np, json
from meshlib import *; from axis import *
up = json.load(open('out/upaxis.json'))
def gt_up(n):
    U = np.array([r['up0'] for r in up[n]]); U = U * np.sign(U @ U[0])[:, None]; m = U.mean(0); return m / np.linalg.norm(m)
res = {}
for n in ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']:
    g, tex = load(n); P, C, N = sample(g, tex, 400000, seed=5)
    u = gt_up(n)
    ext = np.ptp(P, 0)
    if n == 'white_pot_lid':
        y, z = P[:, 1], P[:, 2]; rr = np.hypot(y, z); m = rr > np.percentile(rr, 90)
        cx, cy, r = circle_fit(y[m], z[m]); p, a = np.array([0, cx, cy]), np.array([1., 0, 0])
    elif n == 'white_pot':
        m = np.abs(P[:, 2]) < 0.09; p, a, _ = fit_axis(P[m], np.array([1., 0, 0]), p0=np.zeros(3))
    elif n == 'water_pitcher':
        # body: points within the 60 % radius percentile about the GT-up line through the centroid
        Q = P - P.mean(0); h = Q @ u; rr = np.linalg.norm(Q - np.outer(h, u), axis=1)
        m = rr < np.percentile(rr, 60)
        p, a, _ = fit_axis(P[m], u, p0=P[m].mean(0))
    else:
        p, a, _ = fit_axis(P, np.array([0, 0, 1.]), p0=np.zeros(3))
    if a @ u < 0: a = -a
    # base normal: faces whose normal is close to -up at the lowest height
    h = (P - p) @ a; lowm = (h < np.percentile(h, 3)) & ((N @ -a) > 0.9)
    bn = -N[lowm].mean(0); bn /= np.linalg.norm(bn) + 1e-12
    ang = lambda x, y: np.degrees(np.arccos(np.clip(abs(x @ y), 0, 1)))
    print(f'{n:14s} ext mm {np.round(ext*1000,0)}  fit axis {np.round(a,3)} p mm {np.round(p*1000,1)}  GT up {np.round(u,3)}  '
          f'angle(fit, GTup) {ang(a,u):.1f} deg  angle(base normal, GTup) {ang(bn,u):.1f} (n={lowm.sum()})')
    res[n] = dict(p=p.tolist(), a=a.tolist(), gt_up=u.tolist(), ang_fit_up=ang(a, u))
json.dump(res, open('out/axes2.json', 'w'), indent=1)
