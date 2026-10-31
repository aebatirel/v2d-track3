"""Board slot under the owner's waiver of the camera rule (PREREG F-I4, INTERLOCK.md section 20).

New code path only. interlock.decide_pair(..., waiver_fi4=True) calls apply_waiver() after the F-I1..F-I3 decisions
of the pair; with the flag off nothing here runs and every earlier decision is unchanged (F-I4.10 w2). One branch for
both paths (our tracks and an Embodiment export, F-I3.1): it reads only the Side objects decide_pair already has.

Owner, 31 Oct ~16:00 UTC: "Okay I waive that camera rule" (F-I4.0). Scope: a linked pair whose two targets are
plate-like (F-I4.1) and whose two linked components come from INSERTION runs. In scope, class O and an absent or
failing silhouette no longer block the carve; every other gate stays.

  plate_info(b, obj, mesh)            F-I4.1 plane-pair test (structure._points / _planes: the B7 code) on the object's
                                      owned points within 6 mm of its pick; plate pair = largest footprint overlap
                                      (ties: more inliers); thickness t and the mid plane. F-I4.14 (post hoc, after
                                      T-I11 found no plane pair on either ep24 board): else the camera-side face pair
                                      (_camera_side: slab points of the largest plane split by camera side, median
                                      offset per face), else a one-face plate candidate
  resolve_one_face(info, partner)     F-I4.14 step 3: a one-face plate takes the partner's measured t (same-stock prior
                                      [E], flag plate_t_partner_prior); mid plane = seen face moved t / 2 off the cameras
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

PREREG F-I4.15 (post hoc, round 2, orchestrator decision 31 Oct ~18:05 UTC; REV = 15, records carry fi4_rev 15):
  _t_all_points                       t and the mid plane from the step-2 camera-side estimator on ALL near points (the
                                      plate TESTS stay on the 2 mm downsample); one-face plates take the partner's
                                      all-point t, mid plane from the seen face over all points
  plate_body_poly                     body = the observed outline polygon (2 mm cells laid along the F-I4.2 rectangle's
                                      axes, same cell rules, outer ring, Douglas-Peucker 1.0 mm, must be simple)
                                      extruded at t; the rectangle is the frame only (fill reported, no 0.9 gate)
  slot_for_poly                       F-I4.3 / F-I4.12 slot in the rectangle frame; D measured from the polygon's edge at
                                      the slot mouth (the slot bottom is unchanged)
  crossing_extent_poly / slot_budget_poly   W_x, budget and topology on the polygon prisms (thresholds unchanged)
  pieces_poly                         exact convex partition (ear clipping + Hertel-Mehlhorn) of the polygon minus the
                                      slot footprint, prisms <= 64 vertices, <= floor(165 / objects) per body
  keepout_gate                        unchanged (in_body() now tests the polygon prism)
  The F-I4.12 centre is unchanged; the module text above about the component centroid (F-I4.3) is superseded by
  F-I4.12 (slot_for computes the partner-plane centre). REV = 14 reproduces the rectangle route (tests only).
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
    simplify_m=(0.001, 'generic:F-I4.15.9 Douglas-Peucker tolerance 1.0 mm (half the 2 mm raster pitch)'),
    shapes_max=(165, 'informed:F-I4.15.9 prisms per body <= floor(165 / objects) (the P5 cap, F-I1.14; as F-I5.4)'),
    part_vmax=(32, 'informed:F-I4.15.9 <= 32 vertices per polygon part = 64 per prism (MuJoCo maxv, F-I1.14)'),
)

REV = 15                # PREREG F-I4.15 (records carry fi4_rev); 14 = the F-I4.14 rectangle route (tests only)


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


def _down_idx(P, K):
    """Indices of structure._points' 2 mm first-point-per-voxel downsample (and its rng(0) cap), so the frames of the
    downsampled points are known (structure._points drops them)."""
    k = np.floor(P / K['vox']).astype(np.int64)
    _, idx = np.unique(k, axis=0, return_index=True)
    if len(idx) > K['max_pts']:
        s = np.random.default_rng(0).choice(len(idx), K['max_pts'], replace=False)
        idx = idx[s]
    return idx


def _face(X, C, F, a, e1, e2):
    """One camera-side face (F-I4.14 step 2): PCA normal oriented to its cameras, median offset along a, rms about its own
    plane, 2-98 % box in (e1, e2), frames."""
    c = X.mean(0)
    V = np.linalg.eigh(np.cov((X - c).T))[1]
    nf = V[:, 0]
    if np.median((C - X) @ nf) < 0:
        nf = -nf
    u, v = X @ e1, X @ e2
    return dict(n_pts=int(len(X)), frames=int(len(np.unique(F))), normal=nf, m=float(np.median(X @ a)),
                rms_m=float(np.std((X - c) @ nf)),
                box=(float(np.percentile(u, 2)), float(np.percentile(u, 98)), float(np.percentile(v, 2)),
                     float(np.percentile(v, 98))))


def _camera_side(Pd, Cd, Fd, plane0, sigma, K):
    """PREREG F-I4.14 steps 2-3 (post hoc): split the slab points of the largest F-I4.1 plane by the side their camera is
    on. Returns dict(kind 'two_sided' | 'one_face' | None, ok, t_m, mid_n, mid_d, checks, ...)."""
    a = np.asarray(plane0['n'], np.float64); a /= np.linalg.norm(a)
    e1 = np.asarray(plane0['e1'], np.float64); e2 = np.asarray(plane0['e2'], np.float64)
    da = float(plane0['d'])
    s = Pd @ a
    k = np.abs(s - da) <= K['slab'][1]
    X, C, F = Pd[k], Cd[k], Fd[k]
    view = np.einsum('ij,j->i', C - X, a)
    Sp, Sm = view > 0, view < 0
    fmin = k_('frames_min')
    u, v = X @ e1, X @ e2
    ext = [float(np.percentile(u, 98) - np.percentile(u, 2)), float(np.percentile(v, 98) - np.percentile(v, 2))]
    out = dict(method='camera_side (F-I4.14)', slab_points=int(k.sum()), plus=int(Sp.sum()), minus=int(Sm.sum()),
               plus_frames=int(len(np.unique(F[Sp]))), minus_frames=int(len(np.unique(F[Sm]))),
               inplane_extents_mm=[round(x * 1e3, 1) for x in ext], kind=None, ok=False, _a=a, _d_ref=da)
    good = [int(S.sum()) >= K['plane_min'] and len(np.unique(F[S])) >= fmin for S in (Sp, Sm)]
    if all(good):
        fp, fm = _face(X[Sp], C[Sp], F[Sp], a, e1, e2), _face(X[Sm], C[Sm], F[Sm], a, e1, e2)
        t = fp['m'] - fm['m']
        cos_pm = float(fp['normal'] @ fm['normal'])
        ba, bb = fp['box'], fm['box']
        iu = max(0.0, min(ba[1], bb[1]) - max(ba[0], bb[0])); iv = max(0.0, min(ba[3], bb[3]) - max(ba[2], bb[2]))
        area = min((ba[1] - ba[0]) * (ba[3] - ba[2]), (bb[1] - bb[0]) * (bb[3] - bb[2]))
        ov = float(iu * iv / max(area, 1e-12))
        w = t + 2 * IL.K('clearance_m')
        chk = dict(antiparallel=bool(cos_pm <= -math.cos(math.radians(K['plane_deg']))),
                   material_between=bool(t > 0), window=bool(K['slab'][0] <= t <= K['slab'][1]),
                   overlap=bool(ov >= K['pair_overlap']),
                   rms=bool(fp['rms_m'] <= K['band'] * sigma and fm['rms_m'] <= K['band'] * sigma),
                   plate_extents=bool(min(ext) >= 2 * w))
        out.update(kind='two_sided', ok=all(chk.values()), checks=chk, t_mm=round(t * 1e3, 3), t_m=float(t),
                   overlap=round(ov, 4), angle_deg=round(math.degrees(math.acos(max(-1.0, min(1.0, -cos_pm)))), 2),
                   faces=[{kk: (round(vv * 1e3, 3) if kk in ('m', 'rms_m') else vv) for kk, vv in f.items()
                           if kk not in ('normal', 'box')} for f in (fp, fm)],
                   mid_n=a.tolist(), mid_d=float(0.5 * (fp['m'] + fm['m'])))
        return out
    if any(good):
        seen = +1 if good[0] else -1
        S = Sp if seen > 0 else Sm
        ext_n = float(np.percentile(s[k], 99) - np.percentile(s[k], 1))
        thin = bool(ext_n <= K['slab'][1])
        out.update(kind='one_face', ok=thin, seen_sign=seen, m_seen=float(np.median(X[S] @ a)),
                   extent_n_1_99_mm=round(ext_n * 1e3, 2), checks=dict(thin_extent=thin), mid_n=a.tolist(),
                   _ext_min=min(ext))
        return out
    out['why'] = 'no side with >= plane_min points from >= 3 frames'
    return out


def plate_info(b, obj, mesh):
    """F-I4.1: the structure plane-pair test (structure._points + structure._planes, the B7 code path) on OBJ's owned
    points within 6 mm of its pick. F-I4.14 (post hoc): if no plane pair, the camera-side face pair (step 2), else a
    one-face plate candidate whose thickness the pair resolves from the partner (step 3, resolve_one_face).
    Returns dict(plate bool, t_m, mid_n, mid_d, pair, pairs, planes summary, points, t_source)."""
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
    out['planes'] = [dict(n=np.round(p['n'], 4).tolist(), n_pts=p['n_pts'], rms_mm=p['rms_mm'],
                          two_sided_share=p['two_sided_share']) for p in planes]
    out['pairs'] = pairs
    out['_P'], out['_F'], out['_C'] = P, fr, Cm
    if not pairs:
        out['why_f_i4_1'] = 'no_plane_pair'
        if not planes:
            out.update(why='no_plane', sec=round(time.time() - t0, 1))
            return out
        idx = _down_idx(P, K)
        assert np.array_equal(P[idx], Pd), 'downsample index mismatch'
        cs = _camera_side(Pd, Cd, fr[idx], planes[0], sigma, K)
        out['camera_side'] = {k: v for k, v in cs.items() if not k.startswith('_')}
        out['_e1'] = np.asarray(planes[0]['e1'], np.float64)
        if cs['kind'] == 'two_sided' and cs['ok']:
            out.update(plate=True, t_m=cs['t_m'], mid_n=cs['mid_n'], mid_d=cs['mid_d'], t_source='camera_side_pair',
                       flags=['plate_pair_camera_side'], pair=dict(method=cs['method'], thickness_mm=cs['t_mm'],
                                                                   overlap=cs['overlap']), sec=round(time.time() - t0, 1))
            if REV >= 15:                                  # F-I4.15.1: t and mid plane from all near points
                _apply_t_all(out, P, Cm, fr, cs['_a'], cs['_d_ref'], K)
            return out
        if cs['kind'] == 'one_face' and cs['ok']:
            if REV >= 15:                                  # F-I4.15.1: the seen face from all near points
                m_all, n_all = _m_seen_all(P, Cm, cs['_a'], cs['_d_ref'], cs['seen_sign'], K)
                cs = dict(cs, _m_seen_all=m_all, m_seen_all_points=n_all)
                out['camera_side'] = {k: v for k, v in cs.items() if not k.startswith('_')}
            out.update(why='one_face_pending_partner', _one_face=cs, sec=round(time.time() - t0, 1))
            return out
        out.update(why='no_plane_pair' if cs['kind'] is None else f'camera_side_{cs["kind"]}_fail',
                   sec=round(time.time() - t0, 1))
        return out
    best = max(pairs, key=lambda q: (q['overlap'], planes[q['faces'][0]]['n_pts'] + planes[q['faces'][1]]['n_pts']))
    mid_n = np.asarray(best['mid_n'], np.float64)
    out.update(plate=True, pair=best, t_m=float(best['thickness_mm']) * 1e-3, mid_n=mid_n.tolist(),
               mid_d=float(best['mid_d']), t_source='plane_pair', sec=round(time.time() - t0, 1))
    out['_e1'] = np.asarray(planes[best['faces'][0]]['e1'], np.float64)
    if REV >= 15:                                          # F-I4.15.1: t and mid plane from all near points
        _apply_t_all(out, P, Cm, fr, mid_n, float(best['mid_d']), K)
    return out


def _apply_t_all(out, P, Cm, fr, a, d_ref, K):
    """F-I4.15.1 on a plate by step 1 or 2: replaces t and the mid plane by the all-point estimate (reference a, d_ref);
    the downsample t stays reported (t_down_mm); a failing estimate makes the object not plate-like."""
    ta = _t_all_points(P, Cm, fr, a, d_ref, K)
    out['t_down_mm'] = round(float(out['t_m']) * 1e3, 3)
    out['t_all'] = ta
    out['fi4_rev'] = 15
    if not ta['ok']:
        out.update(plate=False, why='t_all_points_fail')
        return out
    out.update(t_m=ta['t_m'], mid_n=ta['mid_n'], mid_d=ta['mid_d'], t_estimator='all near points (F-I4.15.1)')
    return out


def resolve_one_face(info, partner):
    """F-I4.14 step 3: a one-face plate candidate takes the partner's MEASURED thickness (plane pair or camera-side pair;
    same-stock prior [E], flag plate_t_partner_prior); mid plane = the seen face moved t / 2 away from its cameras;
    plate-like extents >= 2 (t + 2 mm). Returns a new dict (the cached info is not changed)."""
    cs = info.get('_one_face')
    if info.get('plate') or cs is None:
        return info
    out = dict(info)
    if not partner.get('plate') or partner.get('t_source') not in ('plane_pair', 'camera_side_pair'):
        out['why'] = 'one_face_no_partner_t'
        return out
    t = float(partner['t_m'])
    w = t + 2 * IL.K('clearance_m')
    ext_ok = bool(cs['_ext_min'] >= 2 * w)
    out['camera_side'] = dict(out.get('camera_side') or {}, checks=dict(cs['checks'], plate_extents=ext_ok))
    if not ext_ok:
        out['why'] = 'one_face_not_plate_extents'
        return out
    m_seen = cs['_m_seen_all'] if (REV >= 15 and cs.get('_m_seen_all') is not None) else cs['m_seen']
    out.update(plate=True, t_m=t, mid_n=cs['mid_n'], mid_d=float(m_seen - cs['seen_sign'] * t / 2),
               t_source='partner_prior', flags=['plate_t_partner_prior'],
               pair=dict(method='one_face (F-I4.14 step 3)', thickness_mm=round(t * 1e3, 3),
                         t_from=partner['obj'], seen_sign=cs['seen_sign']))
    out.pop('why', None)
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
    cm = in_box(slot['box'], G) & in_body(body, G) & ~ins      # F-I4.15: in_body = the polygon prism
    KP, KW = SP.keepout_points(None, G, ins, pitch, ev, near, cm, partner_occ_lin, sil_lin)
    gate = SP.pieces_gate({'slotted_plate': slotted}, KP, KW)
    gate['keepout_points'] = int(len(KP))
    return gate


# ------------------------------------------------------------------------------------------------ F-I4.15 2-D geometry
# PREREG F-I4.15 (post hoc, round 2): the plate body is the observed outline polygon. Polygons here are (n, 2) float
# arrays in mm in the body frame (u along a_L, v along a_W, origin = the rectangle centre in the mid plane),
# counter-clockwise seen from +a_T, not closed. Self-contained (no shapely in the venv or on the boxes).
class Degenerate(Exception):
    """A polygon vertex lies on a clip-rectangle edge (or an edge is collinear with one): the caller nudges."""


def _cr(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def poly_area(R):
    R = np.asarray(R, np.float64)
    if len(R) < 3:
        return 0.0
    x, y = R[:, 0], R[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _coll(a, b, c, rel=1e-9):
    """b collinear with a, c and between them (a straight continuation)."""
    ab = (b[0] - a[0], b[1] - a[1]); bc = (c[0] - b[0], c[1] - b[1])
    s = math.hypot(*ab) * math.hypot(*bc)
    return abs(_cr(a, b, c)) <= rel * s + 1e-12 and (ab[0] * bc[0] + ab[1] * bc[1]) > 0


def drop_collinear(R):
    """Removes repeated consecutive vertices and vertices on a straight continuation (180 deg); spikes are kept, so a
    non-simple ring stays non-simple."""
    P = [tuple(map(float, p)) for p in np.asarray(R, np.float64)]
    changed = True
    while changed and len(P) > 3:
        changed = False
        n = len(P)
        keep = []
        for i in range(n):
            a, b, c = P[i - 1], P[i], P[(i + 1) % n]
            if b == a or _coll(a, b, c):
                continue
            keep.append(b)
        if len(keep) < n:
            changed = True
            P = keep
    return np.asarray(P, np.float64).reshape(-1, 2)


def mask_ring(M):
    """Outer boundary of the union of the cells of the bool mask M (cell (i, j) = [i, i+1] x [j, j+1]) as closed
    counter-clockwise loops of integer cell corners (interior on the left). At a pinch vertex (cells touching only at
    a corner) the walk takes the rightmost turn, so an 8-connected mask gives one ring that visits the pinch twice.
    Returns (list of loops (k, 2) int arrays with collinear vertices removed, number of pinch vertices)."""
    M = np.asarray(M, bool)
    Mp = np.pad(M, 1)
    I, J = np.nonzero(M)
    ii, jj = I + 1, J + 1
    out = {}

    def add(s, a, b):
        for k in np.nonzero(s)[0]:
            out.setdefault((int(a[0][k]), int(a[1][k])), []).append((int(b[0][k]), int(b[1][k])))
    add(~Mp[ii, jj - 1], (I, J), (I + 1, J))                 # bottom edge, +u
    add(~Mp[ii + 1, jj], (I + 1, J), (I + 1, J + 1))         # right edge, +v
    add(~Mp[ii, jj + 1], (I + 1, J + 1), (I, J + 1))         # top edge, -u
    add(~Mp[ii - 1, jj], (I, J + 1), (I, J))                 # left edge, -v
    pinch = sum(len(v) > 1 for v in out.values())
    used = set()
    loops = []
    for start in sorted(out):
        for b0 in sorted(out[start]):
            if (start, b0) in used:
                continue
            loop, a, b = [], start, b0
            while True:
                used.add((a, b))
                loop.append(a)
                cand = [c for c in out.get(b, []) if (b, c) not in used]
                if not cand:
                    break
                din = (b[0] - a[0], b[1] - a[1])
                c = min(cand, key=lambda q: (din[0] * (q[1] - b[1]) - din[1] * (q[0] - b[0]), q))
                a, b = b, c
            loops.append(drop_collinear(np.asarray(loop, np.float64)).astype(np.int64))
    return loops, pinch


def _dp_chain(Q, tol):
    keep = np.zeros(len(Q), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(Q) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = Q[i], Q[j]
        seg = b - a
        L2 = float(seg @ seg)
        X = Q[i + 1:j]
        if L2 <= 0:
            d = np.linalg.norm(X - a, axis=1)
        else:
            s = np.clip(((X - a) @ seg) / L2, 0.0, 1.0)
            d = np.linalg.norm(X - (a + s[:, None] * seg), axis=1)
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return keep


def dp_ring(R, tol):
    """Douglas-Peucker on a closed ring, split at the two ring vertices farthest apart (ties: lowest indices); distance
    to the chord segment. Returns the kept vertices in ring order, collinear vertices removed."""
    R = np.asarray(R, np.float64)
    n = len(R)
    if n <= 4:
        return R.copy()
    D = np.linalg.norm(R[:, None, :] - R[None, :, :], axis=2)
    i0, i1 = np.unravel_index(int(np.argmax(np.triu(D, 1))), D.shape)
    i0, i1 = int(min(i0, i1)), int(max(i0, i1))
    c1 = R[i0:i1 + 1]
    c2 = np.vstack([R[i1:], R[:i0 + 1]])
    k1 = i0 + np.nonzero(_dp_chain(c1, tol))[0]
    k2 = (i1 + np.nonzero(_dp_chain(c2, tol))[0]) % n
    idx = np.unique(np.concatenate([k1, k2]))
    return drop_collinear(R[idx])


def _orient(a, b, c):
    return (b[..., 0] - a[..., 0]) * (c[..., 1] - a[..., 1]) - (b[..., 1] - a[..., 1]) * (c[..., 0] - a[..., 0])


def ring_simple(R, eps=1e-9):
    """True if the closed ring R is a simple polygon: >= 3 vertices, no repeated vertex, non-zero area, adjacent edges
    not folded back, and no two non-adjacent edges touching or crossing."""
    R = np.asarray(R, np.float64)
    n = len(R)
    if n < 3 or abs(poly_area(R)) <= eps:
        return False
    if len(np.unique(np.round(R, 9), axis=0)) < n:
        return False
    A, B = R, np.roll(R, -1, axis=0)
    # adjacent edges k, k+1 folded back onto each other
    d0, d1 = B - A, np.roll(B - A, -1, axis=0)
    cr = d0[:, 0] * d1[:, 1] - d0[:, 1] * d1[:, 0]
    if np.any((np.abs(cr) <= eps * np.linalg.norm(d0, axis=1) * np.linalg.norm(d1, axis=1)) &
              (np.einsum('ij,ij->i', d0, d1) < 0)):
        return False
    if n == 3:
        return True
    k, l = np.triu_indices(n, 2)
    sel = ~((k == 0) & (l == n - 1))
    k, l = k[sel], l[sel]
    a, b, c, d = A[k], B[k], A[l], B[l]
    sc = np.maximum(np.linalg.norm(b - a, axis=1), 1e-12) * np.maximum(np.linalg.norm(d - c, axis=1), 1e-12)
    o1, o2 = _orient(a, b, c), _orient(a, b, d)
    o3, o4 = _orient(c, d, a), _orient(c, d, b)
    z = [np.abs(o) <= eps * sc for o in (o1, o2, o3, o4)]
    o1, o2, o3, o4 = [np.where(zz, 0.0, o) for zz, o in zip(z, (o1, o2, o3, o4))]

    def on(p, s0, s1):
        return (np.minimum(s0[:, 0], s1[:, 0]) - eps <= p[:, 0]) & (p[:, 0] <= np.maximum(s0[:, 0], s1[:, 0]) + eps) & \
            (np.minimum(s0[:, 1], s1[:, 1]) - eps <= p[:, 1]) & (p[:, 1] <= np.maximum(s0[:, 1], s1[:, 1]) + eps)
    hit = ((o1 * o2 < 0) & (o3 * o4 < 0)) | (z[0] & on(c, a, b)) | (z[1] & on(d, a, b)) | (z[2] & on(a, c, d)) | \
        (z[3] & on(b, c, d))
    return not bool(hit.any())


def pip(R, X):
    """Even-odd point-in-polygon for points X (m, 2) against the ring R (on-boundary points: either side)."""
    R = np.asarray(R, np.float64)
    X = np.asarray(X, np.float64).reshape(-1, 2)
    x, y = X[:, 0], X[:, 1]
    ins = np.zeros(len(X), bool)
    n = len(R)
    for k in range(n):
        x1, y1 = R[k]
        x2, y2 = R[(k + 1) % n]
        c = (y1 > y) != (y2 > y)
        if not c.any():
            continue
        xi = x1 + (y[c] - y1) * (x2 - x1) / (y2 - y1)
        ins[np.nonzero(c)[0][x[c] < xi]] ^= True
    return ins


def clip_half(R, nrm, c):
    """Sutherland-Hodgman: R intersected with {x : nrm . x <= c} (a non-convex R may give zero-width bridges along the
    clip line; areas and vertex extents stay exact)."""
    R = np.asarray(R, np.float64)
    out = []
    n = len(R)
    nrm = np.asarray(nrm, np.float64)
    for k in range(n):
        P, Q = R[k], R[(k + 1) % n]
        fp, fq = float(nrm @ P - c), float(nrm @ Q - c)
        if fp <= 0:
            out.append(P)
        if (fp < 0 < fq) or (fq < 0 < fp):
            out.append(P + fp / (fp - fq) * (Q - P))
    return np.asarray(out, np.float64).reshape(-1, 2) if len(out) >= 3 else np.zeros((0, 2))


def clip_rect(R, u0, u1, v0, v1):
    for nrm, c in (((-1.0, 0.0), -u0), ((1.0, 0.0), u1), ((0.0, -1.0), -v0), ((0.0, 1.0), v1)):
        if not np.isfinite(c):
            continue
        R = clip_half(R, nrm, c)
        if len(R) < 3:
            return np.zeros((0, 2))
    return R


def poly_minus_rect(A, u0, u1, v0, v1, eps=1e-9):
    """Weiler-Atherton difference A minus the axis-aligned rectangle [u0, u1] x [v0, v1] for a simple CCW ring A.
    Returns dict(rings (CCW loops), hole (the rectangle lies inside A without touching its boundary)). Raises
    Degenerate if a vertex of either lies on the other's boundary."""
    A = np.asarray(A, np.float64)
    B = np.array([[u0, v0], [u1, v0], [u1, v1], [u0, v1]], np.float64)
    nA = len(A)
    for p in A:                                      # A vertex on a rectangle edge line inside the edge's span
        if (abs(p[0] - u0) <= eps or abs(p[0] - u1) <= eps) and v0 - eps <= p[1] <= v1 + eps:
            raise Degenerate('vertex on a vertical rectangle edge')
        if (abs(p[1] - v0) <= eps or abs(p[1] - v1) <= eps) and u0 - eps <= p[0] <= u1 + eps:
            raise Degenerate('vertex on a horizontal rectangle edge')
    I = []
    for i in range(nA):
        a1, a2 = A[i], A[(i + 1) % nA]
        da = a2 - a1
        for j in range(4):
            b1, b2 = B[j], B[(j + 1) % 4]
            db = b2 - b1
            den = da[0] * db[1] - da[1] * db[0]
            if abs(den) <= eps * np.linalg.norm(da) * np.linalg.norm(db):
                continue
            w = b1 - a1
            s = (w[0] * db[1] - w[1] * db[0]) / den
            r = (w[0] * da[1] - w[1] * da[0]) / den
            if -eps <= r <= 1 + eps and (abs(r) <= eps or abs(r - 1) <= eps) and 0 <= s <= 1:
                raise Degenerate('rectangle corner on an edge of A')
            if 0 < s < 1 and 0 < r < 1:
                I.append(dict(p=a1 + s * da, i=i, s=float(s), j=j, r=float(r),
                              entering=bool(db[0] * da[1] - db[1] * da[0] > 0)))
    if not I:
        if pip(A, B[:1])[0]:
            return dict(rings=[A.copy()], hole=True)
        if pip(B, A[:1])[0]:
            return dict(rings=[], hole=False)
        return dict(rings=[A.copy()], hole=False)
    la, lb = [], []
    for i in range(nA):
        la.append(('v', A[i]))
        la += [('x', k) for k in sorted((k for k in range(len(I)) if I[k]['i'] == i), key=lambda k: I[k]['s'])]
    for j in range(4):
        lb.append(('v', B[j]))
        lb += [('x', k) for k in sorted((k for k in range(len(I)) if I[k]['j'] == j), key=lambda k: I[k]['r'])]
    posA = {e[1]: q for q, e in enumerate(la) if e[0] == 'x'}
    posB = {e[1]: q for q, e in enumerate(lb) if e[0] == 'x'}
    visited, rings = set(), []
    for k0 in [e[1] for e in la if e[0] == 'x']:
        if k0 in visited or I[k0]['entering']:
            continue
        ring, cur, on = [], k0, 'A'
        for _ in range(4 * (len(la) + len(lb))):
            visited.add(cur)
            ring.append(I[cur]['p'])
            if on == 'A':
                q = posA[cur]
                while True:
                    q = (q + 1) % len(la)
                    if la[q][0] == 'x':
                        cur, on = la[q][1], 'B'
                        break
                    ring.append(la[q][1])
            else:
                q = posB[cur]
                while True:
                    q = (q - 1) % len(lb)
                    if lb[q][0] == 'x':
                        cur, on = lb[q][1], 'A'
                        break
                    ring.append(lb[q][1])
            if cur == k0:
                break
        else:
            raise RuntimeError('Weiler-Atherton walk did not close')
        rings.append(drop_collinear(np.asarray(ring, np.float64)))
    return dict(rings=rings, hole=False)


