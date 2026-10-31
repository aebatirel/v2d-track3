"""Board slot under the owner's waiver of the camera rule (PREREG F-I4, INTERLOCK.md section 20).

New code path only. interlock.decide_pair(..., waiver_fi4=True) calls apply_waiver() after the F-I1..F-I3 decisions
of the pair; with the flag off nothing here runs and every earlier decision is unchanged (F-I4.10 w2). One branch for
both paths (our tracks and an Embodiment export, F-I3.1): it reads only the Side objects decide_pair already has.

Owner, 31 Oct ~16:00 UTC: "Okay I waive that camera rule" (F-I4.0). Scope: a linked pair whose two targets are
plate-like (F-I4.1) and whose two linked components come from INSERTION runs. In scope, class O and an absent or
failing silhouette no longer block the carve; every other gate stays.

  plate_info(b, obj, mesh)            F-I4.1 plane-pair test (structure._points / _planes: the B7 code) on the object's
                                      owned points within 6 mm of its pick; plate pair = largest footprint overlap
                                      (ties: more inliers); thickness t and the mid plane
  plate_body(b, obj, info)            F-I4.2 extrusion of the observed outline (min-area rectangle, fill >= 0.9) at t;
                                      no marker balls (flag plate_body_no_markers); a STRUCT plate candidate is not
                                      built in this repository yet (none exists for ep24)
  slot_for(...)                       F-I4.3 analytic slot of one target: width t_p + 2 mm along a_L, centre = the
                                      linked component's voxel centroid along a_L, entry edge on the -d side, depth
                                      D = P + 2 mm (P = 99th percentile penetration in R, capped at the shared split)
  crossing_extent(...)                F-I4.3 W_x: extent along d of the two unslotted bodies' intersection (2 mm grid)
  slot_budget(...)                    F-I4.4 volume share <= 10 %, reach <= 0.6, D < W_o and both prongs positive
  pieces(body, slot)                  F-I4.6 three boxes sharing faces (+ one hull per marker ball); default = the body
  keepout_gate(...)                   F-I4.6 / F-I3.8 keep-out per hull (<= 0.3 cm3), no splitter, no CoACD
  apply_waiver(b, so, sp, recs, links)  F-I4.0 scope, kept gates, records (flag owner_waiver_fi4, tier T1)
  acceptance(phys, gates, shapes)     F-I4.7 P2-P7 + keep-out (P1 = the Embodiment's jitter_check --k 16)
GT-free: owned points, grids, tracks of our bundle and our pick only (F-I4.9).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

from gmg import guard, interlock as IL

WAIVER_QUOTE = 'Okay I waive that camera rule'
WAIVER_REF = ('PREREG F-I4 (c13f53c); owner, session_01W8Softjo2xx7o6ofSiheuQ, 31 Oct ~16:00 UTC: "' + WAIVER_QUOTE +
              '"')

# name: (value, origin) -- PREREG F-I4.11
C = dict(
    near_m=(0.006, 'generic:F-I2.10 owned points within 6 mm of the pick'),
    depth_margin_m=(0.002, 'generic:F-I4.11 depth margin 2.0 mm at the slot bottom'),
    consist_m=(0.010, 'generic:F-I4.11 cross-lap consistency window 10 mm (= K-c)'),
    raster_m=(0.002, 'generic:F-I4.11 outline raster 2 mm (= the carve sub-grid)'),
    frames_min=(3, 'generic:F-I4.11 >= 3 frames per outline cell (= OBSERVED hits >= 3, A.6)'),
    slab_sigma=(3.0, 'generic:F-I4.11 outline slab margin 3 sigma (A.6 noise band)'),
    fill_min=(0.9, 'generic:F-I4.11 rectangle fill share 0.9'),
    extend_m=(0.003, 'generic:carve_solid 3 mm extension past the entry edge and the faces'),
    grid_m=(0.002, 'generic:F-I4.3 W_x on a 2 mm grid'),
    ball_subdiv=(1, 'generic:icosphere subdivision 1 (42 vertices <= 64)'),
)


def k_(name):
    v, o = C[name]
    guard.constant(f'pb.{name}', v, o)
    return v


# ------------------------------------------------------------------------------------------------ F-I4.1 plate test
def _near_points(b, obj, mesh):
    """Owned points (own == 0, finite) of OBJ within 6 mm of the pick's surface: (pts, cam, frame)."""
    ob = b.obs(obj)
    P = np.asarray(ob['pts'], np.float64)
    Cm = np.asarray(ob['cam'], np.float64)
    fr = np.asarray(ob['frame'])
    own = np.asarray(ob.get('own', np.zeros(len(P), np.uint8)))
    ok = (own == 0) & np.all(np.isfinite(P), 1) & np.all(np.isfinite(Cm), 1)
    P, Cm, fr = P[ok], Cm[ok], fr[ok]
    near = k_('near_m')
    # cheap pre-filter: outside the pick's box grown by 6 mm, a point is farther than 6 mm from its surface
    lo, hi = np.asarray(mesh.bounds[0]) - near, np.asarray(mesh.bounds[1]) + near
    inb = np.all((P >= lo) & (P <= hi), axis=1)
    P, Cm, fr = P[inb], Cm[inb], fr[inb]
    d = np.full(len(P), np.inf)
    cl = IL.geom.Closest(mesh)
    for i in range(0, len(P), 400000):
        d[i:i + 400000] = cl.query(P[i:i + 400000])[0]
    k = d <= near
    return P[k], Cm[k], fr[k], dict(owned=int(ok.sum()), in_box=int(inb.sum()), within_6mm=int(k.sum()))


