"""Cavity-safe lathe collision pieces (1 Nov 2026, ev10-cavsafe; design fixed in ../GATES.md before any number).

A copy of focused-pascal's pipeline/lathe_collision.py (branch claude/focused-pascal-2nz9s1, blob 680cc2f9; the tool
that built meshes/carve/ev10) with three opt-in changes. With none of them set, the wall and ring-base pieces are
the old tool's, vertex for vertex (checked: rebuild of meshes/carve/ev10, Hausdorff 0.0 mm).

  --inner_circ  (receiver; R1 + R2 of GATES.md) per band, the inner radius r_in = r - t at the profile bins is replaced
                by its least convex majorant f (LP: min sum(f - r_in), f >= r_in, f convex in h), and the inner points
                are placed at f / cos(pi / SEG) at the two sector edges. The inner face of every wall piece then lies
                at radius >= f >= r_in everywhere (the chord is tangent to f at mid-sector), so no piece enters the
                cavity { rho < r_in(h) } (r_in linear between bins). The outer points are unchanged.
  --outer_insc  (guest; G1) per band, the (shrunk) outer radius r at the bins is replaced by its greatest concave
                minorant f (LP: max sum(f), f <= r, f concave in h); the outer points stay at the sector edges, so the
                mid-sector chord is inside f <= r: no piece leaves the solid { rho <= r(h) }. Inner points unchanged
                (r - t).
  --outer_circ  (receiver; amendment A1 of GATES.md, 03:10 UTC, before any gate number) the outer points too are placed
                at r / cos(pi / SEG) at the sector edges, so the wall polygon circumscribes the lathe wall on both faces
                (the mirror of ev10, which inscribes both). Needed because with the outer points unchanged the
                mid-sector wall r cos(pi / SEG) - f is negative at 2 bins (mouth lip -1.30 mm, bottom corner -0.30 mm).
  --base_pieces DIR --base_first K  (receiver) instead of --base_from_hulls (which needs flash_chord's CoACD): copy
                DIR/piece_K.. byte for byte as the base (meshes/carve/ev10/blue_cup: piece_36..piece_52, FlashCHORD
                CoACD hulls of library_v3 clipped to the base side of the inner floor).

Why each constant: SEG, BAND, wall, shrink, base extension are ev10's (meshes/carve/ev10/carve.json). The LPs have no
constant. pi / SEG is the half-angle of a sector. Nothing is tuned on any overlap or contact number.
Usage: python lathe_cavsafe.py PROFILE.npz FIT.json OUT_DIR [lathe_collision.py options] [--inner_circ] [--outer_insc]
       [--base_pieces DIR --base_first K]
"""
import argparse, glob, json, os, shutil

import numpy as np
import trimesh
from scipy.optimize import linprog

ap = argparse.ArgumentParser(); ap.add_argument('profile'); ap.add_argument('fit'); ap.add_argument('out')
ap.add_argument('--seg', type=int, default=16); ap.add_argument('--band', type=float, default=0.03)
ap.add_argument('--shrink', type=float, default=0.0)
ap.add_argument('--solid', action='store_true'); ap.add_argument('--mass', type=float, default=0.3)
ap.add_argument('--wall', type=float, default=0.0)
ap.add_argument('--base_to_mesh'); ap.add_argument('--ext_max', type=float, default=1.0)
ap.add_argument('--inner_circ', action='store_true'); ap.add_argument('--outer_insc', action='store_true')
ap.add_argument('--outer_circ', action='store_true')
ap.add_argument('--base_pieces'); ap.add_argument('--base_first', type=int, default=0)
a = ap.parse_args()
z = np.load(a.profile); fit = json.load(open(a.fit))
c0, d, e1, e2 = (np.asarray(z[k], float) for k in ('c0', 'd', 'e1', 'e2'))
h = np.asarray(z['prof_h'], float); r = np.asarray(z['prof_r'], float) - a.shrink
o = np.argsort(h); h, r = h[o], r[o]
t = a.wall if a.wall > 0 else float(z['t']); hollow = bool(fit.get('hollow')) and not a.solid
base_hi = fit.get('base', 'hi') == 'hi'
ext = 0.0
if a.base_to_mesh:
    mv = (np.asarray(trimesh.load(a.base_to_mesh, force='mesh').vertices) - c0) @ d
    if base_hi and mv.max() > h.max():
        ext = min(mv.max() - h.max(), a.ext_max); h = np.r_[h, h.max() + ext]; r = np.r_[r, r[-1]]
    elif not base_hi and mv.min() < h.min():
        ext = min(h.min() - mv.min(), a.ext_max); h = np.r_[h.min() - ext, h]; r = np.r_[r[0], r]


