#!/usr/bin/env python3
"""Parametric wooden-spoon template for V2D Track 3 (the eval `wooden_spoon` has no public scan).

Builds ONE closed, consistently oriented, edge- and vertex-manifold triangle surface (genus 0, single component, no
self-intersections) of a wooden cooking spoon plus its 3 mocap markers (grey sphere on a short black stem each, unioned
into the body: no interior faces), natively under the kit budget of 4,096 faces and 4,096 vertices, then expresses it in
the scan frame given by rule R1 (note 13 "Final summary" item 2):
    origin = exact area-weighted surface centroid; axes = exact area-weighted surface PCA
    (x smallest, y middle, z largest variance); z and y signed by POSITIVE third moment; x = y cross z.
The canonical frame is whatever the rule gives on this shape; it is NOT forced to frame B. The script reports whether it
is frame B (+z bowl -> handle end, +y toward M2, +x out of the concave face) and the skews that decide it.

Construction frame C (metres): z_C along the handle axis from the bowl tip (z=0) to the handle end; x_C = out of the
CONCAVE face of the bowl (up when the spoon rests concave-up); y_C = z_C x x_C, i.e. toward M2 (the handle-side side
marker); M1 (bowl-neck side marker) is on -y_C. The handle axis is the line x_C = y_C = 0 (marker offsets in note 20 are
measured relative to it). Frame B == (x_C, y_C, z_C) up to small tilts.

Defaults and their sources (all [E] estimates, see README.md / params.json for uncertainties):
  note 13 Stage A ruler (length ~30 cm, bowl ~9.5 x 5.2 cm, neck ~1.6 cm, round ~2 cm handle), Stage B/C (round handle,
  shell 4-6 mm, bowl depth ~1 cm [H]); note 17 (marker spheres r 6.6-7.8 mm, median ~7.2 mm, CAD-like); public-scan mount
  profile measured here (sphere centre 10.1-11.7 mm above the host surface, collar ~7 -> ~4.4 mm radius); note 20 Stage B
  + re-run (marker triangle 53.0/153.2/194.2 mm; marker offsets vs the handle axis; handle radius 9.8-10, bulge
  18.8 -> 21.3 -> 18.8 mm; rim plane 0-4 mm above the axis; bowl offset toward M1 +1.3 +- 0.8 mm).

Usage:
  python spoon_template.py                 # build defaults, run checks, write outputs next to this file
  python spoon_template.py --out DIR --params my.json   # override parameters (JSON with any subset of DEFAULTS keys)
  python spoon_template.py --variants      # also run the frame-sensitivity variants (README table)
Dependencies: numpy, scipy (least_squares, cKDTree, norm), trimesh (GLB export/reload only).
"""
import argparse
import copy
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------------------------------------------------------
DEFAULTS = {
    # --- body (metres / degrees) ---
    "total_length": "auto",      # wood length tip -> handle end; 'auto' = put M3 at mount_height above the end cap
    "bowl_length": 0.095,        # tip -> bowl end (note 13: 9-10 cm)
    "bowl_width": 0.052,         # max planform width of the bowl (note 13: ~5.2 cm)
    "bowl_widest_frac": 0.50,    # where the bowl is widest, as a fraction of bowl_length from the tip [H]
    "bowl_depth": 0.010,         # dish depth of the shell mid-surface below the rim at the bowl centre [H ~1 cm]
    "bowl_thickness": 0.005,     # shell wall thickness (note 13: 4-6 mm [H])
    "rim_height": 0.002,         # rim mid-plane above the handle axis toward the concave face (note 20: 0-4 mm)
    "bowl_bend": 0.0013,         # in-plane lateral offset of the bowl centre toward M1 (note 20 re-run +1.3 +- 0.8 mm)
    "bowl_pitch_deg": 0.0,       # bowl tip rotated toward the concave face about the pivot (not measured as body shape)
    "pivot_station": 0.118,      # station of the bend/pitch pivot (note 20: tip/bowl offset ratio ~ rotation about neck)
    "bend_blend": 0.010,         # half-width of the C1 blend of the bend/pitch shear around the pivot
    "neck_station": 0.105,       # station of the narrowest planform width
    "neck_width": 0.016,         # note 13: ~1.6 cm
    "neck_aspect": 1.0,          # neck thickness / width (1 = round) [H]
    "handle_station": 0.172,     # station where the handle reaches handle_d_start (note 20: 18.8 mm at s ~ +32)
    "handle_d_start": 0.0188,    # note 20 re-run: image width 18.8 mm
    "handle_d_max": 0.0213,      # note 20 re-run: bulge 21.3 mm (mid-handle)
    "handle_d_end": 0.0188,      # note 20 re-run: 18.8 mm before the rounded end
    "handle_aspect": 1.0,        # handle thickness / width (1 = round; note 20: round rod, radius 9.8-10)
    "end_cap_length": "auto",    # length of the rounded end; 'auto' = handle_d_end / 2 (hemispherical end)
    "bowl_blend_in": 0.010,      # shell -> solid neck blend starts this far before bowl_length
    "bowl_blend_out": 0.015,     # ... and ends this far after it
    # --- markers ---
    "marker_layout": "note20",   # 'note20' (measured, WLS-adjusted to the triangle), 'note13' (in-plane model), 'none'
    "marker_radius": 0.0072,     # note 17: one physical size, fitted r 6.6-7.8 mm (median ~7.2)
    "marker_stem_foot_radius": 0.0055,   # stem radius on the body (public scans: collar ~7 mm at the pad -> ~4.4 mm)
    "marker_junction_frac": 0.82,        # sphere centre sits 0.82 r above the stem/sphere junction plane (public scans)
    "marker_mount_height": 0.0109,       # sphere centre above the host surface (public scans: 10.1-11.7 mm, median ~10.9)
    # note-20 measured layout (mm; lat = away from the handle axis toward the marker's own side, up = toward the concave
    # face; M3 lat is toward M2). Each entry (mean, sd). Adjusted jointly with the triangle by weighted least squares.
    "m_station1": [120.5, 3.0],  # M1 station from the bowl tip (116-125)
    "m_dz12": [41.5, 1.5],       # M2 - M1 along the axis (40-43)
    "m_station3": [315.0, 3.0],  # M3 station from the bowl tip (311-319)
    "m_lat1": [18.9, 0.6], "m_up1": [6.0, 1.5],
    "m_lat2": [15.5, 0.8], "m_up2": [10.0, 2.0],   # 15.9 +- 0.7 (Stage B) and 15.2 +- 0.8 (re-run) pooled
    "m_lat3": [1.9, 1.2], "m_up3": [11.0, 1.5],
    "m_tri": [[53.0, 1.6], [153.2, 0.6], [194.2, 1.5]],  # |M1M2|, |M2M3|, |M1M3| (note 20, 28 frames / 8 clips)
    "note13_stations": [0.114, 0.154],                    # note 13 Stage A ruler stations (only for layout 'note13')
}

RES = {  # tessellation (fixed topology for a given RES)
    "n_tip": 10, "n_bowl": 9, "n_neck": 16, "n_handle": 14, "n_end": 6,   # stations per body segment
    "n_cap": 5, "n_flat": 7,             # section columns per rounded side / per flat side (nphi = 2*(n_cap+n_flat))
    "bowl_cap_deg": 65.0,                # angular half-span of the rim caps in the bowl sections
    "n_marker": 16, "n_sphere_rings": 6,  # marker ring resolution
    "smooth_p": 6.0,                     # p of the smooth max between bowl and neck planforms
}

WOOD_RGBA = (236, 204, 180, 255)   # note 13 colour probe: H12 S61-70 V236-239 (OpenCV), pale beech
STEM_RGBA = (25, 25, 25, 255)      # black marker base
SPHERE_RGBA = (165, 165, 165, 255)  # grey retro-reflective sphere

MESH_FACE_BUDGET = 4096
MESH_VERT_BUDGET = 4096