def plate_info(b, obj, mesh):
    """F-I4.1: the structure plane-pair test (structure._points + structure._planes, the B7 code path) on OBJ's owned
    points within 6 mm of its pick. Returns dict(plate bool, t_m, mid_n, mid_d, pair, pairs, planes summary, points)."""
    from gmg import structure as ST
    import time
    t0 = time.time()
    P, Cm, fr, cnt = _near_points(b, obj, mesh)
    sigma = b.sigma(obj)
    K = ST.consts()
    out = dict(obj=obj, sigma_mm=round(sigma * 1e3, 3), points=cnt, plate=False)
    obs = dict(pts=P, cam=Cm, own=np.zeros(len(P), np.uint8))
    Pd, Cd, n_raw = ST._points(obs, K, np.random.default_rng(0))
    out['n_down'] = int(len(Pd))
    if len(Pd) < max(K['plane_min'], 500):
        out.update(why='too_few_points', sec=round(time.time() - t0, 1))
        return out
    planes, pairs, sinfo = ST._planes(Pd, Cd, sigma, K)
    out['planes'] = [dict(n=np.round(p['n'], 4).tolist(), n_pts=p['n_pts'], rms_mm=p['rms_mm']) for p in planes]
    out['pairs'] = pairs
    if not pairs:
        out.update(why='no_plane_pair', sec=round(time.time() - t0, 1))
        return out
    best = max(pairs, key=lambda q: (q['overlap'], planes[q['faces'][0]]['n_pts'] + planes[q['faces'][1]]['n_pts']))
    mid_n = np.asarray(best['mid_n'], np.float64)
    out.update(plate=True, pair=best, t_m=float(best['thickness_mm']) * 1e-3, mid_n=mid_n.tolist(),
               mid_d=float(best['mid_d']), sec=round(time.time() - t0, 1))
    out['_P'], out['_F'] = P, fr
    out['_e1'] = np.asarray(planes[best['faces'][0]]['e1'], np.float64)
    return out


# ------------------------------------------------------------------------------------------------ F-I4.2 plate body
def _min_area_rect(Q):
    """Minimum-area rectangle of 2-D points Q (rotating calipers over the convex hull edges): (centre (2,), axes 2x2
    rows (long, short), lengths (long, short))."""
    h = ConvexHull(Q)
    H = Q[h.vertices]
    best = None
    for i in range(len(H)):
        e = H[(i + 1) % len(H)] - H[i]
        n = np.linalg.norm(e)
        if n < 1e-12:
            continue
        u = e / n
        v = np.array([-u[1], u[0]])
        a, c = H @ u, H @ v
        area = (a.max() - a.min()) * (c.max() - c.min())
        if best is None or area < best[0]:
            best = (area, u, v, a.min(), a.max(), c.min(), c.max())
    _, u, v, a0, a1, c0, c1 = best
    cen = u * 0.5 * (a0 + a1) + v * 0.5 * (c0 + c1)
    la, lc = a1 - a0, c1 - c0
    if la >= lc:
        return cen, np.stack([u, v]), (la, lc)
    return cen, np.stack([v, u]), (lc, la)


