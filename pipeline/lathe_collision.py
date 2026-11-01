"""Convex-piece simulator collision copy of a cup-like object from its lathe profile (2026-10-26; approach 2's L1 lathe
rule, docs/research/approaches-2026-10-25/approach2-primitive-meshes.md and approach2-scripts/RULES.md). GT-free: the
profile is fitted to OUR library mesh, in its frame. Only the simulator copy changes; the submitted mesh stays.

Why (eval 10, forensics 26 Oct): our beige cup (library_v3) is an open shell, so in the simulator it has no base and
falls over at frame 2 (89 deg, the episode's object error stays > 20 cm); our blue cup's CoACD hulls fill its cavity
(35 % solid), so the beige cup cannot nest in it and the contact solver overflows (njmax). A lathe body has a real
base and an empty cavity.

Pieces, in the mesh frame (point = c0 + h d + r (cos a e1 + sin a e2)):
  hollow: the wall from the mouth to the base's inner floor is split into height bands (<= BAND) and SEG angle segments;
          each piece is the convex hull of the outer (r_out(h) - SHRINK) and inner (r_out(h) - t - SHRINK) points of the
          profile bins in its band at the segment's two edge angles; the base is one prism of thickness t
          (radius r_out at the base - SHRINK, 2 x SEG sides);
  solid:  one prism stack per band (convex hull of the band's rings).
Also writes inertia.json (uniform density over the pieces, mass MASS): make_assets.py --pieces then uses this centre of
mass and inertia instead of the open-shell surface estimate.
Usage: python lathe_collision.py PROFILE.npz FIT.json OUT_DIR [--seg 16] [--band 0.03] [--shrink 0] [--solid] [--mass 0.3]
       [--inner INNER.npz]  (opt-in, 31 Oct, eval-10 ev10w: per-height cavity radius and band edges; without it the
       output is byte-identical to the earlier tool)
       PROFILE.npz / FIT.json: approach2-scripts/lathe_fit2.py outputs (<name>_profile.npz, <name>.json)."""
import argparse, json, os

import numpy as np
import trimesh

ap = argparse.ArgumentParser(); ap.add_argument('profile'); ap.add_argument('fit'); ap.add_argument('out')
ap.add_argument('--seg', type=int, default=16); ap.add_argument('--band', type=float, default=0.03)
ap.add_argument('--shrink', type=float, default=0.0, help='radial shrink (m), e.g. so a nested partner fits')
ap.add_argument('--solid', action='store_true'); ap.add_argument('--mass', type=float, default=0.3)
ap.add_argument('--wall', type=float, default=0.0, help='wall thickness (m) instead of the fitted one (0: fitted)')
ap.add_argument('--base_to_mesh', help='our mesh: extend the base end to its extreme point along the axis (the lathe rule '
                'cuts the base at the last observed ring, which can leave the body above the table the mesh stands on)')
ap.add_argument('--ext_max', type=float, default=1.0, help='cap (m) on the base extension, e.g. so the base does not start '
                'inside the table at the reference frame-0 pose (a start inside the support makes the object bounce)')
ap.add_argument('--base_from_hulls', help='our mesh: the base is FlashCHORD\'s own CoACD hulls of this mesh clipped to the '
                'base side of the inner floor (keeps the footing that stands in the simulator today; the walls above the '
                'floor come from the lathe, so the cavity is empty)')
ap.add_argument('--inner', help='opt-in (hollow only): npz with h, r_in (profile coordinate along d, m): the inner (cavity) '
                'radius of the wall pieces where r_in is finite (elsewhere r - wall), e.g. a widened lower cavity; optional '
                'band_edges (m, profile h) replace the --band edges, so that a widened band is not bridged by a convex piece '
                'that also spans unwidened heights')
a = ap.parse_args()
z = np.load(a.profile); fit = json.load(open(a.fit))
c0, d, e1, e2 = (np.asarray(z[k], float) for k in ('c0', 'd', 'e1', 'e2'))
h = np.asarray(z['prof_h'], float); r = np.asarray(z['prof_r'], float) - a.shrink
o = np.argsort(h); h, r = h[o], r[o]
t = a.wall if a.wall > 0 else float(z['t']); hollow = bool(fit.get('hollow')) and not a.solid
base_hi = fit.get('base', 'hi') == 'hi'                  # the base is at the high-h end of the body
ext = 0.0
if a.base_to_mesh:
    mv = (np.asarray(trimesh.load(a.base_to_mesh, force='mesh').vertices) - c0) @ d
    if base_hi and mv.max() > h.max():
        ext = min(mv.max() - h.max(), a.ext_max); h = np.r_[h, h.max() + ext]; r = np.r_[r, r[-1]]
    elif not base_hi and mv.min() < h.min():
        ext = min(h.min() - mv.min(), a.ext_max); h = np.r_[h.min() - ext, h]; r = np.r_[r[0], r]


def P(hh, rr, ang):
    return c0 + hh * d + rr * (np.cos(ang) * e1 + np.sin(ang) * e2)


pieces = []
if base_hi:
    hb = h.max(); wall = h <= hb - t if hollow else np.ones(len(h), bool)
else:
    hb = h.min(); wall = h >= hb + t if hollow else np.ones(len(h), bool)
hw, rw = h[wall], r[wall]
edges = np.arange(hw.min(), hw.max() + 1e-9, a.band)
if edges[-1] < hw.max() - 1e-6:
    edges = np.r_[edges, hw.max()]
