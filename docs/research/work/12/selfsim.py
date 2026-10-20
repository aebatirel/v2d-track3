"""Rotational self-similarity about the symmetry/up axis, geometry and texture colour, with and without marker regions."""
import numpy as np, json, sys
from scipy.spatial import cKDTree
from meshlib import *; from axis import *

M = json.load(open('out/markers_raw.json'))
def good_markers(name):
    out = []
    for q in M[name]:
        if 6.5e-3 < q['radius'] < 8.6e-3 and q['bright'] > 0.55: out.append(q['centre'])
        elif name == 'white_pot_lid' or (name == 'white_pot' and q['bright'] > 0.3): out.append(q['mount'])
    # dedupe within 15 mm
    U = []
    for c in out:
        if all(np.linalg.norm(np.subtract(c, u)) > 0.015 for u in U): U.append(c)
    return np.array(U)

def axis_for(name, P):
    if name in ('blue_cup', 'beige_cup'):
        p, a, _ = fit_axis(P, np.array([0, 0, 1.]), p0=np.zeros(3)); return p, a
    if name == 'white_pot_lid':
        y, z = P[:, 1], P[:, 2]; rr = np.hypot(y, z); m = rr > np.percentile(rr, 90)
        cx, cy, r = circle_fit(y[m], z[m]); return np.array([0, cx, cy]), np.array([1., 0, 0])
    if name == 'white_pot':
        # body: exclude handle (long +z/-z arm): keep points within 110 mm of x-axis line through origin in yz
        m = np.abs(P[:, 2]) < 0.09
        p, a, _ = fit_axis(P[m], np.array([1., 0, 0]), p0=np.zeros(3)); return p, a
    if name == 'water_pitcher':
        return np.zeros(3), np.array([0, 0, 1.])

def curves(name, angles, nA=120000, nB=500000, excl=0.016):
    g, tex = load(name)
    PA, CA, _ = sample(g, tex, nA, seed=3); PB, CB, _ = sample(g, tex, nB, seed=4)
    p, a = axis_for(name, PB)
    mk = good_markers(name)
    def strip(P, C):
        if len(mk) == 0: return P, C
        d = cKDTree(mk).query(P)[0]; k = d > excl; return P[k], C[k]
    out = {}
    for tag, (A, CAa, B, CBb) in {'all': (PA, CA, PB, CB), 'nomk': (*strip(PA, CA), *strip(PB, CB))}.items():
        T = cKDTree(B)
        geo, col = [], []
        for ang in angles:
            R = rot(a, np.radians(ang))
            A2 = (A - p) @ R.T + p
            d, i = T.query(A2, distance_upper_bound=0.01)
            ok = np.isfinite(d)
            geo.append(np.where(ok, d, 0.01).mean())
            near = d < 0.0015
            col.append(np.abs(CAa[near] - CBb[i[near]]).sum(1).mean() / 3 if near.sum() > 100 else np.nan)
        out[tag] = dict(geo=np.array(geo), col=np.array(col))
    return out, p, a, mk

def summarise(angles, y):
    angles = np.asarray(angles); y = np.asarray(y)
    f = y[angles == 0][0]
    far = np.abs(((angles + 180) % 360) - 180) > 10
    j = np.nanargmin(np.where(far, y, np.inf))
    med = np.nanmedian(y)
    return dict(floor=float(f), second=float(y[j]), second_at=float(angles[j]), median=float(med),
                contrast=float((y[j] - f) / max(med - f, 1e-9)))

if __name__ == '__main__':
    names = sys.argv[1:] or ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']
    angles = np.r_[np.arange(0, 360, 2.0)]
    res = {}
    for n in names:
        out, p, a, mk = curves(n, angles)
        res[n] = dict(axis_p=p.tolist(), axis_a=a.tolist(), n_markers=len(mk), markers=mk.tolist())
        for tag in out:
            for kind in ('geo', 'col'):
                s = summarise(angles, out[tag][kind]); res[n][f'{tag}_{kind}'] = s
                res[n][f'{tag}_{kind}_curve'] = out[tag][kind].tolist()
                print(f"{n:14s} {tag:4s} {kind}: floor {s['floor']*1000 if kind=='geo' else s['floor']:.4f} second {s['second']*1000 if kind=='geo' else s['second']:.4f} @ {s['second_at']:.0f} deg  median {s['median']*1000 if kind=='geo' else s['median']:.4f}  contrast {s['contrast']:.2f}", flush=True)
        json.dump(res, open(f'out/selfsim_{"_".join(names) if len(names)<5 else "all"}.json', 'w'))