def plate_body(b, obj, info):
    """F-I4.2 for a target without a STRUCT plate candidate: the observed outline (F-I4.1 points within t/2 + 3 sigma of
    the mid plane, 2 mm raster, cells with points of >= 3 frames, one 3 x 3 closing, holes filled, largest
    8-connected component) replaced by its minimum-area rectangle (over the cell corners) and extruded to t about the
    mid plane. Returns dict(ok, box dict(axes rows [a_L, a_W, a_T], centre, half), L, W, t, fill, balls [], flags)."""
    P, F = info['_P'], info['_F']
    n = np.asarray(info['mid_n'], np.float64); n /= np.linalg.norm(n)
    t = float(info['t_m']); sig = b.sigma(obj)
    s = P @ n - info['mid_d']
    k = np.abs(s) <= t / 2 + k_('slab_sigma') * sig
    e1 = info['_e1'] - (info['_e1'] @ n) * n
    e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    o0 = n * info['mid_d']
    U = np.stack([(P[k] - o0) @ e1, (P[k] - o0) @ e2], 1)
    fr = F[k]
    r = k_('raster_m')
    ij = np.floor(U / r).astype(np.int64)
    lo = ij.min(0)
    ij -= lo
    shp = ij.max(0) + 1
    key = np.unique(np.stack([ij[:, 0], ij[:, 1], fr.astype(np.int64)], 1), axis=0)
    cnt = np.zeros(shp, np.int32)
    np.add.at(cnt, (key[:, 0], key[:, 1]), 1)
    M = cnt >= k_('frames_min')
    M = ndimage.binary_closing(np.pad(M, 2), structure=np.ones((3, 3)))[2:-2, 2:-2]
    M = ndimage.binary_fill_holes(M)
    lab, nl = ndimage.label(M, structure=np.ones((3, 3)))
    out = dict(obj=obj, points_in_slab=int(k.sum()), cells=int(M.sum()), flags=['plate_body_no_markers'], balls=[],
               source='observed outline (no STRUCT plate candidate)')
    if nl == 0:
        out.update(ok=False, why='empty_outline')
        return out
    big = int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
    comp = lab == big
    ci = np.argwhere(comp)
    corners = (np.concatenate([ci + np.array([a, c]) for a in (0, 1) for c in (0, 1)]) + lo) * r
    cen2, A2, (Lr, Wr) = _min_area_rect(corners.astype(np.float64))
    fill = float(comp.sum()) * r * r / max(Lr * Wr, 1e-12)
    aL = A2[0, 0] * e1 + A2[0, 1] * e2
    aL /= np.linalg.norm(aL)
    aW = np.cross(n, aL)
    centre = o0 + cen2[0] * e1 + cen2[1] * e2
    box = dict(axes=np.stack([aL, aW, n]).tolist(), centre=centre.tolist(), half=[Lr / 2, Wr / 2, t / 2])
    out.update(ok=bool(fill >= k_('fill_min')), box=box, L_mm=round(Lr * 1e3, 1), W_mm=round(Wr * 1e3, 1),
               t_mm=round(t * 1e3, 2), fill=round(fill, 3), component_cells=int(comp.sum()),
               volume_cm3=round(Lr * Wr * t * 1e6, 2))
    if not out['ok']:
        out['why'] = 'plate_outline_not_rectangular'
    return out


# ------------------------------------------------------------------------------------------------ boxes
def box_vertices(box):
    A = np.asarray(box['axes'], np.float64); c = np.asarray(box['centre'], np.float64)
    h = np.asarray(box['half'], np.float64)
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float64)
    return c + (s * h) @ A


def in_box(box, X):
    A = np.asarray(box['axes'], np.float64); c = np.asarray(box['centre'], np.float64)
    h = np.asarray(box['half'], np.float64)
    return np.all(np.abs((np.asarray(X, np.float64) - c) @ A.T) <= h + 1e-12, axis=1)


def _sub_box(body, l_rng, w_rng, t_rng):
    """Box with the body's axes spanning [l0, l1] x [w0, w1] x [t0, t1] in the body's local coordinates."""
    A = np.asarray(body['axes'], np.float64); c = np.asarray(body['centre'], np.float64)
    lo = np.array([min(l_rng), min(w_rng), min(t_rng)]); hi = np.array([max(l_rng), max(w_rng), max(t_rng)])
    mid = 0.5 * (lo + hi)
    return dict(axes=A.tolist(), centre=(c + mid @ A).tolist(), half=(0.5 * (hi - lo)).tolist())