def ear_clip(R, eps=1e-9):
    """Ear-clipping triangulation of a simple CCW ring (collinear vertices removed first). Each step takes the first ear
    in ring order from the lowest-index remaining vertex; an ear is a strictly convex vertex whose triangle (closed)
    holds no other remaining vertex. A remaining vertex that has become collinear is dropped without a triangle.
    Returns a list of index triples into R."""
    R = np.asarray(R, np.float64)
    idx = list(range(len(R)))
    tris = []
    while len(idx) > 3:
        m = len(idx)
        done = False
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = R[i0], R[i1], R[i2]
            if _coll(a, b, c):
                idx.pop(k)
                done = True
                break
            sc = np.linalg.norm(b - a) * np.linalg.norm(c - b)
            if _cr(a, b, c) <= eps * sc:
                continue
            oth = [idx[q] for q in range(m) if q not in ((k - 1) % m, k, (k + 1) % m)]
            if oth:
                X = R[oth]
                s = max(sc, 1e-12)
                inside = (_orient(a, b, X) >= -eps * s) & (_orient(b, c, X) >= -eps * s) & (_orient(c, a, X) >= -eps * s)
                if inside.any():
                    continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            done = True
            break
        if not done:
            raise RuntimeError('ear clipping found no ear (ring not simple?)')
    if len(idx) == 3 and not _coll(R[idx[0]], R[idx[1]], R[idx[2]]):
        tris.append(tuple(idx))
    return tris


