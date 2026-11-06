"""D2 x1 diagnostic of the topology failure (never delivered): rebuild the D2 carve (physics off), then the carved
host's thinnest wall (per sector piece: outer chord minus new inner face at the piece's knots) and topology on 2 mm and
1 mm grids (interlock.topology), default vs carved."""
import os, sys, json, math, time
os.environ.setdefault('GMG_MODE', 'dev')
R = '/home/user/v2d-track3/docs/research/mesh-2026-10-26'
sys.path.insert(0, R); sys.path.insert(0, R + '/gmg/tests')
import numpy as np
import test_collcarve as T
from gmg import cavpieces as CP, interlock as IL
T.COPIES = 16
b, M = T.cups_case()
objects, ctx, W, rep = T.run(b, M, 'd2_x1_topo', lathe=dict(A=T.AXIS, B=T.AXIS), hands=b.hands, physics=False,
                             diag_rest=True)
carved = W['_carved']
out = dict(caps=W['caps'])
for pitch in (0.002, 0.001):
    Hd, Hc = CP.Hulls(objects['A']['hulls']), CP.Hulls(carved)
    lo = np.minimum(Hd.bounds()[0], Hc.bounds()[0]) - 2 * pitch
    hi = np.maximum(Hd.bounds()[1], Hc.bounds()[1]) + 2 * pitch
    G, n = CP.grid_points(lo, hi, pitch)
    out[f'topo_{pitch*1e3:.0f}mm'] = dict(default=list(IL.topology(Hd.inside(G).reshape(n))),
                                          carved=list(IL.topology(Hc.inside(G).reshape(n))))
# thinnest wall along radial rays (mid-sector and sector edges) every 1 mm in height, 1 deg in azimuth
L = objects['A']['lathe'][0]
Hc = CP.Hulls(carved)
rows = []
for h in np.arange(0.008, 0.095, 0.001):
    for phi in np.radians(np.arange(0, 360, 1.0)):
        r = np.arange(0.025, 0.042, 0.0001)
        X = L.pt(np.full(len(r), h), r, np.full(len(r), phi))
        ins = Hc.inside(X)
        if not ins.any():
            rows.append((h, phi, 0.0)); continue
        # longest run of inside samples along the ray = wall thickness at this ray
        best = cur = 0
        for v in ins:
            cur = cur + 1 if v else 0; best = max(best, cur)
        rows.append((h, phi, best * 1e-4))
th = np.array([x[2] for x in rows])
out['wall_mm'] = dict(min=round(float(th.min()) * 1e3, 2), p1=round(float(np.percentile(th, 1)) * 1e3, 2),
                      median=round(float(np.median(th)) * 1e3, 2), rays=len(th), rays_lt_0p5mm=int((th < 0.0005).sum()),
                      rays_zero=int((th == 0).sum()))
z = [x for x in rows if x[2] == th.min()][:5]
out['thinnest'] = [dict(h_mm=round(x[0] * 1e3, 1), phi_deg=round(math.degrees(x[1]), 1), mm=round(x[2] * 1e3, 2)) for x in z]
print(json.dumps(out, default=IL._jdefault))