def resolve_params(user=None):
    p = copy.deepcopy(DEFAULTS)
    if user:
        unknown = set(user) - set(p)
        if unknown:
            raise KeyError(f"unknown parameters: {sorted(unknown)}")
        p.update(copy.deepcopy(user))
    if p["end_cap_length"] == "auto":
        p["end_cap_length"] = 0.5 * p["handle_d_end"]
    return p


# ----------------------------------------------------------------------------------------------------------------------
# Marker layout
# ----------------------------------------------------------------------------------------------------------------------
def solve_marker_layout_note20(p):
    """Weighted least squares of the 9 marker coordinates against the note-20 measurements and the measured triangle.
    Returns (centres (3,3) in construction frame, metres), report dict."""
    from scipy.optimize import least_squares
    keys = ["m_station1", "m_dz12", "m_station3", "m_lat1", "m_up1", "m_lat2", "m_up2", "m_lat3", "m_up3"]
    pri = np.array([p[k] for k in keys], float)
    tri = np.array(p["m_tri"], float)

    def pts(q):
        z1, dz, z3, l1, u1, l2, u2, l3, u3 = q
        return np.array([[u1, -l1, z1], [u2, l2, z1 + dz], [u3, l3, z3]])

    def res(q):
        r = list((q - pri[:, 0]) / pri[:, 1])
        M = pts(q)
        for (a, b), (d, sd) in zip(((0, 1), (1, 2), (0, 2)), tri):
            r.append((np.linalg.norm(M[a] - M[b]) - d) / sd)
        return np.array(r)

    sol = least_squares(res, pri[:, 0].copy())
    J = sol.jac
    cov = np.linalg.inv(J.T @ J)
    M = pts(sol.x)
    rep = {
        "method": "weighted least squares: 9 coordinates vs note-20 priors + 3 triangle lengths",
        "chi2": float((sol.fun ** 2).sum()), "dof_note": "12 residuals, 9 unknowns",
        "adjusted_mm": {k: [round(float(v), 3), round(float(np.sqrt(cov[i, i])), 3)] for i, (k, v) in enumerate(zip(keys, sol.x))},
        "triangle_mm": [round(float(np.linalg.norm(M[a] - M[b])), 3) for a, b in ((0, 1), (1, 2), (0, 2))],
        "triangle_target_mm": tri[:, 0].tolist(),
    }
    return M * 1e-3, rep


def resolve_length_and_markers(p):
    """Fix total_length ('auto') and the marker centres. Returns centres (k,3) metres or None, report dict."""
    rep = {}
    lay = p["marker_layout"]
    M = None
    if lay == "note20" or p["total_length"] == "auto":
        M, rep = solve_marker_layout_note20(p)
    if p["total_length"] == "auto":
        # M3 centre at marker_mount_height above the hemispherical end cap (cap centre on the axis at L - rc)
        rc, hm = p["end_cap_length"], p["marker_mount_height"]
        x3, y3, z3 = M[2]
        rad = (0.5 * p["handle_d_end"] + hm) ** 2 - x3 ** 2 - y3 ** 2
        if rad <= 0:
            raise ValueError("M3 too far off-axis for the end cap; set total_length explicitly")
        p["total_length"] = float(z3 + rc - math.sqrt(rad))
        rep["total_length_rule"] = "auto: M3 centre at marker_mount_height above the hemispherical end cap"
    if lay == "note13":
        M = None  # placed after the body exists (needs the half-width); see place_note13_markers
    if lay == "none":
        M = None
    rep["total_length"] = p["total_length"]
    return M, rep


# ----------------------------------------------------------------------------------------------------------------------
# Body loft (written with elementwise array ops only; `xp` = numpy here; see fit_spoon.py for the torch use)
# ----------------------------------------------------------------------------------------------------------------------
def loft_layout(res):
    """Parameter-independent layout = topology: per station (segment id, warped fraction, cap scale);
    per column (side kind 0..3, fraction)."""
    seg, fr, cap = [], [], []
    n = res["n_tip"]; k = np.arange(1, n + 1) / n
    seg += [0] * n; fr += list(1.0 - np.cos(k * np.pi / 2)); cap += [1.0] * n
    for sid, key in ((1, "n_bowl"), (2, "n_neck"), (3, "n_handle")):
        n = res[key]; k = np.arange(1, n + 1) / n
        seg += [sid] * n; fr += list(k); cap += [1.0] * n
    n = res["n_end"]; th = np.arange(1, n + 1) / (n + 1) * np.pi / 2
    seg += [4] * n; fr += list(np.sin(th)); cap += list(np.cos(th))
    kind, cf = [], []
    for kd, cnt in ((0, res["n_cap"]), (1, res["n_flat"]), (2, res["n_cap"]), (3, res["n_flat"])):
        kind += [kd] * cnt; cf += list(np.arange(cnt) / cnt)
    return dict(seg=np.array(seg), frac=np.array(fr), capscale=np.array(cap), kind=np.array(kind), cfrac=np.array(cf))


def _smoothstep(xp, t):
    t = xp.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _softramp(xp, d, a):
    """C1 approximation of max(d, 0): quadratic blend for |d| < a."""
    return xp.where(d > a, d, xp.where(d < -a, 0.0 * d, (d + a) ** 2 / (4.0 * a)))


def _tan(xp, a):
    return xp.tan(a) if hasattr(a, "shape") else math.tan(a)


def station_profile(p, lay, res, xp=np):
    """Per-station section descriptors. All lengths in metres."""
    L, Lb = p["total_length"], p["bowl_length"]
    smax = p["bowl_widest_frac"] * Lb
    sn, sh0 = p["neck_station"], p["handle_station"]
    rc = p["end_cap_length"]; se = L - rc
    seg = lay["seg"]; fr = lay["frac"]; capsc = lay["capscale"]
    starts = xp.stack([0.0 * L, smax + 0.0 * L, Lb + 0.0 * L, sh0 + 0.0 * L, se])
    lens = xp.stack([smax + 0.0 * L, (Lb - smax) + 0.0 * L, (sh0 - Lb) + 0.0 * L, se - sh0, rc + 0.0 * L])
    s = starts[seg] + lens[seg] * fr
    is_cap = seg == 4

    # bowl planform (skewed ellipse) and dish
    u = xp.where(s < smax, (s - smax) / smax, (s - smax) / (Lb - smax))
    u = xp.clip(u, -1.0, 1.0)
    one_m_u2 = xp.clip(1.0 - u * u, 0.0, 1.0)
    wb = 0.5 * p["bowl_width"] * xp.sqrt(one_m_u2)
    Ds = xp.where(s < Lb, p["bowl_depth"] * one_m_u2, 0.0 * s)

    # neck / handle planform
    bin_, bout = p["bowl_blend_in"], p["bowl_blend_out"]
    em = _smoothstep(xp, (s - (Lb - bin_)) / bin_)                    # neck emerges inside the bowl rear
    rn = 0.5 * p["neck_width"]
    t1 = _smoothstep(xp, (s - sn) / (sh0 - sn))
    r_nh = rn + (0.5 * p["handle_d_start"] - rn) * t1
    tau = xp.clip((s - sh0) / (se - sh0), 0.0, 1.0)
    d0, d1, dm = p["handle_d_start"], p["handle_d_end"], p["handle_d_max"]
    r_h = 0.5 * (d0 + (d1 - d0) * tau) + 4.0 * (0.5 * dm - 0.25 * (d0 + d1)) * tau * (1.0 - tau)
    wh = xp.where(s <= sh0, r_nh * em, r_h)
    P = res["smooth_p"]
    w = xp.where(s <= sh0, (wb ** P + wh ** P + 1e-30) ** (1.0 / P), wh)
    r_end = 0.5 * d1
    w = xp.where(is_cap, r_end * capsc, w)

    # vertical half-thickness, centre height, lateral centre
    beta = _smoothstep(xp, (s - (Lb - bin_)) / (bin_ + bout))
    beta = xp.where(is_cap, 1.0 + 0.0 * s, beta)
    kasp = p["neck_aspect"] + (p["handle_aspect"] - p["neck_aspect"]) * t1
    kasp = xp.where(s > sh0, p["handle_aspect"] + 0.0 * s, kasp)
    h_solid = xp.where(is_cap, w * p["handle_aspect"], wh * kasp)
    hv = (1.0 - beta) * 0.5 * p["bowl_thickness"] + beta * h_solid

    piv, a = p["pivot_station"], p["bend_blend"]
    g = _softramp(xp, piv - s, a)                     # ~ (pivot - s) on the bowl side, 0 on the handle side
    g_c = _softramp(xp, piv - smax + 0.0 * s, a)
    yc = -p["bowl_bend"] * g / g_c                    # toward M1 = -y
    x0 = (1.0 - beta) * p["rim_height"] + _tan(xp, p["bowl_pitch_deg"] * (math.pi / 180.0)) * g
    psic = (1.0 - beta) * math.radians(res["bowl_cap_deg"]) + beta * (math.pi * res["n_cap"] / (2.0 * (res["n_cap"] + res["n_flat"])))
    return dict(s=s, w=w, hv=hv, x0=x0, yc=yc, Ds=Ds, psic=psic, beta=beta, u=u)