def P(hh, rr, ang):
    return c0 + hh * d + rr * (np.cos(ang) * e1 + np.sin(ang) * e2)


def envelope(x, g, convex):
    """convex: least convex majorant of g at the bins x (min sum f, f >= g, f convex); else greatest concave minorant
    (max sum f, f <= g, f concave). Piecewise linear between bins, as the hull of points at those bins."""
    n = len(x)
    if n < 3:
        return g.copy()
    A = np.zeros((n - 2, n))
    for i in range(1, n - 1):
        dl, dr = x[i] - x[i - 1], x[i + 1] - x[i]
        A[i - 1, i - 1], A[i - 1, i], A[i - 1, i + 1] = 1 / dl, -(1 / dl + 1 / dr), 1 / dr   # slope difference
    if convex:            # slope difference >= 0  ->  -A f <= 0 ; f >= g
        res = linprog(np.ones(n), A_ub=-A, b_ub=np.zeros(n - 2), bounds=[(gi, None) for gi in g], method='highs')
    else:                 # slope difference <= 0  ->   A f <= 0 ; f <= g
        res = linprog(-np.ones(n), A_ub=A, b_ub=np.zeros(n - 2), bounds=[(None, gi) for gi in g], method='highs')
    assert res.success, res.message
    f = np.asarray(res.x, float)
    return np.maximum(f, g) if convex else np.minimum(f, g)        # exact bound at the bins (LP tolerance)


pieces, srcs = [], []
if base_hi:
    hb = h.max(); wall = h <= hb - t if hollow else np.ones(len(h), bool)
else:
    hb = h.min(); wall = h >= hb + t if hollow else np.ones(len(h), bool)
hw, rw = h[wall], r[wall]
edges = np.arange(hw.min(), hw.max() + 1e-9, a.band)
if edges[-1] < hw.max() - 1e-6:
    edges = np.r_[edges, hw.max()]
edges[-1] = hw.max()
angs = np.linspace(0, 2 * np.pi, a.seg + 1)
sec = 1.0 / np.cos(np.pi / a.seg)
band_rep = []
for b0, b1 in zip(edges[:-1], edges[1:]):
    k = (hw >= b0 - 1e-9) & (hw <= b1 + 1e-9)
    if k.sum() < 2:
        continue
    hb_, rb_ = hw[k], rw[k]
    if hollow:
        ro = rb_.copy(); ri = rb_ - t
        rep = dict(h_mm=[round(float(hb_.min()) * 1e3, 2), round(float(hb_.max()) * 1e3, 2)], bins=int(k.sum()))
        if a.outer_insc:
            f = envelope(hb_, rb_, convex=False); rep['outer_lowered_max_mm'] = round(float((rb_ - f).max()) * 1e3, 3)
            ro = f
        mid_o = ro * np.cos(np.pi / a.seg)                  # outer chord at mid-sector at the bins (lower bound)
        if a.outer_circ:
            mid_o = ro.copy(); ro = ro * sec; rep['outer_circ'] = True
        if a.inner_circ:
            f = envelope(hb_, rb_ - t, convex=True); rep['inner_raised_max_mm'] = round(float((f - (rb_ - t)).max()) * 1e3, 3)
            ri = f * sec
            # wall at mid-sector, lower bound at the bins: outer chord minus the inner tangent f
            wm = mid_o - f
            rep['wall_mid_min_mm'] = round(float(wm.min()) * 1e3, 3)
            rep['wall_mid_min_at_h_mm'] = round(float(hb_[np.argmin(wm)]) * 1e3, 2)
            rep['wall_edge_min_mm'] = round(float((ro - ri).min()) * 1e3, 3)
            assert (ro > ri).all() and (wm > 0).all(), 'wall vanishes'
        band_rep.append(rep)
        for a0, a1 in zip(angs[:-1], angs[1:]):
            V = np.array([P(hh, rr, an) for hh, rr in zip(hb_, ro) for an in (a0, a1)]
                         + [P(hh, max(rr, 1e-3), an) for hh, rr in zip(hb_, ri) for an in (a0, a1)])
            pieces.append(trimesh.convex.convex_hull(V)); srcs.append(None)
    else:
        ring = np.linspace(0, 2 * np.pi, 2 * a.seg, endpoint=False)
        V = np.array([P(hh, rr, an) for hh, rr in zip(hb_, rb_) for an in ring])
        pieces.append(trimesh.convex.convex_hull(V)); srcs.append(None)