def hertel_mehlhorn(R, tris, eps=1e-9):
    """Hertel-Mehlhorn: remove internal diagonals of the triangulation, longest first (ties: vertex indices), when both
    endpoints stay convex (interior angle <= 180 deg) in the merged part. Returns parts as CCW index lists."""
    R = np.asarray(R, np.float64)
    parts = [list(t) for t in tris]
    cnt = {}
    for t in tris:
        for q in range(3):
            e = tuple(sorted((t[q], t[(q + 1) % 3])))
            cnt[e] = cnt.get(e, 0) + 1
    diags = sorted((e for e, c in cnt.items() if c == 2),
                   key=lambda e: (-float(np.linalg.norm(R[e[0]] - R[e[1]])), e))

    def find(i, j):
        for pi, P in enumerate(parts):
            m = len(P)
            for q in range(m):
                if P[q] == i and P[(q + 1) % m] == j:
                    return pi, q
        return None, None
    for i, j in diags:
        p1, q1 = find(i, j)
        p2, q2 = find(j, i)
        if p1 is None or p2 is None or p1 == p2:
            continue
        P1, P2 = parts[p1], parts[p2]
        P1r = P1[(q1 + 1):] + P1[:(q1 + 1)]            # starts with j, ends with i
        P2r = P2[(q2 + 1):] + P2[:(q2 + 1)]            # starts with i, ends with j
        Mg = P1r + P2r[1:-1]
        m = len(Mg)
        ki = Mg.index(i)
        kj = 0
        ok = True
        for kk in (ki, kj):
            a, b, c = R[Mg[kk - 1]], R[Mg[kk]], R[Mg[(kk + 1) % m]]
            sc = np.linalg.norm(b - a) * np.linalg.norm(c - b)
            if _cr(a, b, c) < -eps * sc:
                ok = False
        if not ok:
            continue
        parts = [P for q, P in enumerate(parts) if q not in (p1, p2)] + [Mg]
    return parts