def section_points(prof, lay, xp=np):
    """Grid of section points (n_stations, nphi, 3) in the construction frame."""
    w, hv, x0, yc, Ds, psic, s = (prof[k][:, None] for k in ("w", "hv", "x0", "yc", "Ds", "psic", "s"))
    kind = lay["kind"]; cf = lay["cfrac"]
    A = xp.stack([-psic, psic, math.pi - psic, math.pi + psic], -1)[..., 0, :]      # (ns, 4)
    B = xp.stack([2 * psic, math.pi - 2 * psic, 2 * psic, math.pi - 2 * psic], -1)[..., 0, :]
    psi = A[:, kind] + B[:, kind] * cf[None, :]
    rho = xp.minimum(w, hv)
    m = w - rho
    k = hv / rho
    Ds = Ds * xp.clip(m / (2.0 * rho), 0.0, 1.0)   # no dish on sections without a flat midline (tip / neck)
    c0 = xp.cos(psic)
    sig = xp.clip(xp.cos(psi) / c0, -1.0, 1.0)
    My = yc + m * sig
    Mx = x0 - Ds * (1.0 - sig * sig)
    Ty = m + 1e-12
    Tx = 2.0 * Ds * sig
    nrm = xp.sqrt(Ty * Ty + Tx * Tx)
    Ty, Tx = Ty / nrm, Tx / nrm
    ny, nx = -Tx, Ty
    cp, sp = xp.cos(psi), xp.sin(psi)
    Py = My + rho * (cp * Ty + k * sp * ny)
    Px = Mx + rho * (cp * Tx + k * sp * nx)
    Pz = s + 0.0 * Px
    return xp.stack([Px, Py, Pz], -1)


def body_mesh(p, res=RES):
    """Closed lofted body: (V, F, info). Orientation: outward normals (positive signed volume)."""
    lay = loft_layout(res)
    prof = station_profile(p, lay, res, np)
    G = section_points(prof, lay, np)                       # (ns, nphi, 3)
    ns, nphi, _ = G.shape
    # tip pole: rim mid-plane height and lateral centre extrapolated to s = 0
    g0 = _softramp(np, np.array(p["pivot_station"]), p["bend_blend"])
    gc = _softramp(np, np.array(p["pivot_station"] - p["bowl_widest_frac"] * p["bowl_length"]), p["bend_blend"])
    tip = np.array([p["rim_height"] + math.tan(math.radians(p["bowl_pitch_deg"])) * g0, -p["bowl_bend"] * g0 / gc, 0.0])
    end = np.array([0.0, 0.0, p["total_length"]])
    V = np.concatenate([G.reshape(-1, 3), tip[None], end[None]])
    i_tip, i_end = ns * nphi, ns * nphi + 1
    idx = np.arange(ns * nphi).reshape(ns, nphi)
    F = []
    for i in range(ns - 1):
        a, b = idx[i], idx[i + 1]
        a2, b2 = np.roll(a, -1), np.roll(b, -1)
        d1 = np.linalg.norm(V[a] - V[b2], axis=1)   # diagonal a-b2
        d2 = np.linalg.norm(V[a2] - V[b], axis=1)   # diagonal a2-b
        use1 = d1 <= d2
        F.append(np.where(use1[:, None], np.stack([a, b, b2], 1), np.stack([a, b, a2], 1)))
        F.append(np.where(use1[:, None], np.stack([a, b2, a2], 1), np.stack([b, b2, a2], 1)))
    F.append(np.stack([np.full(nphi, i_tip), idx[0], np.roll(idx[0], -1)], 1))
    F.append(np.stack([np.full(nphi, i_end), np.roll(idx[-1], -1), idx[-1]], 1))
    F = np.concatenate(F).astype(np.int64)
    if signed_volume(V, F) < 0:
        F = F[:, ::-1].copy()
    info = dict(n_stations=int(ns), nphi=int(nphi), prof={k: np.asarray(v) for k, v in prof.items() if np.ndim(v) > 0})
    return V, F, info


# ----------------------------------------------------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------------------------------------------------
def signed_volume(V, F):
    T = V[F]
    return float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)


def tri_areas(V, F):
    T = V[F]
    return 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)


def closest_point_on_mesh(p, V, F):
    """Exact closest point on a triangle mesh (Ericson 5.1.5, vectorised over triangles)."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    ab, ac, ap = B - A, C - A, p - A
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - B; d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - C; d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4
    out = np.empty_like(A); done = np.zeros(len(A), bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = (d1 <= 0) & (d2 <= 0); out[m] = A[m]; done |= m
        m = ~done & (d3 >= 0) & (d4 <= d3); out[m] = B[m]; done |= m
        m = ~done & (vc <= 0) & (d1 >= 0) & (d3 <= 0); t = d1 / (d1 - d3); out[m] = A[m] + t[m, None] * ab[m]; done |= m
        m = ~done & (d6 >= 0) & (d5 <= d6); out[m] = C[m]; done |= m
        m = ~done & (vb <= 0) & (d2 >= 0) & (d6 <= 0); t = d2 / (d2 - d6); out[m] = A[m] + t[m, None] * ac[m]; done |= m
        m = ~done & (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        t = (d4 - d3) / ((d4 - d3) + (d5 - d6)); out[m] = B[m] + t[m, None] * (C[m] - B[m]); done |= m
        m = ~done; den = 1.0 / (va + vb + vc); v, w = vb * den, vc * den
        out[m] = A[m] + ab[m] * v[m, None] + ac[m] * w[m, None]
    d = np.linalg.norm(out - p, axis=1)
    i = int(np.argmin(d))
    return out[i], float(d[i]), i


def ray_first_hit(o, d, V, F):
    """Smallest positive t of ray o + t d against the mesh (Moller-Trumbore), or None."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    e1, e2 = B - A, C - A
    pv = np.cross(d, e2); det = (e1 * pv).sum(1)
    ok = np.abs(det) > 1e-18
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    sv = o - A; u = (sv * pv).sum(1) * inv
    q = np.cross(sv, e1); v = (q @ d) * inv; t = (e2 * q).sum(1) * inv
    hit = ok & (u >= -1e-10) & (v >= -1e-10) & (u + v <= 1 + 1e-10) & (t > 1e-9)
    if not hit.any():
        return None, None
    i = np.nonzero(hit)[0][np.argmin(t[hit])]
    return float(t[i]), int(i)


def orthobasis(d):
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u)
    return u, np.cross(d, u)


# ----------------------------------------------------------------------------------------------------------------------
# Marker union (stem + sphere stitched into a hole cut in the body: one manifold surface, no interior faces)
# ----------------------------------------------------------------------------------------------------------------------
def _col_arc(cols, nphi):
    """Smallest circular arc [j0, j0+len) covering the given column indices; returns (j0, length)."""
    c = np.unique(np.asarray(cols) % nphi)
    if len(c) == nphi:
        return 0, nphi
    gaps = np.diff(np.concatenate([c, [c[0] + nphi]]))
    k = int(np.argmax(gaps))
    j0 = int(c[(k + 1) % len(c)])
    length = int(nphi - gaps[k] + 1)
    return j0, length