if hollow and a.base_pieces:
    bp = sorted(glob.glob(os.path.join(a.base_pieces, 'piece_*.obj')))[a.base_first:]
    for f in bp:
        pieces.append(trimesh.load(f, force='mesh')); srcs.append(f)
elif hollow:                                                # ring base, exactly as lathe_collision.py
    rbase = float(r[np.argmax(h)] if base_hi else r[np.argmin(h)])
    hs = (hb - t, hb) if base_hi else (hb, hb + t)
    ring = np.linspace(0, 2 * np.pi, 2 * a.seg, endpoint=False)
    pieces.append(trimesh.convex.convex_hull(np.array([P(hh, rbase / 2, an) for hh in hs for an in ring]))); srcs.append(None)
    for a0, a1 in zip(angs[:-1], angs[1:]):
        V = np.array([P(hh, rr, an) for hh in hs for rr in (rbase / 2, rbase) for an in (a0, (a0 + a1) / 2, a1)])
        pieces.append(trimesh.convex.convex_hull(V)); srcs.append(None)
vol = np.array([p.volume for p in pieces]); rho = a.mass / vol.sum()
com = (np.array([p.center_mass for p in pieces]) * vol[:, None]).sum(0) / vol.sum()
I = np.zeros((3, 3))
for p, v in zip(pieces, vol):
    m = rho * v; Ip = p.moment_inertia * rho
    dv = p.center_mass - com; I += Ip + m * (dv @ dv * np.eye(3) - np.outer(dv, dv))
os.makedirs(a.out, exist_ok=True)
for k, (p, s) in enumerate(zip(pieces, srcs)):
    if s is None:
        p.export(f'{a.out}/piece_{k:02d}.obj')
    else:
        shutil.copyfile(s, f'{a.out}/piece_{k:02d}.obj')
rep = dict(tool='lathe_cavsafe (lathe_collision.py blob 680cc2f9 + opt-in cavity-safe options)', profile=a.profile,
           name=fit.get('name'), hollow=hollow, wall_t_mm=round(t * 1e3, 2),
           shrink_mm=round(a.shrink * 1e3, 2), segments=a.seg, band_cm=a.band * 100, pieces=len(pieces),
           volume_cm3=round(float(vol.sum() * 1e6), 1), height_cm=round(float((h.max() - h.min()) * 100), 2),
           r_out_cm=[round(float(r.min() * 100), 2), round(float(r.max() * 100), 2)], base_end='hi' if base_hi else 'lo',
           wall_fitted_mm=round(float(z['t']) * 1e3, 2), base_extended_mm=round(ext * 1e3, 2),
           max_piece_vertices=int(max(len(p.vertices) for p in pieces)),
           inner_circ=a.inner_circ, outer_insc=a.outer_insc, outer_circ=a.outer_circ,
           base=(f'{a.base_pieces} piece_{a.base_first:02d}.. copied byte for byte' if a.base_pieces else 'ring base'),
           bands=band_rep)
json.dump(dict(mass=a.mass, com=com.tolist(), inertia=I.tolist(), source='lathe_collision uniform solid pieces'),
          open(f'{a.out}/inertia.json', 'w'), indent=1)
json.dump(rep, open(f'{a.out}/lathe_collision.json', 'w'), indent=1)
print(json.dumps(rep), 'com_cm', np.round(com * 100, 2).tolist())