def convex_partition(R, vmax):
    """F-I4.15.4: ear clipping + Hertel-Mehlhorn of the simple CCW ring R; parts with more than VMAX vertices are split
    by the diagonal from their vertex 0 to vertex floor(k / 2) until every part has <= VMAX. Returns a list of CCW
    convex polygons (coordinate arrays), collinear vertices removed."""
    R = drop_collinear(R)
    if poly_area(R) < 0:
        R = R[::-1]
    tris = ear_clip(R)
    parts = [drop_collinear(R[P]) for P in hertel_mehlhorn(R, tris)]
    out = []
    while parts:
        P = parts.pop(0)
        k = len(P)
        if k <= vmax:
            out.append(P)
            continue
        h = k // 2
        parts = [P[:h + 1], np.vstack([P[h:], P[:1]])] + parts
    return out


def convex_ok(P, eps=1e-9):
    P = np.asarray(P, np.float64)
    n = len(P)
    for k in range(n):
        a, b, c = P[k - 1], P[k], P[(k + 1) % n]
        if _cr(a, b, c) < -eps * np.linalg.norm(b - a) * np.linalg.norm(c - b):
            return False
    return poly_area(P) > 0


def chord_widths(R, us):
    """Total length of the polygon's intersection with the lines u = us (vertical chords), per u."""
    R = np.asarray(R, np.float64)
    out = []
    n = len(R)
    for u in us:
        ys = []
        for k in range(n):
            (x1, y1), (x2, y2) = R[k], R[(k + 1) % n]
            if (x1 > u) != (x2 > u):
                ys.append(y1 + (u - x1) * (y2 - y1) / (x2 - x1))
        ys.sort()
        out.append(float(sum(ys[q + 1] - ys[q] for q in range(0, len(ys) - 1, 2))))
    return np.asarray(out)