# ------------------------------------------------------------------------------------------------ F-I4.3 slot
def _split_cap(comp, body, c_L, u_e, s_e):
    """Depth (from the entry edge, along -s_e a_W, on the slot centre line in the mid plane) of the pair's shared split
    plane when the through-column split applied; None otherwise."""
    sp = comp.split or {}
    if not sp.get('through_column') or sp.get('plane_point') is None:
        return None, dict(applied=False)
    A = np.asarray(body['axes'], np.float64); c0 = np.asarray(body['centre'], np.float64)
    aL, aW = A[0], A[1]
    pc = np.asarray(sp['plane_point'], np.float64); nn = np.asarray(sp['plane_normal'], np.float64)
    nn /= np.linalg.norm(nn)
    sign = +1 if str(sp.get('carve_side', '')).startswith('entry (s < 0)') else -1
    q0 = c0 + c_L * aL + u_e * aW
    f0 = float((q0 - pc) @ nn)
    den = float(s_e * (aW @ nn))
    info = dict(applied=True, shared=bool(sp.get('shared')), carve_sign=sign,
                entry_edge_on_carve_side=bool((f0 < 0) if sign > 0 else (f0 > 0)),
                plane_vs_aW_cos=round(abs(float(aW @ nn)), 4))
    if abs(den) < 1e-9:
        info['why'] = 'split plane parallel to a_W: no cap'
        return None, info
    s_star = f0 / den
    info['raw_depth_mm'] = round(s_star * 1e3, 2)
    return float(np.clip(s_star, 0.0, 2 * float(body['half'][1]))), info


def slot_for(side, comp, R_lin, body, t_partner, run, partner_plane=None):
    """F-I4.3 for one target (in its frame). Returns dict(ok, box, w, c_L, D, P, entry sign, ...).
    PARTNER_PLANE = (n', d'): the partner's plate mid plane (F-I4.1) mapped into this target's frame by the median
    assembled relative pose; F-I4.12 (post hoc, after the synthetic w1 miss): the slot centre c_L is where that plane
    crosses the slot's centre line (o's mid plane, middle of the slot's depth range); the component's voxel centroid
    of F-I4.3 is reported as c_L_component and used for the split cap and as the fallback."""
    A = np.asarray(body['axes'], np.float64); c0 = np.asarray(body['centre'], np.float64)
    aL, aW, aT = A
    L, W, t = 2 * np.asarray(body['half'], np.float64)
    d = np.asarray(run.d, np.float64); d = d / np.linalg.norm(d)
    w = float(t_partner) + 2 * IL.K('clearance_m')
    C = side.ev.grid.centres(comp.lin)                    # the linked persistent component, before the split
    c_L = float(np.mean((C - c0) @ aL))
    s_e = -1.0 if float(d @ aW) > 0 else 1.0             # entry edge on the -d side
    u_e = s_e * W / 2
    fr_asm = [f for f in (run.assembled or run.build) if f in run.build] or run.build
    sel = np.isin(side.intr.frame, fr_asm) & np.isin(side.intr.lin, R_lin)
    X = side.intr.pts[sel]
    out = dict(w_mm=round(w * 1e3, 2), t_partner_mm=round(t_partner * 1e3, 2), c_L_mm=round(c_L * 1e3, 2),
               entry_sign_aW=int(s_e), d_dot_aW=round(float(d @ aW), 4),
               angle_d_aW_deg=round(math.degrees(math.acos(min(1.0, abs(float(d @ aW))))), 2),
               samples=int(len(X)), assembled_build_frames=len(fr_asm))
    if len(X) == 0:
        out.update(ok=False, why='slot_depth_no_samples')
        return out
    depth = W / 2 - s_e * ((X - c0) @ aW)
    P99 = float(np.percentile(depth, 99))
    cap, cinfo = _split_cap(comp, body, c_L, u_e, s_e)
    P = min(P99, cap) if cap is not None else P99
    D = P + k_('depth_margin_m')
    ext = k_('extend_m')
    out['c_L_component_mm'] = round(c_L * 1e3, 2)
    out['centre_from'] = 'component voxel centroid (F-I4.3)'
    if partner_plane is not None:                         # F-I4.12
        n_, d_ = np.asarray(partner_plane[0], np.float64), float(partner_plane[1])
        den = float(n_ @ aL)
        if abs(den) >= 1e-6:
            x0 = c0 + (u_e - s_e * D / 2) * aW
            c_L = float((d_ - n_ @ x0) / den)
            out['centre_from'] = "partner's plate mid plane at the median assembled pose (F-I4.12)"
        else:
            out['centre_from'] = 'component voxel centroid (F-I4.12 fallback: partner normal perpendicular to a_L)'
        out['c_L_mm'] = round(c_L * 1e3, 2)
        out['c_L_shift_mm'] = round((c_L - float(out['c_L_component_mm']) * 1e-3) * 1e3, 2)
    lo_w, hi_w = sorted([u_e + s_e * ext, u_e - s_e * D])
    box = _sub_box(body, (c_L - w / 2, c_L + w / 2), (lo_w, hi_w), (-(t / 2 + ext), t / 2 + ext))
    out.update(ok=True, P99_mm=round(P99 * 1e3, 2), cap_mm=None if cap is None else round(cap * 1e3, 2),
               split=cinfo, P_mm=round(P * 1e3, 2), D_mm=round(D * 1e3, 2), box=box,
               depth_is='prior [E] (split share of the constrained depth sum)' if cap is not None else
               'measured 99th percentile [M]')
    out['_w'], out['_c_L'], out['_D'], out['_s_e'], out['_u_e'] = w, c_L, D, s_e, u_e
    return out


