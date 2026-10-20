"""Marker constellation spin-symmetry: full-set self-match vs spin, and per-viewpoint visible-subset ambiguity."""
import numpy as np, json
from scipy.optimize import linear_sum_assignment
from selfsim import good_markers
from meshlib import rot
AX = json.load(open('out/axes2.json'))
def cyl(M, p, a):
    from axis import frame_from_axis
    e1, e2, a = frame_from_axis(a); Q = M - p
    return np.degrees(np.arctan2(Q @ e2, Q @ e1)), Q @ a, np.hypot(Q @ e1, Q @ e2)
def match(X, Y):
    if len(X) != len(Y): return np.inf
    if len(X) == 0: return 0.0
    D = np.linalg.norm(X[:, None] - Y[None], axis=2); i, j = linear_sum_assignment(D); return D[i, j].mean()
out = {}
for n in ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']:
    p, a = np.array(AX[n]['p']), np.array(AX[n]['a']); M = good_markers(n)
    th, h, r = cyl(M, p, a); o = np.argsort(th)
    print(f'{n}: {len(M)} markers; (theta deg, height mm, radius mm):', ' '.join(f'({t:.0f},{hh*1000:.0f},{rr*1000:.0f})' for t, hh, rr in zip(th[o], h[o], r[o])))
    # outward direction of each marker: radial for side markers, axial for top markers
    radial = (M - p) - np.outer((M - p) @ a, a); rn = np.linalg.norm(radial, axis=1)
    nrm = np.where((rn > 0.03)[:, None] & (n != "white_pot_lid"), radial / rn[:, None], a[None] * (np.ones(len(M)) if n == "white_pot_lid" else np.sign((M - p) @ a))[:, None])
    phis = np.arange(0, 360, 1.0)
    full = np.array([match(M, (M - p) @ rot(a, np.radians(f)).T + p) for f in phis])
    far = np.abs((phis + 180) % 360 - 180) > 15
    j = np.argmin(np.where(far, full, np.inf))
    print(f'   full-set: best non-identity spin {phis[j]:.0f} deg mean marker mismatch {full[j]*1000:.1f} mm')
    # visible-subset ambiguity from an ego-like camera (elevation el, distance 0.5 m), azimuth sweep
    from axis import frame_from_axis
    e1, e2, _ = frame_from_axis(a); ctr = p + a * np.median((M - p) @ a)
    rows = []
    for el in (30, 55, 80):
        amb, margins, nvis = [], [], []
        for az in np.arange(0, 360, 5):
            cam = ctr + 0.5 * (np.cos(np.radians(el)) * (np.cos(np.radians(az)) * e1 + np.sin(np.radians(az)) * e2) + np.sin(np.radians(el)) * a)
            def vis(X, N):
                v = cam - X; v /= np.linalg.norm(v, axis=1, keepdims=True); return (v * N).sum(1) > np.cos(np.radians(75))
            V0 = M[vis(M, nrm)]; nvis.append(len(V0))
            best = np.inf
            for f in phis[far]:
                Rf = rot(a, np.radians(f)); Mf = (M - p) @ Rf.T + p; Nf = nrm @ Rf.T
                best = min(best, match(V0, Mf[vis(Mf, Nf)]))
            margins.append(best)
        margins = np.array(margins); nvis = np.array(nvis)
        rows.append(dict(el=el, nvis_min=int(nvis.min()), nvis_mean=float(nvis.mean()), frac_amb_6mm=float((margins < 0.006).mean()),
                         frac_amb_12mm=float((margins < 0.012).mean()), frac_none_visible=float((nvis == 0).mean()), margin_med_mm=float(np.median(np.where(np.isfinite(margins), margins, 1)) * 1000)))
        print(f"   view el {el:2d}: visible markers min {nvis.min()} mean {nvis.mean():.1f}; azimuths with 0 visible {np.mean(nvis==0):.2f}; "
              f"ambiguous (another spin >15 deg explains the visible set within 6 / 12 mm): {np.mean(margins<0.006):.2f} / {np.mean(margins<0.012):.2f}")
    out[n] = dict(theta=th.tolist(), h=h.tolist(), r=r.tolist(), full_best_spin=float(phis[j]), full_best_mm=float(full[j] * 1000), views=rows)
json.dump(out, open('out/markers2.json', 'w'), indent=1)