# ------------------------------------------------------------------------------------------------ F-I4.15 thickness
def _t_all_points(P, Cm, F, a, d_ref, K):
    """PREREG F-I4.15.1 (post hoc): the step-2 camera-side estimator on ALL near points (no downsample, no cap): slab
    |a . x - d_ref| <= 25 mm, S+ / S- by the side of each point's camera, m+- = median of a . x per side,
    t = m+ - m-, mid plane (a, (m+ + m-) / 2). Checks: each side >= 300 points from >= 3 frames, t > 0, t in 3-25 mm.
    Reports each face's count, frames, frame range and the 5 / 50 / 95 % of its per-frame medians about the mid plane."""
    a = np.asarray(a, np.float64)
    a = a / np.linalg.norm(a)
    s = P @ a
    k = np.abs(s - float(d_ref)) <= K['slab'][1]
    X, C, Fk, sk = P[k], Cm[k], np.asarray(F)[k], s[k]
    view = np.einsum('ij,j->i', C - X, a)
    Sp, Sm = view > 0, view < 0
    fmin = k_('frames_min')
    out = dict(method='camera_side_all_points (F-I4.15.1)', slab_points=int(k.sum()), plus=int(Sp.sum()),
               minus=int(Sm.sum()), plus_frames=int(len(np.unique(Fk[Sp]))),
               minus_frames=int(len(np.unique(Fk[Sm]))), ok=False)
    good = [int(S_.sum()) >= K['plane_min'] and len(np.unique(Fk[S_])) >= fmin for S_ in (Sp, Sm)]
    if not all(good):
        out.update(checks=dict(sides=False), why='t_all_points_fail')
        return out
    mp, mm = float(np.median(sk[Sp])), float(np.median(sk[Sm]))
    t = mp - mm
    mid = 0.5 * (mp + mm)
    faces = []
    for S_, m in ((Sp, mp), (Sm, mm)):
        f, v = Fk[S_], sk[S_]
        o = np.argsort(f, kind='stable')
        f, v = f[o], v[o]
        uf, st = np.unique(f, return_index=True)
        med = np.array([np.median(x) for x in np.split(v, st[1:])])
        faces.append(dict(n_pts=int(S_.sum()), frames=int(len(uf)), frame_range=[int(uf.min()), int(uf.max())],
                          median_offset_mm=round((m - mid) * 1e3, 3),
                          per_frame_median_offset_mm_5_50_95=[round((float(np.percentile(med, q)) - mid) * 1e3, 3)
                                                              for q in (5, 50, 95)]))
    chk = dict(sides=True, material_between=bool(t > 0), window=bool(K['slab'][0] <= t <= K['slab'][1]))
    out.update(t_m=float(t), t_mm=round(t * 1e3, 3), mid_n=a.tolist(), mid_d=float(mid), faces=faces, checks=chk,
               ok=all(chk.values()))
    if not out['ok']:
        out['why'] = 't_all_points_fail'
    return out