def crossing_extent(body_o, body_p, T_op, d_o):
    """F-I4.3 W_x: 2 mm grid points inside o's unslotted body that lie inside p's (mapped by T_op = T_{o<-p}); extent
    along d_o (max - min + one pitch). Returns (W_x m, n points)."""
    g = k_('grid_m')
    A = np.asarray(body_o['axes'], np.float64); c = np.asarray(body_o['centre'], np.float64)
    h = np.asarray(body_o['half'], np.float64)
    ax = [np.arange(-h[i] + g / 2, h[i], g) for i in range(3)]
    Q = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    X = c + Q @ A
    Ti = np.linalg.inv(T_op)
    Xp = X @ Ti[:3, :3].T + Ti[:3, 3]
    k = in_box(body_p, Xp)
    if not k.any():
        return 0.0, 0
    s = X[k] @ (np.asarray(d_o, np.float64) / np.linalg.norm(d_o))
    return float(s.max() - s.min() + g), int(k.sum())


def slot_budget(side, body, slot, d, carved_before_cm3=0.0):
    """F-I4.4: (slot box intersected with the body) <= 10 % of the round-0 body (cumulative), reach along d <= 0.6 of
    the body's extent along d, D < W_o and both prongs of positive length along a_L."""
    A = np.asarray(body['axes'], np.float64)
    L, W, t = 2 * np.asarray(body['half'], np.float64)
    d = np.asarray(d, np.float64); d = d / np.linalg.norm(d)
    w, c_L, D = slot['_w'], slot['_c_L'], slot['_D']
    w_in = max(0.0, min(c_L + w / 2, L / 2) - max(c_L - w / 2, -L / 2))
    D_in = min(D, W)
    vol = w_in * D_in * t
    body_vol = L * W * t
    share = (carved_before_cm3 * 1e-6 + vol) / body_vol
    ext_slot = w_in * abs(d @ A[0]) + D_in * abs(d @ A[1]) + t * abs(d @ A[2])
    ext_body = L * abs(d @ A[0]) + W * abs(d @ A[1]) + t * abs(d @ A[2])
    reach = ext_slot / max(ext_body, 1e-12)
    prong_lo = (c_L - w / 2) + L / 2
    prong_hi = L / 2 - (c_L + w / 2)
    topo = bool(D < W and prong_lo > 0 and prong_hi > 0)
    ok = bool(share <= IL.K('budget_vol') and reach <= IL.K('budget_reach') and topo)
    return dict(slot_cm3=round(vol * 1e6, 3), body_cm3=round(body_vol * 1e6, 2), vol_share=round(share, 4),
                reach=round(reach, 3), D_lt_W=bool(D < W), prong_mm=[round(prong_lo * 1e3, 1), round(prong_hi * 1e3, 1)],
                topology=topo, ok=ok, _vol=vol)