def attach_marker(V, F, col, centre, p, res, name, grid):
    """Cut a hole in the surface under the marker, build stem (frustum) + sphere as a surface of revolution about the
    foot normal direction, and stitch the stem's foot ring to the hole boundary. Returns V, F, col, report.
    The hole is a rectangle of whole loft quads in (station, column) grid space (1-cell margin around the cells hit by
    the foot ring), or a full cap around a pole when it reaches one: its boundary is star-shaped around the stem axis."""
    r = p["marker_radius"]; rs0 = p["marker_stem_foot_radius"]; jf = p["marker_junction_frac"]
    Ns, nsr = res["n_marker"], res["n_sphere_rings"]
    foot, dist, _ = closest_point_on_mesh(centre, V, F)
    d = (centre - foot) / dist
    stem_len = dist - jf * r
    if stem_len < 0.0005:
        raise ValueError(f"{name}: sphere would intersect the body (centre {dist*1e3:.1f} mm from the surface)")
    u, v = orthobasis(d)
    th = 2 * np.pi * np.arange(Ns) / Ns
    circ = np.cos(th)[:, None] * u + np.sin(th)[:, None] * v
    # foot ring: circle of radius rs0 around the axis, projected along -d onto the body surface
    H = dist + 0.02
    ring, hitf = [], []
    for k in range(Ns):
        o = foot + rs0 * circ[k] + H * d
        t, fi = ray_first_hit(o, -d, V, F)
        if t is None:
            raise RuntimeError(f"{name}: foot ring ray {k} missed the body")
        ring.append(o - t * d); hitf.append(fi)
    ring = np.array(ring)
    depth = (ring - foot) @ d
    if depth.max() > stem_len - 0.0003:
        raise RuntimeError(f"{name}: stem too short for the surface curvature under the foot ring")
    # hole: rectangle of loft quads (grid rows x circular column arc) around the cells hit by the foot ring
    ns, nphi = grid
    nb = ns * nphi                      # body grid vertices 0..nb-1; tip pole nb, end pole nb+1
    _, _, ffoot = closest_point_on_mesh(foot, V, F)
    hv_ = np.unique(F[np.array(hitf + [ffoot])].ravel())
    if (hv_ >= nb + 2).any():
        raise RuntimeError(f"{name}: foot ring lands on an earlier marker")
    rows = [int(x) // nphi for x in hv_ if x < nb]
    cols = [int(x) % nphi for x in hv_ if x < nb]
    if (nb in hv_) or min(rows) - 1 < 0:
        raise RuntimeError(f"{name}: hole reaches the bowl-tip pole (not supported)")
    O = None
    last_err = None
    pole_hit = (nb + 1) in hv_ or max(rows) + 1 >= ns - 1
    rows_a, cols_a = np.array(rows), np.array(cols)
    if pole_hit:   # full polar cap from row ip to the end pole, plus a rectangular tongue below it (ip = imin: cap only)
        # smallest hole first: polar cap from row ip (ns-1 = just the pole fan) down to imin (= full cap, no tongue)
        shapes = [("cap+tongue", g, ip) for g in range(1, 4) for ip in range(ns - 1, min(rows) - g - 1, -1)]
    else:
        shapes = [("rect", g, None) for g in range(1, 5)]
    for shape, grow, ip in shapes:           # try hole shapes until the boundary is a clean star-shaped loop
        imin, imax = min(rows) - grow, min(max(rows) + grow, ns - 1)
        if imin < 0:
            raise RuntimeError(f"{name}: hole reaches the bowl-tip pole (not supported)")
        inset = np.zeros(len(V), bool)
        if shape == "cap+tongue":
            inset[ip * nphi: nb] = True; inset[nb + 1] = True
            below = rows_a < ip
            if below.any() and ip > imin:
                j0, ln = _col_arc(cols_a[below], nphi)
                j0, ln = (j0 - grow) % nphi, ln + 2 * grow
                if ln >= nphi:
                    last_err = "hole would wrap all the way around the body"; continue
                rr = np.arange(imin, ip); cc = (j0 + np.arange(ln)) % nphi
                inset[(rr[:, None] * nphi + cc[None, :]).ravel()] = True
        else:
            j0, ln = _col_arc(cols, nphi)
            j0, ln = (j0 - grow) % nphi, ln + 2 * grow
            if ln >= nphi:
                last_err = "hole would wrap all the way around the body"; continue
            rr = np.arange(imin, imax + 1); cc = (j0 + np.arange(ln)) % nphi
            inset[(rr[:, None] * nphi + cc[None, :]).ravel()] = True
        kill = inset[F].all(1)
        F2 = F[~kill]
        de = np.concatenate([F2[:, [0, 1]], F2[:, [1, 2]], F2[:, [2, 0]]])
        key = de[:, 0] * (len(V) + 1) + de[:, 1]
        rkey = de[:, 1] * (len(V) + 1) + de[:, 0]
        bnd = de[~np.isin(key, rkey)]
        nxt = {}
        ok = True
        for a_, b_ in bnd:
            if a_ in nxt:
                ok = False; last_err = "hole boundary is not a simple loop"; break
            nxt[int(a_)] = int(b_)
        if not ok:
            continue
        start = int(bnd[0, 0]); loop = [start]
        while nxt[loop[-1]] != start and len(loop) <= len(bnd):
            loop.append(nxt[loop[-1]])
        if len(loop) != len(bnd):
            last_err = "hole boundary has several loops"; continue
        Oc = np.array(loop)
        ang = np.arctan2((V[Oc] - foot) @ v, (V[Oc] - foot) @ u)
        steps = np.angle(np.exp(1j * np.diff(np.concatenate([ang, ang[:1]]))))
        if steps.sum() < 0:                   # make CCW about d
            Oc, ang = Oc[::-1], ang[::-1]
            steps = np.angle(np.exp(1j * np.diff(np.concatenate([ang, ang[:1]]))))
        if not (steps > 0).all() or abs(steps.sum() - 2 * np.pi) > 1e-6:
            last_err = "hole boundary is not star-shaped around the stem axis"; continue
        if (np.linalg.norm((V[Oc] - foot) - np.outer((V[Oc] - foot) @ d, d), axis=1) <= rs0 + 0.0003).any():
            last_err = "hole boundary vertex inside the stem foot ring"; continue
        O = Oc
        break
    if O is None:
        raise RuntimeError(f"{name}: {last_err}")
    # new vertices: foot ring, junction ring, sphere rings, pole
    alpha_j = math.acos(-jf)
    alphas = np.linspace(alpha_j, 0.0, nsr + 2)[1:-1]
    jc = centre - jf * r * d
    jring = jc + r * math.sqrt(1 - jf * jf) * circ
    rings = [ring, ring + 0.12 * (jring - ring), jring]   # foot ring (wood), black stem from 12 % up, junction
    for al in alphas:
        rings.append(centre + r * (math.sin(al) * circ + math.cos(al) * d))
    pole = centre + r * d
    n0 = len(V)
    newV = np.concatenate(rings + [pole[None]])
    ridx = [n0 + i * Ns + np.arange(Ns) for i in range(len(rings))]
    i_pole = n0 + len(rings) * Ns
    newF = []
    for a_, b_ in zip(ridx[:-1], ridx[1:]):
        a2, b2 = np.roll(a_, -1), np.roll(b_, -1)
        newF += [np.stack([a_, a2, b2], 1), np.stack([a_, b2, b_], 1)]
    last = ridx[-1]
    newF.append(np.stack([last, np.roll(last, -1), np.full(Ns, i_pole)], 1))
    # zipper between hole boundary O (outer) and foot ring I (inner), both CCW about d
    I = ridx[0]
    ai = th.copy()
    j0 = int(np.argmin(np.abs(np.angle(np.exp(1j * (ang - ai[0]))))))
    O = np.roll(O, -j0); ao0 = np.angle(np.exp(1j * (np.roll(ang, -j0) - ai[0])))
    ao = ao0[0] + np.concatenate([[0.0], np.cumsum(np.angle(np.exp(1j * np.diff(ao0))))])
    No = len(O)
    Oe = np.concatenate([O, O[:1]]); aoe = np.concatenate([ao, [ao[0] + 2 * np.pi]])
    Ie = np.concatenate([I, I[:1]]); aie = np.concatenate([ai, [2 * np.pi]])
    zi = zj = 0; Z = []
    while zi < Ns or zj < No:
        adv_outer = zi == Ns or (zj < No and aoe[zj + 1] <= aie[zi + 1])
        if adv_outer:
            Z.append([Oe[zj], Oe[zj + 1], Ie[zi]]); zj += 1
        else:
            Z.append([Ie[zi], Oe[zj], Ie[zi + 1]]); zi += 1
    newF.append(np.array(Z))
    V = np.concatenate([V, newV])
    F = np.concatenate([F2] + [np.asarray(x, np.int64) for x in newF])
    ncol = np.zeros((len(newV), 4), np.uint8)
    ncol[:Ns] = WOOD_RGBA            # foot ring lies on the body surface: the stitch strip stays wood-coloured
    ncol[Ns: 3 * Ns] = STEM_RGBA
    ncol[3 * Ns:] = SPHERE_RGBA
    col = np.concatenate([col, ncol])
    rep = dict(centre_mm=(centre * 1e3).round(2).tolist(), foot_mm=(foot * 1e3).round(2).tolist(),
               axis=d.round(4).tolist(), centre_above_surface_mm=round(dist * 1e3, 2), stem_len_mm=round(stem_len * 1e3, 2),
               foot_ring_depth_mm=[round(float(depth.min() * 1e3), 2), round(float(depth.max() * 1e3), 2)],
               faces_removed=int(kill.sum()), hole_shape=shape if ip is None else f'{shape} (cap from station row {ip})', hole_grow_cells=int(grow), hole_loop_vertices=int(No), faces_added=int(sum(len(x) for x in newF)))
    return V, F, col, rep


def remove_unreferenced(V, F, col):
    used = np.zeros(len(V), bool); used[F.ravel()] = True
    remap = -np.ones(len(V), np.int64); remap[used] = np.arange(used.sum())
    return V[used], remap[F], col[used]


def place_note13_markers(p, V, F):
    """Note-13 model layout: M1/M2 in the rim mid-plane at the side edges (M1 at -y, M2 at +y), M3 on the axis at the end;
    centres at marker_mount_height from the surface."""
    hm = p["marker_mount_height"]
    out = []
    for z, side in ((p["note13_stations"][0], -1), (p["note13_stations"][1], +1)):
        x = 0.0
        o = np.array([x, side * 0.05, z]); t, _ = ray_first_hit(o, np.array([0, -side, 0.0]), V, F)
        edge = o + t * np.array([0, -side, 0.0])
        out.append(edge + np.array([0, side * hm, 0.0]))
    out.append(np.array([0.0, 0.0, p["total_length"] + hm]))
    return np.array(out)


def build_spoon(p, res=RES):
    """Full template in the construction frame. Returns dict(V, F, col, markers, reports)."""
    p = copy.deepcopy(p)
    if p.get("end_cap_length") == "auto":
        p["end_cap_length"] = 0.5 * p["handle_d_end"]
    M, lrep = resolve_length_and_markers(p)
    V, F, binfo = body_mesh(p, res)
    col = np.tile(np.array(WOOD_RGBA, np.uint8), (len(V), 1))
    if p["marker_layout"] == "note13":
        M = place_note13_markers(p, V, F)
    mreps = []
    if p["marker_layout"] != "none":
        r_junction = p["marker_radius"] * math.sqrt(1.0 - p["marker_junction_frac"] ** 2)
        for name, c in zip(("M1", "M2", "M3"), M):
            err = None
            for scale in (1.0, 0.9, 0.8, 0.7):     # fallback: narrower stem foot on strongly curved hosts
                pk = dict(p, marker_stem_foot_radius=max(p["marker_stem_foot_radius"] * scale, r_junction + 1e-4))
                try:
                    V, F, col, rep = attach_marker(V, F, col, c, pk, res, name, (binfo["n_stations"], binfo["nphi"]))
                    rep["stem_foot_radius_mm"] = round(pk["marker_stem_foot_radius"] * 1e3, 3)
                    break
                except RuntimeError as e:
                    err = e
            else:
                raise err
            rep["name"] = name
            mreps.append(rep)
    V, F, col = remove_unreferenced(V, F, col)
    return dict(V=V, F=F, col=col, markers=M, params=p, layout_report=lrep, marker_reports=mreps, body_info=binfo)


# ----------------------------------------------------------------------------------------------------------------------
# Mesh checks
# ----------------------------------------------------------------------------------------------------------------------
def self_intersections(V, F, max_report=5):
    """Count (edge, triangle) pairs where an edge properly crosses a non-incident triangle."""
    from scipy.spatial import cKDTree
    E = np.unique(np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1), axis=0)
    T = V[F]; cen = T.mean(1)
    rad = np.linalg.norm(T - cen[:, None], axis=2).max()
    P0, P1 = V[E[:, 0]], V[E[:, 1]]
    mid = 0.5 * (P0 + P1); half = 0.5 * np.linalg.norm(P1 - P0, axis=1)
    tree = cKDTree(cen)
    lists = tree.query_ball_point(mid, half + rad + 1e-9)
    ei = np.repeat(np.arange(len(E)), [len(x) for x in lists]); ti = np.concatenate([np.asarray(x, np.int64) for x in lists])
    share = (F[ti] == E[ei, 0:1]).any(1) | (F[ti] == E[ei, 1:2]).any(1)
    ei, ti = ei[~share], ti[~share]
    o = P0[ei]; dvec = P1[ei] - P0[ei]
    A, B, C = V[F[ti, 0]], V[F[ti, 1]], V[F[ti, 2]]
    e1, e2 = B - A, C - A
    pv = np.cross(dvec, e2); det = (e1 * pv).sum(1)
    ok = np.abs(det) > 1e-20
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    sv = o - A; uu = (sv * pv).sum(1) * inv
    q = np.cross(sv, e1); vv = (dvec * q).sum(1) * inv; t = (e2 * q).sum(1) * inv
    eps = 1e-7
    hit = ok & (uu > eps) & (vv > eps) & (uu + vv < 1 - eps) & (t > eps) & (t < 1 - eps)
    return int(hit.sum()), [(int(E[a][0]), int(E[a][1]), int(b)) for a, b in zip(ei[hit][:max_report], ti[hit][:max_report])], int(len(ei))