def _m_seen_all(P, Cm, a, d_ref, seen, K):
    """F-I4.15.1 one-face plate: median a . x of the seen side over all near points in the slab."""
    a = np.asarray(a, np.float64)
    a = a / np.linalg.norm(a)
    s = P @ a
    k = np.abs(s - float(d_ref)) <= K['slab'][1]
    view = np.einsum('ij,j->i', Cm[k] - P[k], a)
    S_ = view > 0 if seen > 0 else view < 0
    return (float(np.median(s[k][S_])) if S_.any() else None), int(S_.sum())


# ------------------------------------------------------------------------------------------------ F-I4.15 body
def _state_shares(ev, X):
    """Shares of the points X in FREE / UNKNOWN / OBSERVED voxels of the object's own grid (and outside it)."""
    lin, ok = ev.grid.lin(X)
    st = np.full(len(X), -1)
    st[ok] = ev.state[lin[ok]]
    n = max(len(X), 1)
    return dict(points=int(len(X)), free=round(float((st == IL.STATE_FREE).sum()) / n, 4),
                unknown=round(float((st == IL.STATE_UNKNOWN).sum()) / n, 4),
                observed=round(float((st == IL.STATE_OBSERVED).sum()) / n, 4),
                outside_grid=round(float((st == -1).sum()) / n, 4))


def _frame_grid(body, g):
    A = np.asarray(body['axes'], np.float64)
    c = np.asarray(body['centre'], np.float64)
    h = np.asarray(body['half'], np.float64)
    ax = [np.arange(-h[i] + g / 2, h[i], g) for i in range(3)]
    Q = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    return c + Q @ A, Q


def in_body(body, X):
    """Inside the plate body: the F-I4.15 polygon prism (|w| <= t / 2 and (u, v) inside the polygon) when the body
    carries a polygon, else the F-I4.2 box."""
    if 'poly' not in body:
        return in_box(body, X)
    A = np.asarray(body['axes'], np.float64)
    c = np.asarray(body['centre'], np.float64)
    Q = (np.asarray(X, np.float64).reshape(-1, 3) - c) @ A.T
    R = np.asarray(body['poly'], np.float64)
    k = (np.abs(Q[:, 2]) <= float(body['half'][2]) + 1e-12) & (Q[:, 0] >= R[:, 0].min()) & \
        (Q[:, 0] <= R[:, 0].max()) & (Q[:, 1] >= R[:, 1].min()) & (Q[:, 1] <= R[:, 1].max())
    out = np.zeros(len(Q), bool)
    if k.any():
        out[np.nonzero(k)[0]] = pip(R * 1e3, Q[k, :2] * 1e3)
    return out


def plate_body_poly(b, obj, info, ev):
    """PREREG F-I4.15.2 (post hoc, replaces the F-I4.2 rectangle body): (a) the F-I4.2 raster and min-area rectangle
    give the frame (a_L, a_W, a_T, centre, L, W; fill reported, no 0.9 gate); (b) the same slab points rasterised again
    at 2 mm along (a_L, a_W) with cell edges on the rectangle's sides, same cell rules; (c) outer ring of the
    component's cells, collinear vertices removed, Douglas-Peucker 1.0 mm split at the two farthest vertices; must be
    simple, else the unsimplified ring (flag outline_unsimplified), else plate_outline_not_simple; (d) body = the
    polygon extruded to +-t / 2 about the mid plane, no balls; (e) reported: areas, I-shape widths, vertex / reflex
    counts, FREE share of the polygon body and of the full rectangle body at the same t."""
    fr0 = plate_body(b, obj, info)
    out = dict(obj=obj, fi4_rev=15, flags=['plate_body_no_markers'], balls=[],
               source='observed outline polygon (F-I4.15.2; no STRUCT plate candidate)',
               frame=dict(method='F-I4.2 min-area rectangle of the outline (frame only, F-I4.15.2 (a))',
                          **{k: fr0.get(k) for k in ('L_mm', 'W_mm', 'fill', 'component_cells', 'cells',
                                                     'points_in_slab')}))
    if 'box' not in fr0:
        out.update(ok=False, why=fr0.get('why', 'empty_outline'))
        return out
    box = fr0['box']
    A = np.asarray(box['axes'], np.float64)
    c0 = np.asarray(box['centre'], np.float64)
    L, W = 2 * float(box['half'][0]), 2 * float(box['half'][1])
    t = float(info['t_m'])
    P, F = info['_P'], info['_F']
    n = A[2]
    sig = b.sigma(obj)
    k = np.abs(P @ n - info['mid_d']) <= t / 2 + k_('slab_sigma') * sig
    r = k_('raster_m')
    U = (P[k] - c0) @ A[0] + L / 2
    V = (P[k] - c0) @ A[1] + W / 2
    ij = np.stack([np.floor(U / r), np.floor(V / r)], 1).astype(np.int64)
    lo = ij.min(0)
    ij -= lo
    shp = ij.max(0) + 1
    key = np.unique(np.stack([ij[:, 0], ij[:, 1], np.asarray(F)[k].astype(np.int64)], 1), axis=0)
    cnt = np.zeros(shp, np.int32)
    np.add.at(cnt, (key[:, 0], key[:, 1]), 1)
    M = cnt >= k_('frames_min')
    M = ndimage.binary_closing(np.pad(M, 2), structure=np.ones((3, 3)))[2:-2, 2:-2]
    M = ndimage.binary_fill_holes(M)
    lab, nl = ndimage.label(M, structure=np.ones((3, 3)))
    if nl == 0:
        out.update(ok=False, why='empty_outline')
        return out
    comp = lab == int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
    loops, pinch = mask_ring(comp)
    out['raster'] = dict(axes='rectangle (a_L, a_W)', cells=int(comp.sum()), cell_area_cm2=round(
        float(comp.sum()) * r * r * 1e4, 2), pinch_vertices=int(pinch), loops=len(loops))
    if len(loops) != 1:
        out.update(ok=False, why='plate_outline_not_simple')
        return out
    Rc = loops[0].astype(np.float64)
    raw = np.stack([((Rc[:, 0] + lo[0]) * r - L / 2) * 1e3, ((Rc[:, 1] + lo[1]) * r - W / 2) * 1e3], 1)
    raw = drop_collinear(raw)
    tol = k_('simplify_m') * 1e3
    simp = dp_ring(raw, tol)
    if ring_simple(simp):
        poly, used = simp, 'simplified'
    elif ring_simple(raw):
        poly, used = raw, 'unsimplified'
        out['flags'].append('outline_unsimplified')
    else:
        out.update(ok=False, why='plate_outline_not_simple')
        return out
    if poly_area(poly) < 0:
        poly = poly[::-1]
    nv = len(poly)
    refl = int(sum(_cr(poly[q - 1], poly[q], poly[(q + 1) % nv]) < 0 for q in range(nv)))
    u0, u1 = float(poly[:, 0].min()), float(poly[:, 0].max())
    Lp = u1 - u0
    us = np.arange(u0 + 0.5, u1, 1.0)
    wid = chord_widths(poly, us)
    fr = (us - u0) / Lp
    waist = float(np.median(wid[(fr >= 0.3) & (fr <= 0.7)]))
    e_lo, e_hi = wid[fr <= 0.1], wid[fr >= 0.9]
    ends = float(np.median(np.concatenate([e_lo, e_hi])))
    body = dict(axes=A.tolist(), centre=c0.tolist(), half=[L / 2, W / 2, t / 2], poly=(poly * 1e-3).tolist(),
                t=t, frame='rectangle frame of F-I4.15.2 (a): u along a_L, v along a_W, origin its centre')
    area = poly_area(poly)
    out.update(ok=True, box=body, L_mm=round(L * 1e3, 1), W_mm=round(W * 1e3, 1), t_mm=round(t * 1e3, 3),
               polygon=dict(used=used, tolerance_mm=tol, vertices_raw=int(len(raw)), vertices=int(nv),
                            reflex_vertices=refl, area_cm2=round(area * 1e-2, 2),
                            area_vs_cells=round(area * 1e-6 / max(float(comp.sum()) * r * r, 1e-12), 4),
                            extent_mm=[round(Lp, 1), round(float(poly[:, 1].max() - poly[:, 1].min()), 1)],
                            poly_mm=np.round(poly, 3).tolist()),
               widths_mm=dict(waist_30_70=round(waist, 1), ends_outer_10=round(ends, 1),
                              end_lo=round(float(np.median(e_lo)), 1), end_hi=round(float(np.median(e_hi)), 1),
                              end_minus_waist=round(ends - waist, 1), max=round(float(wid.max()), 1)),
               volume_cm3=round(area * t * 1e3 * 1e-3, 2))
    g = k_('grid_m')
    X, _ = _frame_grid(body, g)
    ins = in_body(body, X)
    fp, frt = _state_shares(ev, X[ins]), _state_shares(ev, X)
    out['free_share'] = dict(grid_mm=g * 1e3, polygon=fp, rectangle=frt,
                             polygon_free_cm3=round(fp['free'] * fp['points'] * g ** 3 * 1e6, 2),
                             rectangle_free_cm3=round(frt['free'] * frt['points'] * g ** 3 * 1e6, 2),
                             ratio_polygon_to_rectangle=round(fp['free'] / frt['free'], 3) if frt['free'] > 0 else None)
    return out