edges[-1] = hw.max()
INNER = np.load(a.inner) if a.inner else None
if INNER is not None and 'band_edges' in INNER.files:
    be = np.asarray(INNER['band_edges'], float)
    edges = np.unique(np.r_[hw.min(), be[(be > hw.min()) & (be < hw.max())], hw.max()])
angs = np.linspace(0, 2 * np.pi, a.seg + 1)
if INNER is None:
    def r_in(hh, rr):
        return rr - t
else:
    ih, ir = np.asarray(INNER['h'], float), np.asarray(INNER['r_in'], float); io = np.argsort(ih); ih, ir = ih[io], ir[io]
    wmin = [np.inf, None]                                         # thinnest wall where r_in is used (m, at h)

    def r_in(hh, rr):
        v = float(np.interp(hh, ih, ir, left=np.nan, right=np.nan)) if ih.min() <= hh <= ih.max() else np.nan
        if not np.isfinite(v):
            return rr - t
        if rr - v < wmin[0]:
            wmin[0], wmin[1] = rr - v, hh
        return v
for b0, b1 in zip(edges[:-1], edges[1:]):
    k = (hw >= b0 - 1e-9) & (hw <= b1 + 1e-9)
    if k.sum() < 2:
        continue
    hb_, rb_ = hw[k], rw[k]
    if hollow:
        for a0, a1 in zip(angs[:-1], angs[1:]):
            V = np.array([P(hh, rr, an) for hh, rr in zip(hb_, rb_) for an in (a0, a1)]
                         + [P(hh, max(r_in(hh, rr), 1e-3), an) for hh, rr in zip(hb_, rb_) for an in (a0, a1)])
            pieces.append(trimesh.convex.convex_hull(V))
    else:
        ring = np.linspace(0, 2 * np.pi, 2 * a.seg, endpoint=False)
        V = np.array([P(hh, rr, an) for hh, rr in zip(hb_, rb_) for an in ring])
        pieces.append(trimesh.convex.convex_hull(V))
if hollow and a.base_from_hulls:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from interaction_carve import clip, fc_hulls, load_mesh
    floor = hb - t if base_hi else hb + t                          # keep where (x - c0).d >= floor (base hi) / <= floor
    nd, off = (-d, float(d @ c0 + floor)) if base_hi else (d, float(-(d @ c0) - floor))
    for V in fc_hulls(load_mesh(a.base_from_hulls)):
        Vc = clip(V, [(nd, off)])
        if Vc is not None:
            pieces.append(trimesh.convex.convex_hull(Vc))
elif hollow:                                                # base plate of thickness t, as SEG sectors: MuJoCo (Warp)
    rbase = float(r[np.argmax(h)] if base_hi else r[np.argmin(h)])   # gives one contact per convex pair, so a one-piece
    hs = (hb - t, hb) if base_hi else (hb, hb + t)                  # base stands on a single point and rocks over (eval 10
    ring = np.linspace(0, 2 * np.pi, 2 * a.seg, endpoint=False)    # CPU test, 26 Oct): a centre disc (r/2) plus SEG rim
    pieces.append(trimesh.convex.convex_hull(np.array([P(hh, rbase / 2, an) for hh in hs for an in ring])))   # sectors
    for a0, a1 in zip(angs[:-1], angs[1:]):                         # (r/2 to r) keep the contacts near the rim
        V = np.array([P(hh, rr, an) for hh in hs for rr in (rbase / 2, rbase) for an in (a0, (a0 + a1) / 2, a1)])
        pieces.append(trimesh.convex.convex_hull(V))
vol = np.array([p.volume for p in pieces]); rho = a.mass / vol.sum()
com = (np.array([p.center_mass for p in pieces]) * vol[:, None]).sum(0) / vol.sum()
I = np.zeros((3, 3))
for p, v in zip(pieces, vol):
    m = rho * v; Ip = p.moment_inertia * rho                  # trimesh: unit density, about the piece's centre of mass
    dv = p.center_mass - com; I += Ip + m * (dv @ dv * np.eye(3) - np.outer(dv, dv))
os.makedirs(a.out, exist_ok=True)
for k, p in enumerate(pieces):
    p.export(f'{a.out}/piece_{k:02d}.obj')
rep = dict(tool='lathe_collision', profile=a.profile, name=fit.get('name'), hollow=hollow, wall_t_mm=round(t * 1e3, 2),
           shrink_mm=round(a.shrink * 1e3, 2), segments=a.seg, band_cm=a.band * 100, pieces=len(pieces),
           volume_cm3=round(float(vol.sum() * 1e6), 1), height_cm=round(float((h.max() - h.min()) * 100), 2),
           r_out_cm=[round(float(r.min() * 100), 2), round(float(r.max() * 100), 2)], base_end='hi' if base_hi else 'lo',
           wall_fitted_mm=round(float(z['t']) * 1e3, 2), base_extended_mm=round(ext * 1e3, 2),
           max_piece_vertices=int(max(len(p.vertices) for p in pieces)))
if INNER is not None:
    rep.update(inner=a.inner, band_edges_mm=np.round(edges * 1e3, 2).tolist(),
               inner_min_wall_mm=round(float(wmin[0]) * 1e3, 2) if np.isfinite(wmin[0]) else None,
               inner_min_wall_at_h_mm=round(float(wmin[1]) * 1e3, 2) if wmin[1] is not None else None)
json.dump(dict(mass=a.mass, com=com.tolist(), inertia=I.tolist(), source='lathe_collision uniform solid pieces'),
          open(f'{a.out}/inertia.json', 'w'), indent=1)
json.dump(rep, open(f'{a.out}/lathe_collision.json', 'w'), indent=1)
print(json.dumps(rep), 'com_cm', np.round(com * 100, 2).tolist())