# ------------------------------------------------------------------------------------------------ F-I4.6 pieces
def pieces(body, slot=None):
    """Slotted body = three boxes sharing faces (solid part, two prongs) + one icosphere hull per marker ball; default
    (slot None) = the body box + the balls. Returns (list of vertex arrays, list of box dicts)."""
    import trimesh
    L, W, t = 2 * np.asarray(body['half'], np.float64)
    if slot is None:
        boxes = [body]
    else:
        w, c_L, D, s_e, u_e = slot['_w'], slot['_c_L'], slot['_D'], slot['_s_e'], slot['_u_e']
        bot = u_e - s_e * D
        far = -u_e
        boxes = [_sub_box(body, (-L / 2, L / 2), (bot, far), (-t / 2, t / 2)),
                 _sub_box(body, (-L / 2, c_L - w / 2), (u_e, bot), (-t / 2, t / 2)),
                 _sub_box(body, (c_L + w / 2, L / 2), (u_e, bot), (-t / 2, t / 2))]
    hulls = [box_vertices(bx) for bx in boxes]
    for c, r in body.get('balls', []) or []:
        s = trimesh.creation.icosphere(subdivisions=k_('ball_subdiv'), radius=float(r))
        hulls.append(np.asarray(s.vertices) + np.asarray(c, np.float64))
    return hulls, boxes


def keepout_gate(ev, body, slot, slotted, partner_occ_lin=None, sil_lin=None):
    """F-I4.6: the F-I3.8 gate on the slotted pieces with the F-I1.8 keep-out (carved slot + FREE + SIL + the partner's
    persistent occupancy, within 2 voxels of the slotted body's surface; partner and carve weight 10)."""
    from gmg import simpieces as SP
    pitch = SP.k_('pitch_m')
    near = SP.k_('near_vox') * ev.grid.vox
    V = np.vstack(slotted)
    G = SP.grid_points(V.min(0) - near - 2 * pitch, V.max(0) + near + 2 * pitch, pitch)
    ins = SP.inside_any(slotted, G)
    cm = in_box(slot['box'], G) & in_box(body, G) & ~ins
    KP, KW = SP.keepout_points(None, G, ins, pitch, ev, near, cm, partner_occ_lin, sil_lin)
    gate = SP.pieces_gate({'slotted_plate': slotted}, KP, KW)
    gate['keepout_points'] = int(len(KP))
    return gate


# ------------------------------------------------------------------------------------------------ F-I4.0 the branch
def _plate(side, b):
    if getattr(side, '_plate_fi4', None) is None:
        side._plate_fi4 = plate_info(b, side.name, side.ev.mesh)
    return side._plate_fi4


def _sweep_push(comp, side, b, R_lin, rep):
    """Kept gates (i) sweep (>= 50 % of R's OBSERVED voxels swept; all of R if none is OBSERVED) and (ii) not pushable
    (median smallest rigid partner translation over the build frames R is entered > 10 mm, or a validated
    pushed_residual_m), exactly as decide_component computes them; reused from the record when step 4 ran."""
    ev = side.ev
    obs = ev.state[R_lin] == IL.STATE_OBSERVED
    sw_map = dict(zip(comp.lin.tolist(), comp.swept.tolist()))
    sel = R_lin[obs] if obs.any() else R_lin
    swept = np.array([sw_map.get(int(v), False) for v in sel])
    share = float(swept.mean()) if len(swept) else 0.0
    if rep.get('push_mm') is not None and 'ii' in rep:
        return share, rep['ii'], dict(push_mm=rep['push_mm'], reused=True)
    frames_R = [f for f in comp.run.build if np.isin(side.intr.entered(f), R_lin).any()]
    normal = IL._comp_frame(comp, ev, side)[1][1]
    push_m, per = IL.push_distance(side.intr, frames_R, R_lin, ev, normal=normal)
    ii_ok = bool(push_m > IL.K('push_prior_m'))
    info = dict(push_mm=round(push_m * 1e3, 1) if np.isfinite(push_m) else 'inf', push_frames=len(frames_R),
                reused=False)
    pr = side.intr.pushed_residual
    if pr:
        vals = [pr.get(f) for f in frames_R if pr.get(f) is not None and np.isfinite(pr.get(f))]
        if vals:
            band = float(b.band(side.name, side.intr.partner))
            ii_ok = float(np.mean([v > band for v in vals])) >= 0.5
            info['pushed_residual_used'] = dict(frames=len(vals), band_mm=round(band * 1e3, 2))
    return share, ii_ok, info


def _force_push(rep, why, flag):
    rep['decision_before_waiver_gate'] = rep['decision']
    rep['decision'] = 'PUSH'
    rep.pop('_sim_solid', None)
    rep['sim_carve'] = False
    rep['flags'].append(flag)
    if 'interlock_push' not in rep['flags']:
        rep['flags'].append('interlock_push')
    rep['push_list'] = dict(kind='PUSH', frames=[rep['_comp'].run.frames[0], rep['_comp'].run.frames[-1]],
                            push_mm=rep.get('push_mm'), why=why)