# ------------------------------------------------------------------------------------------------ F-I4.15 slot
def slot_for_poly(side, comp, R_lin, body, t_partner, run, partner_plane=None):
    """PREREG F-I4.15.3: frame, d, entry side, c_L (F-I4.12, middle of the rectangle-based depth range), the slot
    bottom b and the slot box as F-I4.3 in the rectangle frame (slot_for); then the polygon's entry edge u_e (its
    outermost coordinate along s_e a_W inside the band |u - c_L| <= w / 2) and D = s_e (u_e - b), P = D - 2 mm."""
    sl = slot_for(side, comp, R_lin, body, t_partner, run, partner_plane=partner_plane)
    if not sl['ok']:
        return sl
    w, c_L, D_r, s_e, u_r = sl['_w'], sl['_c_L'], sl['_D'], sl['_s_e'], sl['_u_e']
    bot = u_r - s_e * D_r
    R = np.asarray(body['poly'], np.float64) * 1e3
    band = clip_rect(R, (c_L - w / 2) * 1e3, (c_L + w / 2) * 1e3, -np.inf, np.inf)
    sl.update(D_rect_mm=sl['D_mm'], P_rect_mm=sl['P_mm'], u_rect_mm=round(u_r * 1e3, 2),
              bottom_mm=round(bot * 1e3, 2))
    if len(band) < 3:
        sl.update(ok=False, why='slot_band_outside_polygon')
        return sl
    u_e = s_e * float(np.max(s_e * band[:, 1])) * 1e-3
    D = s_e * (u_e - bot)
    sl.update(u_e_poly_mm=round(u_e * 1e3, 2), D_mm=round(D * 1e3, 2),
              P_mm=round((D - k_('depth_margin_m')) * 1e3, 2), entry_edge_shift_mm=round(s_e * (u_r - u_e) * 1e3, 2),
              depth_from='the polygon edge at the slot mouth (F-I4.15.3)')
    sl['_D'], sl['_u_e'], sl['_u_rect'], sl['_bot'] = D, u_e, u_r, bot
    return sl


def crossing_extent_poly(body_o, body_p, T_op, d_o):
    """F-I4.15.3 W_x: 2 mm grid points inside both unslotted polygon bodies at the median assembled relative pose;
    extent along d_o (max - min + one pitch)."""
    g = k_('grid_m')
    X, _ = _frame_grid(body_o, g)
    X = X[in_body(body_o, X)]
    Ti = np.linalg.inv(T_op)
    k = in_body(body_p, X @ Ti[:3, :3].T + Ti[:3, 3])
    if not k.any():
        return 0.0, 0
    s = X[k] @ (np.asarray(d_o, np.float64) / np.linalg.norm(d_o))
    return float(s.max() - s.min() + g), int(k.sum())


def _extent_along(body, R_mm, d):
    A = np.asarray(body['axes'], np.float64)
    t = float(body['half'][2])
    d = np.asarray(d, np.float64) / np.linalg.norm(d)
    s2 = (np.asarray(R_mm, np.float64) * 1e-3) @ np.stack([A[0] @ d, A[1] @ d])
    e = (s2.max() - s2.min()) if len(s2) else 0.0
    return float(e + 2 * t * abs(A[2] @ d)) if len(s2) else 0.0


def _footprint(slot):
    """Slot box section in the mid plane, mm: (u0, u1, v0, v1)."""
    w, c_L, s_e, u_r, bot = slot['_w'], slot['_c_L'], slot['_s_e'], slot['_u_rect'], slot['_bot']
    mouth = u_r + s_e * k_('extend_m')
    v0, v1 = sorted([mouth, bot])
    return ((c_L - w / 2) * 1e3, (c_L + w / 2) * 1e3, v0 * 1e3, v1 * 1e3)


def slotted_polygon(R_mm, fp):
    """The polygon minus the slot footprint (Weiler-Atherton); a vertex on a footprint edge nudges the footprint
    outward by 1e-6 mm (up to 5 times; reported)."""
    u0, u1, v0, v1 = fp
    for q in range(6):
        e = 1e-6 * q
        try:
            res = poly_minus_rect(R_mm, u0 - e, u1 + e, v0 - e, v1 + e)
            res['nudge_mm'] = e
            return res
        except Degenerate:
            continue
    return dict(rings=[], hole=False, why='degenerate', nudge_mm=None)


def slot_budget_poly(side, body, slot, d, carved_before_cm3=0.0):
    """F-I4.15.3 budget (F-I4.4 thresholds): volume share = area(footprint & polygon) / area(polygon) (cumulative vs
    the round-0 body), reach along d <= 0.6, topology: polygon minus footprint is one simple polygon without holes, the
    bottom b lies inside the polygon, and both prongs (polygon beside the slot band between u_e and b) have area > 0."""
    R = np.asarray(body['poly'], np.float64) * 1e3
    t_mm = float(body['half'][2]) * 2e3
    fp = _footprint(slot)
    inter = clip_rect(R, *fp)
    a_in = abs(poly_area(inter)) if len(inter) else 0.0
    vol = a_in * t_mm                                             # mm3
    a_body = poly_area(R)
    body_vol = a_body * t_mm
    share = (carved_before_cm3 * 1e3 + vol) / body_vol
    reach = (_extent_along(body, inter, d) if len(inter) else 0.0) / max(_extent_along(body, R, d), 1e-12)
    res = slotted_polygon(R, fp)
    rings = res['rings']
    one = bool(len(rings) == 1 and not res['hole'] and ring_simple(rings[0]))
    area_ok = bool(one and abs(poly_area(rings[0]) - (a_body - a_in)) <= 1e-6 * a_body)
    c_L, w, u_e, bot = slot['_c_L'] * 1e3, slot['_w'] * 1e3, slot['_u_e'] * 1e3, slot['_bot'] * 1e3
    b_in = bool(pip(R, np.array([[c_L, bot]]))[0])
    vl, vh = sorted([u_e, bot])
    pr = [abs(poly_area(clip_rect(R, -np.inf, c_L - w / 2, vl, vh))),
          abs(poly_area(clip_rect(R, c_L + w / 2, np.inf, vl, vh)))]
    topo = bool(one and area_ok and b_in and pr[0] > 0 and pr[1] > 0)
    ok = bool(share <= IL.K('budget_vol') and reach <= IL.K('budget_reach') and topo)
    out = dict(slot_cm3=round(vol * 1e-3, 3), body_cm3=round(body_vol * 1e-3, 2), vol_share=round(share, 4),
               reach=round(reach, 3), footprint_mm=[round(x, 2) for x in fp], one_simple_polygon=one,
               area_consistent=area_ok, bottom_inside=b_in, D_lt_W=b_in, prong_area_mm2=[round(x, 1) for x in pr],
               topology=topo, rings=len(rings), hole=bool(res['hole']), nudge_mm=res.get('nudge_mm'), ok=ok,
               _vol=vol * 1e-9)
    if one:
        out['_slotted_ring'] = rings[0]
    return out