def mesh_checks(V, F):
    nV, nF = len(V), len(F)
    de = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = de[:, 0] * (nV + 1) + de[:, 1]
    uk, cnt = np.unique(key, return_counts=True)
    rkey = de[:, 1] * (nV + 1) + de[:, 0]
    directed_once = bool((cnt == 1).all())
    has_reverse = bool(np.isin(key, rkey).all())
    ue = np.unique(np.sort(de, 1), axis=0)
    # vertex manifoldness: link of each vertex is one cycle
    link = {}
    for a, b, c in F:
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):
            link.setdefault(int(x), {})
            if int(y) in link[int(x)]:
                link[int(x)]["__dup__"] = True
            link[int(x)][int(y)] = int(z)
    vman = True
    for x, nx in link.items():
        if "__dup__" in nx:
            vman = False; break
        s0 = next(iter(nx)); cur = s0; n = 0
        while True:
            cur = nx.get(cur)
            n += 1
            if cur is None or n > len(nx):
                vman = False; break
            if cur == s0:
                break
        if not vman or n != len(nx):
            vman = False; break
    # connected components (faces via shared edges)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    fid = np.tile(np.arange(nF), 3)
    order = np.argsort(np.sort(de, 1)[:, 0] * (nV + 1) + np.sort(de, 1)[:, 1], kind="stable")
    sk = (np.sort(de, 1)[:, 0] * (nV + 1) + np.sort(de, 1)[:, 1])[order]
    same = sk[1:] == sk[:-1]
    g = coo_matrix((np.ones(same.sum()), (fid[order][1:][same], fid[order][:-1][same])), shape=(nF, nF))
    ncomp = int(connected_components(g, directed=False)[0])
    ar = tri_areas(V, F)
    T = V[F]
    def ang(a, b, c):
        u_, v_ = b - a, c - a
        return np.degrees(np.arccos(np.clip((u_ * v_).sum(1) / (np.linalg.norm(u_, axis=1) * np.linalg.norm(v_, axis=1) + 1e-300), -1, 1)))
    minang = np.minimum(np.minimum(ang(T[:, 0], T[:, 1], T[:, 2]), ang(T[:, 1], T[:, 2], T[:, 0])), ang(T[:, 2], T[:, 0], T[:, 1]))
    nsi, si_ex, npairs = self_intersections(V, F)
    euler = nV - len(ue) + nF
    return dict(
        n_vertices=int(nV), n_faces=int(nF), under_budget=bool(nV <= MESH_VERT_BUDGET and nF <= MESH_FACE_BUDGET),
        each_directed_edge_once=directed_once, every_edge_has_opposite=has_reverse,
        edge_manifold_closed=bool(directed_once and has_reverse), vertex_manifold=bool(vman),
        euler_characteristic=int(euler), genus=int((2 - euler) // 2) if ncomp == 1 else None, components=ncomp,
        signed_volume_cm3=round(signed_volume(V, F) * 1e6, 3), area_cm2=round(float(ar.sum()) * 1e4, 3),
        min_face_area_mm2=float(ar.min() * 1e6), min_angle_deg=float(minang.min()), p01_angle_deg=float(np.percentile(minang, 1)),
        self_intersections=nsi, self_intersection_pairs_tested=npairs, self_intersection_examples=si_ex,
        duplicate_faces=int(len(F) - len(np.unique(np.sort(F, 1), axis=0))),
    )


# ----------------------------------------------------------------------------------------------------------------------
# Frame rule R1 (note 13 item 2) and skews
# ----------------------------------------------------------------------------------------------------------------------
def surface_moments(V, F):
    """Exact uniform-surface (area-weighted) centroid and covariance of a triangle mesh."""
    T = V[F]
    area = tri_areas(V, F); A = area.sum()
    s = T.sum(1)
    c = (area[:, None] * s / 3.0).sum(0) / A
    M2 = (np.einsum("n,ni,nj->ij", area, T[:, 0], T[:, 0]) + np.einsum("n,ni,nj->ij", area, T[:, 1], T[:, 1])
          + np.einsum("n,ni,nj->ij", area, T[:, 2], T[:, 2]) + np.einsum("n,ni,nj->ij", area, s, s)) / 12.0 / A
    return c, M2 - np.outer(c, c), A


def skew_along(V, F, origin, axis):
    """Exact standardised third moment of the uniform surface measure along `axis` (degree-3 triangle quadrature)."""
    T = V[F]; area = tri_areas(V, F)
    f = (T - origin) @ axis
    a, b, c = f[:, 0], f[:, 1], f[:, 2]
    h3 = a ** 3 + b ** 3 + c ** 3 + a * a * b + a * a * c + b * b * a + b * b * c + c * c * a + c * c * b + a * b * c
    m3 = (area * h3 / 10.0).sum() / area.sum()
    m2 = (area * (a * a + b * b + c * c + a * b + a * c + b * c) / 6.0).sum() / area.sum()
    return float(m3 / m2 ** 1.5)


def r1_frame(V, F, rule="mid"):
    """Rule R1. rule='mid' (task / note 13 item 2): z and y by positive skew, x = y x z.
    rule='x' (note 07 variant): z and x by positive skew, y = z x x.
    Returns R (rows = canonical axes in input coords; p_canon = R (p - c)), c, eigenvalues (asc), skews (along final axes)."""
    c, C, _ = surface_moments(V, F)
    w, E = np.linalg.eigh(C)
    ex, ey, ez = E[:, 0].copy(), E[:, 1].copy(), E[:, 2].copy()
    if skew_along(V, F, c, ez) < 0:
        ez = -ez
    if rule == "mid":
        if skew_along(V, F, c, ey) < 0:
            ey = -ey
        ex = np.cross(ey, ez)
    elif rule == "x":
        if skew_along(V, F, c, ex) < 0:
            ex = -ex
        ey = np.cross(ez, ex)
    else:
        raise ValueError(rule)
    R = np.stack([ex, ey, ez])
    assert np.linalg.det(R) > 0
    sk = [skew_along(V, F, c, R[i]) for i in range(3)]
    return R, c, w, np.array(sk)


def noisy_mid_axis_PB(V, F, c, R_constr_signed, n_samples=200000, seed=0):
    """P(y bit = toward M2) if the organisers' y sign is the skew sign estimated from n surface points, with n drawn from
    the note-13 c_noisy posterior (median 5.6e3, 10-90% 1.6e3-1.8e4). R_constr_signed rows: axes signed like frame B."""
    from scipy.stats import norm
    rng = np.random.default_rng(seed)
    T = V[F]; area = tri_areas(V, F)
    idx = rng.choice(len(F), n_samples, p=area / area.sum())
    r1, r2 = rng.random(n_samples), rng.random(n_samples); m = r1 + r2 > 1; r1[m], r2[m] = 1 - r1[m], 1 - r2[m]
    P = T[idx, 0] + r1[:, None] * (T[idx, 1] - T[idx, 0]) + r2[:, None] * (T[idx, 2] - T[idx, 0])
    ey = R_constr_signed[1]
    sk = skew_along(V, F, c, ey)
    _, C, _ = surface_moments(V, F)
    sd = math.sqrt(ey @ C @ ey)
    uu = ((P - c) @ ey) / sd
    se1 = float(np.std(uu ** 3 - 3 * uu - 1.5 * sk * (uu ** 2 - 1)))
    post_f = "/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_noisy_post.npy"
    out = {"skew_toward_M2": sk, "se1": se1}
    for n in (1.6e3, 5.6e3, 1.8e4):
        out[f"P_B_at_n={int(n)}"] = float(norm.cdf(sk * math.sqrt(n) / se1))
    if os.path.exists(post_f):
        ns, post = np.load(post_f)
        out["P_B_noisy_posterior"] = float((norm.cdf(sk * np.sqrt(ns) / se1) * post).sum())
    return out


def frame_report(V, F, markers):
    """Apply R1 ('mid' and 'x' variants) to a construction-frame mesh; label the result relative to frame B."""
    rep = {}
    eye = np.eye(3)
    for rule in ("mid", "x"):
        R, c, w, sk = r1_frame(V, F, rule)
        dots = np.array([R[i] @ eye[i] for i in range(3)])     # canonical axis i vs construction axis i
        order_ok = bool(np.argmax(np.abs(R[0])) == 0 and np.argmax(np.abs(R[1])) == 1 and np.argmax(np.abs(R[2])) == 2)
        z_ok, y_ok, x_ok = dots[2] > 0, dots[1] > 0, dots[0] > 0
        label = ("B" if (y_ok and x_ok) else "A" if (not y_ok and not x_ok) else "mixed") + ("" if z_ok else "-zflip")
        if not order_ok:
            label = "axis-order-differs"
        r = dict(label=label, axis_dots_with_construction=dots.round(6).tolist(),
                 tilt_deg=[round(float(np.degrees(np.arccos(min(1.0, abs(d))))), 3) for d in dots],
                 skews_along_canonical_axes=sk.round(5).tolist(), sd_mm=(np.sqrt(w) * 1e3).round(2).tolist(),
                 origin_construction_mm=(c * 1e3).round(3).tolist())
        if markers is not None:
            Mc = (markers - c) @ R.T
            r["y_toward_M2"] = bool((Mc[1, 1] - Mc[0, 1]) > 0)
            r["markers_canonical_mm"] = (Mc * 1e3).round(2).tolist()
        rep[rule] = dict(r, R=R.tolist(), c=c.tolist())
    # skews along the construction-signed PCA axes (frame-B signs): >0 means the tail points that way
    R, c, w, _ = r1_frame(V, F, "mid")
    Rs = R * np.sign(np.array([R[i, i] for i in range(3)]))[:, None]
    rep["skew_toward_concave_x"] = round(skew_along(V, F, c, Rs[0]), 5)
    rep["skew_toward_M2_y"] = round(skew_along(V, F, c, Rs[1]), 5)
    rep["skew_toward_handle_z"] = round(skew_along(V, F, c, Rs[2]), 5)
    rep["noisy_mid_axis"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in noisy_mid_axis_PB(V, F, c, Rs).items()}
    return rep


# ----------------------------------------------------------------------------------------------------------------------
# Dimensions, inertia, export
# ----------------------------------------------------------------------------------------------------------------------
def dimensions(build):
    p = build["params"]; V = build["V"]; F = build["F"]
    prof = build["body_info"]["prof"]
    s, w, hv = prof["s"], prof["w"], prof["hv"]
    body = np.arange(len(V))[np.all(build["col"] == np.array(WOOD_RGBA, np.uint8), axis=1)]
    Vb = V[body]
    neck_zone = (s > p["bowl_length"]) & (s < p["handle_station"])
    out = dict(
        wood_length_mm=round(float(Vb[:, 2].max() - Vb[:, 2].min()) * 1e3, 2),
        overall_extent_with_markers_mm=((V.max(0) - V.min(0)) * 1e3).round(2).tolist(),
        bowl_length_mm=round(p["bowl_length"] * 1e3, 2),
        bowl_max_width_mm=round(float(2 * w[s < p["bowl_length"]].max()) * 1e3, 2),
        bowl_inner_depth_mm=round(float(p["bowl_depth"]) * 1e3, 2),
        bowl_wall_thickness_mm=round(p["bowl_thickness"] * 1e3, 2),
        rim_top_above_axis_mm=round((p["rim_height"] + 0.5 * p["bowl_thickness"]) * 1e3, 2),
        bowl_back_lowest_mm=round(float(Vb[Vb[:, 2] < p["bowl_length"], 0].min()) * 1e3, 2),
        neck_min_width_mm=round(float(2 * w[neck_zone].min()) * 1e3, 2),
        handle_diameter_mm={f"{si*1e3:.0f}": round(float(2 * wi) * 1e3, 2) for si, wi in zip(s, w) if p["handle_station"] - 1e-9 <= si <= p["total_length"] - p["end_cap_length"] + 1e-9},
        handle_max_diameter_mm=round(float(2 * w[s > p["handle_station"]].max()) * 1e3, 2),
    )
    return out


def surface_inertia(V, F, mass):
    """Uniform triangle-surface inertia about the surface centroid (as in the public URDFs)."""
    c, C, _ = surface_moments(V, F)
    I = mass * (np.trace(C) * np.eye(3) - C)
    return c, I


def write_obj(path, V, F, col, header):
    with open(path, "w") as f:
        for h in header:
            f.write(f"# {h}\n")
        cf = col[:, :3] / 255.0
        for v, cc in zip(V, cf):
            f.write(f"v {v[0]:.9f} {v[1]:.9f} {v[2]:.9f} {cc[0]:.4f} {cc[1]:.4f} {cc[2]:.4f}\n")
        for t in F + 1:
            f.write(f"f {t[0]} {t[1]} {t[2]}\n")


def _glb_postprocess(path, mesh_name="wooden_spoon"):
    """Mirror the public scans' node layout: root node 'world' -> one mesh node, no transforms."""
    try:
        import pygltflib
    except ImportError:
        return False
    g = pygltflib.GLTF2().load(path)
    if not any(n.name == "world" for n in g.nodes):
        mesh_nodes = [i for i, n in enumerate(g.nodes) if n.mesh is not None]
        assert len(g.nodes) == 1 and mesh_nodes == [0]
        g.nodes[0].name = mesh_name
        g.nodes = [pygltflib.Node(name="world", children=[1]), g.nodes[0]]
        g.scenes[0].nodes = [0]
        g.scene = 0
    for m in g.meshes:
        m.name = mesh_name
    g.save_binary(path)
    return True


PALETTE = [WOOD_RGBA, STEM_RGBA, SPHERE_RGBA]


def texture_atlas(col, block=16):
    """Tiny texture atlas (one uniform block per colour, wood|black|grey so blended UVs only cross neighbours) and
    per-vertex UVs at block centres. Mirrors the public scans' textured material (TEXCOORD_0 + PNG baseColorTexture)."""
    from PIL import Image
    img = np.zeros((block, block * len(PALETTE), 3), np.uint8)
    for k, c in enumerate(PALETTE):
        img[:, k * block:(k + 1) * block] = c[:3]
    kidx = np.zeros(len(col), np.int64)
    for k, c in enumerate(PALETTE):
        kidx[(col[:, :3] == np.array(c[:3])).all(1)] = k
    uv = np.stack([(kidx + 0.5) / len(PALETTE), np.full(len(col), 0.5)], 1)
    return Image.fromarray(img), uv


def write_glb(path, V, F, col):
    import trimesh
    img, uv = texture_atlas(col)
    mat = trimesh.visual.material.PBRMaterial(name="_texture", baseColorTexture=img, baseColorFactor=[255, 255, 255, 255],
                                              metallicFactor=0.0, roughnessFactor=1.0, doubleSided=True)
    tm = trimesh.Trimesh(vertices=V.astype(np.float64), faces=F, process=False, validate=False)
    tm.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
    tm.export(path, file_type="glb")
    post = _glb_postprocess(path)
    back = trimesh.load(path, force="mesh", process=False)
    same = (len(back.vertices) == len(V) and len(back.faces) == len(F)
            and np.abs(np.asarray(back.vertices) - V.astype(np.float32)).max() < 1e-6 and (np.asarray(back.faces) == F).all())
    tex_ok = False
    if back.visual.kind == "texture" and back.visual.material.baseColorTexture is not None:
        im = np.asarray(back.visual.material.baseColorTexture.convert("RGB"))
        h, w = im.shape[:2]
        buv = np.asarray(back.visual.uv)
        px = im[np.clip(((1 - buv[:, 1]) * h).astype(int), 0, h - 1), np.clip((buv[:, 0] * w).astype(int), 0, w - 1)]
        tex_ok = bool((px == col[:, :3]).all())
    return dict(reload_identical=bool(same), texture_colours_match=tex_ok, visual_kind=back.visual.kind, postprocessed=bool(post),
                reload_watertight=bool(back.is_watertight), reload_winding_consistent=bool(back.is_winding_consistent),
                bytes=os.path.getsize(path))


def glb_structure(path):
    try:
        import pygltflib
    except ImportError:
        return None
    g = pygltflib.GLTF2().load(path)
    return dict(nodes=[dict(name=n.name, mesh=n.mesh, children=n.children, matrix=n.matrix, translation=n.translation,
                            rotation=n.rotation, scale=n.scale) for n in g.nodes], scene_roots=g.scenes[g.scene or 0].nodes,
                meshes=len(g.meshes), primitives=len(g.meshes[0].primitives),
                material=None if not g.materials else dict(name=g.materials[0].name, metallic=g.materials[0].pbrMetallicRoughness.metallicFactor,
                                                           roughness=g.materials[0].pbrMetallicRoughness.roughnessFactor,
                                                           texture=g.materials[0].pbrMetallicRoughness.baseColorTexture is not None,
                                                           doubleSided=g.materials[0].doubleSided),
                generator=g.asset.generator, attributes=[k for k, v in g.meshes[0].primitives[0].attributes.__dict__.items() if v is not None])


URDF_TMPL = """<?xml version="1.0"?>
<robot name="track3_wooden_spoon">
  <!-- Track 3 supplies no measured physical properties. 0.3 kg is a placeholder mass; COM/inertia are a uniform triangle-surface estimate over the collision mesh. -->
  <!-- wooden_spoon: own parametric reconstruction (no public scan); see colab/spoon/README.md. -->
  <mujoco><compiler balanceinertia="true" discardvisual="false"/></mujoco>
  <link name="object">
    <inertial>
      <origin xyz="{ox} {oy} {oz}" rpy="0 0 0"/>
      <mass value="{mass}"/>
      <inertia ixx="{ixx}" ixy="{ixy}" ixz="{ixz}" iyy="{iyy}" iyz="{iyz}" izz="{izz}"/>
    </inertial>
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="../mesh/wooden_spoon/wooden_spoon.glb" scale="1 1 1"/></geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="../mesh/wooden_spoon/wooden_spoon.glb" scale="1 1 1"/></geometry>
    </collision>
  </link>
</robot>
"""


def fmt_num(x, scale_ref, zero_rel=1e-9):
    if abs(x) < zero_rel * scale_ref:
        return "0"
    return f"{x:.15g}"


def write_urdf(path, V, F, mass=0.3):
    c, I = surface_inertia(V, F, mass)
    ref = float(np.abs(np.diag(I)).max())
    vals = dict(ox=fmt_num(c[0], 1.0, 1e-12), oy=fmt_num(c[1], 1.0, 1e-12), oz=fmt_num(c[2], 1.0, 1e-12), mass=f"{mass:g}",
                ixx=fmt_num(I[0, 0], ref), ixy=fmt_num(I[0, 1], ref), ixz=fmt_num(I[0, 2], ref),
                iyy=fmt_num(I[1, 1], ref), iyz=fmt_num(I[1, 2], ref), izz=fmt_num(I[2, 2], ref))
    with open(path, "w") as f:
        f.write(URDF_TMPL.format(**vals))
    return dict(centroid=c.tolist(), inertia=I.tolist())


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


# ----------------------------------------------------------------------------------------------------------------------
# Variants for the frame-sensitivity table
# ----------------------------------------------------------------------------------------------------------------------
VARIANTS = {
    "default (note-20 layout, bend 1.3 mm)": {},
    "bend 0": {"bowl_bend": 0.0},
    "bend 2.8 mm (note-20 upper)": {"bowl_bend": 0.0028},
    "M2 lat 16.6 (asym -1.1 mm)": {"m_lat2": [16.6, 0.4]},
    "M2 lat 14.4 (asym +1.1 mm)": {"m_lat2": [14.4, 0.4]},
    "note-13 in-plane layout, bend 0": {"marker_layout": "note13", "bowl_bend": 0.0},
    "no markers, bend 1.3": {"marker_layout": "none"},
    "no markers, bend 0 (tessellation floor)": {"marker_layout": "none", "bowl_bend": 0.0},
    "bowl depth 6 mm": {"bowl_depth": 0.006},
    "bowl depth 14 mm": {"bowl_depth": 0.014},
    "oval handle+neck (aspect 0.8)": {"handle_aspect": 0.8, "neck_aspect": 0.8},
    "rim 4 mm above axis": {"rim_height": 0.004},
}


def run_variants(base_user, res=RES):
    rows = []
    for name, ov in VARIANTS.items():
        u = dict(base_user or {}); u.update(ov)
        try:
            b = build_spoon(resolve_params(u), res)
            fr = frame_report(b["V"], b["F"], b["markers"])
            ck = mesh_checks(b["V"], b["F"])
            rows.append(dict(variant=name, label_mid=fr["mid"]["label"], label_x=fr["x"]["label"],
                             skew_x_concave=fr["skew_toward_concave_x"], skew_y_M2=fr["skew_toward_M2_y"],
                             skew_z_handle=fr["skew_toward_handle_z"],
                             P_B_noisy=fr["noisy_mid_axis"].get("P_B_noisy_posterior"),
                             faces=ck["n_faces"], manifold=ck["edge_manifold_closed"] and ck["vertex_manifold"] and ck["self_intersections"] == 0))
        except Exception as e:  # keep going; report
            rows.append(dict(variant=name, error=f"{type(e).__name__}: {e}"))
        print("  variant:", rows[-1], flush=True)
    return rows


# ----------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--params", default=None, help="JSON file with parameter overrides")
    ap.add_argument("--variants", action="store_true", help="run the frame-sensitivity variants")
    ap.add_argument("--frame", choices=["rule", "B"], default="rule",
                    help="'rule' (default): canonical frame = R1 result; 'B': force frame B (NOT the default; reported)")
    args = ap.parse_args()
    user = json.load(open(args.params)) if args.params else {}
    p = resolve_params(user)
    print("building template ...", flush=True)
    b = build_spoon(p)
    V, F, col, M = b["V"], b["F"], b["col"], b["markers"]
    checks = mesh_checks(V, F)
    print("checks:", json.dumps(checks), flush=True)
    fr = frame_report(V, F, M)
    print("frame (mid rule):", fr["mid"]["label"], "skews x/y/z (construction-signed):",
          fr["skew_toward_concave_x"], fr["skew_toward_M2_y"], fr["skew_toward_handle_z"], flush=True)
    # canonicalise
    R = np.array(fr["mid"]["R"]); c = np.array(fr["mid"]["c"])
    forced = False
    if args.frame == "B" and fr["mid"]["label"] != "B":
        sgn = np.sign(np.array([R[i, i] for i in range(3)]))
        R = R * sgn[:, None]; forced = True
    Vc = (V - c) @ R.T
    Mc = None if M is None else (M - c) @ R.T
    # idempotence on the exported (float32) geometry
    R2, c2, _, sk2 = r1_frame(Vc.astype(np.float32).astype(np.float64), F, "mid")
    idem = dict(origin_mm=float(np.linalg.norm(c2) * 1e3), max_axis_dev_deg=float(np.degrees(np.arccos(np.clip(np.diag(R2), -1, 1))).max()),
                diag_signs=np.sign(np.diag(R2)).astype(int).tolist(), skews=sk2.round(5).tolist())
    os.makedirs(args.out, exist_ok=True)
    glb = os.path.join(args.out, "wooden_spoon.glb")
    obj = os.path.join(args.out, "wooden_spoon.obj")
    urdf = os.path.join(args.out, "wooden_spoon_rigid.urdf")
    glbrep = write_glb(glb, Vc, F, col)
    glbrep["structure"] = glb_structure(glb)
    write_obj(obj, Vc, F, col, ["wooden_spoon parametric template (colab/spoon/spoon_template.py)",
                                f"canonical frame: R1 rule '{'forced B' if forced else 'mid'}' ({fr['mid']['label']}); metres",
                                "vertex colours: wood / black stem / grey marker sphere"])
    urep = write_urdf(urdf, Vc, F)
    dims = dimensions(b)
    out = dict(
        generator="colab/spoon/spoon_template.py", date="2026-10-13",
        params=_jsonable(b["params"]), resolution=RES,
        marker_layout_report=_jsonable(b["layout_report"]), marker_reports=_jsonable(b["marker_reports"]),
        markers_construction_m=None if M is None else M.tolist(), markers_canonical_m=None if Mc is None else Mc.tolist(),
        marker_triangle_mm=None if M is None else [round(float(np.linalg.norm(M[a] - M[b_])) * 1e3, 3) for a, b_ in ((0, 1), (1, 2), (0, 2))],
        construction_frame="x = out of the concave face, y = z x x (toward M2), z = bowl tip -> handle end; origin = bowl tip on the handle axis",
        canonical_from_construction=dict(R=R.tolist(), c=c.tolist(), note="p_canonical = R @ (p_construction - c)", forced_B=forced),
        frame_check=_jsonable({k: v for k, v in fr.items()}), idempotence_on_export=idem,
        mesh_checks=_jsonable(checks), dimensions=dims, glb=_jsonable(glbrep), urdf_inertial=_jsonable(urep),
    )
    if args.variants:
        print("variants ...", flush=True)
        out["variants"] = run_variants(user)
    with open(os.path.join(args.out, "params.json"), "w") as f:
        json.dump(_jsonable(out), f, indent=1)
    print("wrote", glb, obj, urdf, os.path.join(args.out, "params.json"), flush=True)
    print("dims:", json.dumps(dims), flush=True)
    print("idempotence:", idem, flush=True)
    ok = checks["edge_manifold_closed"] and checks["vertex_manifold"] and checks["self_intersections"] == 0 \
        and checks["components"] == 1 and checks["under_budget"] and checks["duplicate_faces"] == 0
    print("ALL MESH CHECKS PASS" if ok else "MESH CHECK FAILURE", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
