#!/usr/bin/env python
"""P1-P3 physical checks on OUR references (GT-free)."""
import sys, json, numpy as np, trimesh
from scipy.spatial import ConvexHull
sys.path.insert(0, '.')
import refpose
L = '/home/user/v2d-track3/meshes/'; A = 'out/'
def load(p): return trimesh.load(p, force='mesh')
def world(m, pos, q):
    m = m.copy(); T = np.eye(4); T[:3, :3] = refpose.R_of(q); T[:3, 3] = pos; m.apply_transform(T); return m
def surf_com(m):
    tri = m.triangles; a = m.area_faces
    return (tri.mean(1) * a[:, None]).sum(0) / a.sum()
def stand(m, band=0.001):
    """static certificate on the plane through the lowest point (support_fill.py style)."""
    V = m.sample(40000); z0 = V[:, 2].min()
    S = V[V[:, 2] <= z0 + band][:, :2]
    com = surf_com(m)
    out = dict(n_support=int(len(S)))
    if len(S) < 3:
        return dict(out, inside=False, margin_mm=None)
    try:
        H = ConvexHull(S)
    except Exception:
        return dict(out, inside=False, margin_mm=None, note='degenerate')
    eq = H.equations                                          # a x + b y + c <= 0 inside
    d = -(eq[:, :2] @ com[:2] + eq[:, 2])
    inside = bool((d >= 0).all()); margin = float(d.min())
    h = com[2] - z0
    return dict(out, inside=inside, margin_mm=round(margin * 1e3, 1), tip_deg=round(float(np.degrees(np.arctan2(margin, h))), 1) if inside else None,
                support_area_cm2=round(H.volume * 1e4, 2))
def penetration(a, b, n=6000):
    """fraction of a's surface samples inside b, and max depth (mm)."""
    P = a.sample(n); inside = b.contains(P)
    if not inside.any(): return dict(frac_in=0.0, max_depth_mm=0.0)
    dist = np.abs(trimesh.proximity.signed_distance(b, P[inside]))
    return dict(frac_in=round(float(inside.mean()), 4), max_depth_mm=round(float(dist.max()) * 1e3, 1), p90_depth_mm=round(float(np.percentile(dist, 90)) * 1e3, 1))
res = {}
# P1: beige cup at eval-10 f0 (slot 1), blue cup at eval-10 f0 (slot 0) and ep21 f0 (slot 0)
nm, pos, q = refpose.load('ev10')
for lab, p in [('library_v3/beige', L + 'library_v3/beige_cup.glb'), ('library_v3x/beige', L + 'library_v3x/beige_cup.glb'),
               ('lathe2/beige_v3', A + 'lathe2/beige_cup_v3_body.glb'), ('lathe2/beige_v3x', A + 'lathe2/beige_cup_v3x_body.glb')]:
    res[f'P1 ev10 f0 {lab}'] = stand(world(load(p), pos[0, 1], q[0, 1]))
for lab, p in [('library_v3/blue', L + 'library_v3/blue_cup.glb'), ('lathe2/blue', A + 'lathe2/blue_cup_body.glb')]:
    res[f'P1 ev10 f0 {lab}'] = stand(world(load(p), pos[0, 0], q[0, 0]))
# axis tilt of the beige cup at f0 (lathe axis in world)
z = np.load(A + 'lathe2/beige_cup_v3x_profile.npz'); dw = refpose.R_of(q[0, 1]) @ z['d']
res['P1 ev10 f0 beige axis tilt vs vertical (deg)'] = round(float(np.degrees(np.arccos(abs(dw[2])))), 1)
# P2: nest at eval-10 last frame: beige in blue
f = len(pos) - 1
for lab, pb, pg in [('library (v3 blue, v3x beige)', L + 'library_v3/blue_cup.glb', L + 'library_v3x/beige_cup.glb'),
                    ('lathe2 (blue, beige_v3x)', A + 'lathe2/blue_cup_body.glb', A + 'lathe2/beige_cup_v3x_body.glb')]:
    blue = world(load(pb), pos[f, 0], q[f, 0]); beige = world(load(pg), pos[f, 1], q[f, 1])
    r = penetration(beige, blue)
    try:
        r['overlap_cm3'] = round(float(blue.intersection(beige, engine='manifold').volume) * 1e6, 2)
    except Exception as e:
        r['overlap_cm3'] = None
    res[f'P2 ev10 last frame beige-in-blue {lab}'] = r
# P3: lid in pot at f0 of ep2 and eval 1
for key in ['ep2', 'ev1']:
    nm, pos, q = refpose.load(key)
    lid = world(load(L + 'library_v3/white_pot_lid.glb'), pos[0, 1], q[0, 1])
    for lab, pp in [('library pot', L + 'library_v3/white_pot.glb'), ('lathe2 pot body', A + 'lathe2/white_pot_body.glb')]:
        pot = world(load(pp), pos[0, 0], q[0, 0])
        r = penetration(lid, pot)
        try:
            r['overlap_cm3'] = round(float(pot.intersection(lid, engine='manifold').volume) * 1e6, 2)
        except Exception:
            r['overlap_cm3'] = None
        res[f'P3 {key} f0 lid-in-pot {lab}'] = r
json.dump(res, open(A + 'phys_checks.json', 'w'), indent=1)
for k, v in res.items(): print(k, v)