def apply_waiver(b, so, sp, recs, links, round_k=0):
    """F-I4.0 for every linked pair of this call. Mutates RECS: in-scope pairs that pass every kept gate become
    CARVE (simulator only, tier T1, flag owner_waiver_fi4, analytic slot in rec['_waiver']); otherwise the F-I1..F-I3
    decision stands with flag waiver_gate_fail:<gate> (F-I4.3 inconsistency and F-I4.4 budget PUSH both)."""
    byc = {id(r['_comp']): r for r in recs}
    done = set()
    for co in so.comps:
        if id(co) not in links or id(co) in done:
            continue
        cp = links[id(co)][0]
        if id(cp) in done:
            continue
        done |= {id(co), id(cp)}
        _pair(b, so, sp, co, cp, byc[id(co)], byc[id(cp)], round_k)
    return recs


def _pair(b, so, sp, co, cp, ro, rp, round_k):
    S = [(so, co, ro), (sp, cp, rp)]
    pi = {s.name: _plate(s, b) for s, _, _ in S}
    W = dict(rule=WAIVER_REF, plate={n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in pi.items()})
    in_scope = all(pi[s.name]['plate'] for s, _, _ in S) and all(c.run.kind == 'INSERTION' for _, c, _ in S)
    W['in_scope'] = bool(in_scope)
    if not in_scope:
        W['why_out'] = ('not plate-like: ' + ', '.join(n for n, x in pi.items() if not x['plate'])
                        if not all(x['plate'] for x in pi.values()) else 'run kinds ' +
                        ', '.join(c.run.kind for _, c, _ in S))
        for _, _, r in S:
            r['waiver_fi4'] = W
        return
    for _, _, r in S:
        r['flags'].append('owner_waiver_fi4')

    def fail(gate, push=False, why=''):
        W['gate_fail'] = gate
        for _, _, r in S:
            r['waiver_fi4'] = W
            r['flags'].append(f'waiver_gate_fail:{gate}')
            if push:
                _force_push(r, why or gate, gate if gate.startswith('interlock_') else 'budget_iv_fail')
        return
    # kept gate: identity / track (F-I1.2, F-I3.1)
    if not (so.track_ok and sp.track_ok):
        return fail('track_identity')
    gates = {}
    bodies, slots = {}, {}
    for s, c, r in S:
        R = c.region()
        g = dict(region_voxels=int(len(R)), run_kind=c.run.kind)
        gates[s.name] = g
        if c.run.kind == 'TRANSIENT' or len(R) < 3:
            W['gates'] = gates
            return fail('region_size')
        share, ii_ok, pinfo = _sweep_push(c, s, b, R, r)
        g.update(sweep_share=round(share, 3), sweep=bool(share >= IL.K('swept_share')), not_pushable=bool(ii_ok),
                 **pinfo)
    W['gates'] = gates
    if not all(g['sweep'] for g in gates.values()):
        return fail('sweep')
    if not all(g['not_pushable'] for g in gates.values()):
        return fail('push')
    for s, c, r in S:
        bd = plate_body(b, s.name, pi[s.name])
        bodies[s.name] = bd
    W['body'] = {n: {k: v for k, v in x.items()} for n, x in bodies.items()}
    for n, bd in bodies.items():
        if not bd['ok']:
            return fail(bd.get('why', 'plate_body'))
    # F-I4.3 slots
    for (s, c, r), (s2, _, _) in zip(S, S[::-1]):
        T = IL._asm_pose(s.intr, c.run)                     # T_{s<-s2}, the median assembled relative pose
        n2 = T[:3, :3] @ np.asarray(pi[s2.name]['mid_n'], np.float64)
        d2 = float(pi[s2.name]['mid_d']) + float(n2 @ T[:3, 3])
        sl = slot_for(s, c, c.region(), bodies[s.name]['box'], pi[s2.name]['t_m'], c.run, partner_plane=(n2, d2))
        slots[s.name] = sl
    W['slot'] = {n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in slots.items()}
    for n, sl in slots.items():
        if not sl['ok']:
            return fail(sl['why'])
    T_op = IL._asm_pose(so.intr, co.run)
    Wx, npts = crossing_extent(bodies[so.name]['box'], bodies[sp.name]['box'], T_op, co.run.d)
    Dsum = slots[so.name]['_D'] + slots[sp.name]['_D']
    # angle between the partner's plate normal (mapped into o) and o's a_L, both ways
    ang = {}
    for (s, c, r), (s2, c2, _) in zip(S, S[::-1]):
        T = IL._asm_pose(s.intr, c.run)                     # T_{s<-s2}
        nP = T[:3, :3] @ np.asarray(bodies[s2.name]['box']['axes'][2])
        aL = np.asarray(bodies[s.name]['box']['axes'][0])
        ang[s.name] = round(math.degrees(math.acos(min(1.0, abs(float(nP @ aL))))), 2)
        slots[s.name]['angle_partner_normal_aL_deg'] = ang[s.name]
        W['slot'][s.name]['angle_partner_normal_aL_deg'] = ang[s.name]
    W['crosslap'] = dict(W_x_mm=round(Wx * 1e3, 2), grid_points=npts, D_sum_mm=round(Dsum * 1e3, 2),
                         diff_mm=round((Dsum - Wx) * 1e3, 2), window_mm=k_('consist_m') * 1e3,
                         ok=bool(abs(Dsum - Wx) <= k_('consist_m')))
    if not W['crosslap']['ok']:
        return fail('interlock_slot_inconsistent', push=True,
                    why=f'|D_o + D_p - W_x| = {abs(Dsum - Wx) * 1e3:.1f} mm > 10 mm (F-I4.3)')
    # F-I4.4 budget and topology
    bud = {}
    for s, c, r in S:
        bud[s.name] = slot_budget(s, bodies[s.name]['box'], slots[s.name], c.run.d,
                                  carved_before_cm3=s.carved_cm3_before)
    W['budget'] = {n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in bud.items()}
    if not all(x['ok'] for x in bud.values()):
        return fail('budget_iv', push=True, why='budget (iv) / topology on the analytic slot (F-I4.4)')
    # pass: CARVE both (simulator copy only)
    for s, c, r in S:
        slotted, sboxes = pieces(bodies[s.name]['box'], slots[s.name])
        default, _ = pieces(bodies[s.name]['box'], None)
        r['decision_f_i3'] = r['decision']
        r['tier_f_i3'] = r['tier']
        r['decision'] = 'CARVE'
        r['tier'] = 'T1'
        r.pop('_sim_solid', None)
        r['flags'] = [f for f in r['flags'] if f not in ('interlock_push', 'interlock_pair_fail')]
        if 'push_list' in r:
            r['push_list_f_i3'] = r.pop('push_list')
        r['sim_carve'] = True
        r['waiver_fi4'] = W
        r['_waiver'] = dict(body=bodies[s.name]['box'], slot=slots[s.name], slotted=slotted, slot_boxes=sboxes,
                            default=default, slot_cm3=bud[s.name]['slot_cm3'], body_cm3=bud[s.name]['body_cm3'],
                            w_sim_m=slots[s.name]['_w'])
    W['decision'] = 'CARVE (simulator copy only, T1)'
    return