# ------------------------------------------------------------------------------------------------ F-I4.15 pieces
def prism(body, P_mm):
    A = np.asarray(body['axes'], np.float64)
    c = np.asarray(body['centre'], np.float64)
    h = float(body['half'][2])
    Q = np.asarray(P_mm, np.float64) * 1e-3
    B = c + Q[:, :1] * A[0] + Q[:, 1:2] * A[1]
    return np.vstack([B - h * A[2], B + h * A[2]])


def pieces_poly(body, R_mm, cap):
    """F-I4.15.4: exact convex partition (ear clipping + Hertel-Mehlhorn, <= 32 vertices per part) of the ring R_mm,
    each part extruded to +-t / 2 (<= 64 vertices per prism). Returns (hulls, info: count, cap, over_cap, tiling)."""
    parts = convex_partition(R_mm, k_('part_vmax'))
    hulls = [prism(body, P) for P in parts]
    a_r = abs(poly_area(R_mm))
    a_p = float(sum(poly_area(P) for P in parts))
    info = dict(n=len(parts), cap=int(cap), over_cap=bool(len(parts) > cap),
                max_vertices_per_prism=int(max(2 * len(P) for P in parts)) if parts else 0,
                all_convex=bool(all(convex_ok(P) for P in parts)), ring_area_mm2=round(a_r, 3),
                parts_area_mm2=round(a_p, 3), tiling_diff_mm2=round(abs(a_p - a_r), 6),
                tiling_ok=bool(abs(a_p - a_r) <= 1.0), method='ear clipping + Hertel-Mehlhorn (F-I4.15.4)')
    return hulls, info


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
    pi0 = {s.name: _plate(s, b) for s, _, _ in S}
    pi = {so.name: resolve_one_face(pi0[so.name], pi0[sp.name]),       # F-I4.14 step 3
          sp.name: resolve_one_face(pi0[sp.name], pi0[so.name])}
    so._plate_fi4_resolved, sp._plate_fi4_resolved = pi[so.name], pi[sp.name]
    W = dict(rule=WAIVER_REF, fi4_rev=REV,
             plate={n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in pi.items()})
    in_scope = all(pi[s.name]['plate'] for s, _, _ in S) and all(c.run.kind == 'INSERTION' for _, c, _ in S)
    W['in_scope'] = bool(in_scope)
    if not in_scope:
        W['why_out'] = ('not plate-like: ' + ', '.join(n for n, x in pi.items() if not x['plate'])
                        if not all(x['plate'] for x in pi.values()) else 'run kinds ' +
                        ', '.join(c.run.kind for _, c, _ in S))
        for _, _, r in S:
            r['waiver_fi4'] = W
        return
    for s_, _, r in S:
        r['flags'].append('owner_waiver_fi4')
        r['flags'] += [f for f in pi[s_.name].get('flags', []) if f not in r['flags']]     # F-I4.14 plate flags

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
    poly = REV >= 15                                       # PREREG F-I4.15: polygon body, prisms, D from its edge
    for s, c, r in S:
        bd = plate_body_poly(b, s.name, pi[s.name], s.ev) if poly else plate_body(b, s.name, pi[s.name])
        bodies[s.name] = bd
    W['body'] = {n: {k: v for k, v in x.items()} for n, x in bodies.items()}
    for n, bd in bodies.items():
        if not bd['ok']:
            return fail(bd.get('why', 'plate_body'))
    defaults = {}
    if poly:                                               # F-I4.15.4 default prisms, cap floor(165 / objects)
        cap = k_('shapes_max') // max(1, len(b.objects))
        for s, c, r in S:
            R_mm = np.asarray(bodies[s.name]['box']['poly'], np.float64) * 1e3
            defaults[s.name], dinf = pieces_poly(bodies[s.name]['box'], R_mm, cap)
            W['body'][s.name]['default_pieces'] = dinf
        if any(W['body'][n]['default_pieces']['over_cap'] for n in bodies):
            return fail('plate_body_over_cap')
    # F-I4.3 slots
    for (s, c, r), (s2, _, _) in zip(S, S[::-1]):
        T = IL._asm_pose(s.intr, c.run)                     # T_{s<-s2}, the median assembled relative pose
        n2 = T[:3, :3] @ np.asarray(pi[s2.name]['mid_n'], np.float64)
        d2 = float(pi[s2.name]['mid_d']) + float(n2 @ T[:3, 3])
        sl = (slot_for_poly if poly else slot_for)(s, c, c.region(), bodies[s.name]['box'], pi[s2.name]['t_m'], c.run,
                                                   partner_plane=(n2, d2))
        slots[s.name] = sl
    W['slot'] = {n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in slots.items()}
    for n, sl in slots.items():
        if not sl['ok']:
            return fail(sl['why'])
    T_op = IL._asm_pose(so.intr, co.run)
    Wx, npts = (crossing_extent_poly if poly else crossing_extent)(bodies[so.name]['box'], bodies[sp.name]['box'],
                                                                    T_op, co.run.d)
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
        bud[s.name] = (slot_budget_poly if poly else slot_budget)(s, bodies[s.name]['box'], slots[s.name], c.run.d,
                                                                  carved_before_cm3=s.carved_cm3_before)
    W['budget'] = {n: {k: v for k, v in x.items() if not k.startswith('_')} for n, x in bud.items()}
    if not all(x['ok'] for x in bud.values()):
        return fail('budget_iv', push=True, why='budget (iv) / topology on the analytic slot (F-I4.4)')
    slotted_by = {}
    if poly:                                               # F-I4.15.4 slotted prisms (polygon minus the footprint)
        for s, c, r in S:
            sh, sinf = pieces_poly(bodies[s.name]['box'], bud[s.name]['_slotted_ring'], cap)
            slotted_by[s.name] = sh
            W['body'][s.name]['slotted_pieces'] = sinf
        if any(W['body'][n]['slotted_pieces']['over_cap'] for n in bodies):
            return fail('plate_body_over_cap')
    # pass: CARVE both (simulator copy only)
    for s, c, r in S:
        if poly:
            slotted, sboxes, default = slotted_by[s.name], None, defaults[s.name]
        else:
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