# ------------------------------------------------------------------------------------------------ F-I4.7 acceptance
def acceptance(phys, gates, n_shapes):
    """F-I4.7 table: P2, P3 (with the restored overlap clause), P4 (both objects), P5 (<= 165 shapes in the episode),
    P6, P7, keep-out per object. P1 = pending (the Embodiment's jitter_check --k 16)."""
    from gmg import simphys as PH
    rows = dict(P2=bool(phys['P2']['pass_']))
    if 'P3' in phys:
        rows['P3'] = bool(phys['P3']['judge']['pass_'])
    else:
        rows['P3'] = False
    for o, v in phys['P4'].items():
        rows[f'P4_{o}'] = bool(v['pass_'])
    p5 = PH.shape_budget(n_shapes)
    rows['P5'] = bool(p5['pass_'])
    rows['P6'] = bool(phys['P6']['pass_'])
    rows['P7'] = bool(phys['P7'].get('pass_', True))
    for o, g in gates.items():
        rows[f'keepout_{o}'] = g['do_not_use'] is None
    failing = [k for k, v in rows.items() if not v]
    return dict(tests=rows, P5=p5, failing=failing, pass_all_but_P1=not failing, P1='pending (Embodiment '
                'jitter_check --k 16 on the delivered folder; F-I2.12, F-I4.8)')
