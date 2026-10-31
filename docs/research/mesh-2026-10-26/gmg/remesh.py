"""Watertight remesh of generated meshes (module M10 of SPEC section 7; build step B3; PREREG B.10).

  watertight(mesh, pitch=0.0015, budget=4000) -> (mesh, info)

SPEC section 7 M10: "Generalised winding number or SDF voxelisation, marching cubes, largest-component cleanup, then
program.fit_budget(..., 4000). Mandatory for every generated mesh." Generated meshes are often open, self-overlapping,
inconsistently oriented or non-manifold (raw outputs watertight: SAM 3D 13/20, Hunyuan 6/20, Pixal3D-MV 0/20,
TRELLIS.2 0/20 [M]).

Method (pure numpy / scipy / scikit-image; GT-free geometry, no file access):
  1. Clean the input (merge vertices, drop degenerate and duplicate faces; repair the orientation if it is not
     winding-consistent). Large inputs are decimated for the queries (fast_simplification, the kit's decimator):
     <= QUERY_FACES for the votes and distances, <= GWN_FACES for the exact winding-number refinement.
  2. Node grid at PITCH (1.5 mm, SPEC M10) over the bounds plus PAD nodes, its origin shifted by GRID_SHIFT pitch.
  3. Inside test = generalised winding number >= 0.5 (Jacobson et al. 2013), estimated per node by ray votes along
     the six axis directions (+-x, +-y, +-z), the ray-voting idea of Nooruddin and Turk (2003): a ray votes "inside" if
     its signed crossing count (a face crossed adds the sign of its normal along the ray) is non-zero or its crossing
     count is odd. For a closed, consistently oriented mesh every ray gives the winding number (overlapping bodies
     included: signed count 2); the parity keeps the vote when orientation repair failed; for an open mesh the GWN
     is the solid-angle mean of the crossing count over all directions, which the six-direction share approximates.
     A node is inside if more than half of the six rays vote inside. Nodes near the surface with 2-4 inside votes
     are ambiguous and get the exact GWN (geom.winding_number, solid angles) of the query mesh (at most REFINE_MAX,
     nearest the surface first; the rest keep the vote, 3 of 6 = outside).
  4. Occupancy cleanup: enclosed outside regions (not connected to the grid boundary) are filled; the largest
     6-connected inside component is kept (largest-component cleanup on the solid, so floaters and noise bubbles go).
  5. Unsigned distance: exact point-triangle distance (geom.Closest) at nodes within BAND of the surface (candidates
     from the surface samples' cells, then a KD-tree on dense surface samples); farther nodes get BAND (only the sign
     matters there). Signed distance = -d inside.
  6. Marching cubes (Lewiner) at level 0; outward orientation; the largest connected component by volume is kept.
  7. Thin parts: coverage = share of input surface samples within PITCH of the result. Below COVER_MIN (sheets or
     walls thinner than the grid vanish) the occupancy is redone as the union with a shell of half-thickness THIN_H
     around the input surface (flag thin_union) and kept if its coverage is higher.
  8. autokit.program.fit_budget(mesh, [], 4000), checked with the kit decode (float32 vertices, the gmg's copy of the
     kit's budget_mesh, zero-area faces dropped: V1) and accepted only if the decimation changed the area by at most
     AREA_TOL. If no budget in BUDGET_RETRY is accepted (a dense, high-genus marching-cubes surface can defeat the
     decimator), steps 5-8 are redone on a coarser grid (PITCH_FALLBACK, flag pitch_fallback), whose surface decimates
     more gently. If nothing is accepted, the last try is returned (info accepted False; it may still be watertight).

The constants with a model meaning are registered with the guard (pitch, budget); the others are numerical (caps,
band, padding, retry ladders) and documented here.
"""
from __future__ import annotations

import math
import time

import numpy as np
import trimesh

from gmg import geom

PITCH = 0.0015              # SPEC section 7 M10
BUDGET = 4000               # PREREG A.6 'remesh, budget' (kit 4096)
PAD = 3                     # nodes of free margin around the bounds (marching cubes needs an outside layer)
GRID_SHIFT = 0.3819660113   # grid origin shifted by this fraction of a pitch (golden-ratio conjugate), so nodes do not
                            # sit exactly on the axis-aligned planes of synthetic / CAD inputs (zero signed distances
                            # give degenerate marching-cubes slivers)
BAND_NODES = 2.0            # exact distances within 2 pitches of the surface (+ the sample spacing)
QUERY_FACES = 100_000       # votes and distances on at most this many faces (decimated copy)
GWN_FACES = 3_000           # exact-GWN refinement on at most this many faces (decimated copy)
REFINE_MAX = 5_000          # at most this many ambiguous nodes get the exact GWN (nearest the surface first)
COVER_MIN = 0.90            # coverage below this triggers the thin-part retry
THIN_H = 0.75               # half-thickness of the thin-part shell, in pitches
MAX_NODES = 24_000_000      # grid size cap (memory); the pitch is raised above it (flag pitch_raised)
COVER_SAMPLES = 20_000      # input surface samples for the coverage
BUDGET_RETRY = (0, 8, 24, 64, 128, 256)   # budget reductions tried until the kit decode stays watertight
AREA_TOL = 0.05             # a budgeted mesh is accepted only if the decimation changed the surface area by <= 5 %
                            # (fit_budget's last resort can return a far coarser mesh: -25 % area on a noisy surface)
PITCH_FALLBACK = (2.0, 3.0, 4.0)          # pitch multiples tried when no budget decodes watertight
SEED = 0


def consts():
    from gmg import guard
    return dict(pitch=guard.constant('remesh_pitch_m', PITCH, 'generic:SPEC section 7 M10 remesh pitch 1.5 mm'),
                budget=guard.constant('remesh_budget_faces', BUDGET, 'kit:PREREG A.6 4000 faces (kit 4096)'))


# ------------------------------------------------------------------------------------------------ input cleanup
def clean(mesh):
    """Merged, degenerate-free, duplicate-free copy; orientation repaired if not winding-consistent."""
    V = np.asarray(mesh.vertices, np.float64)
    F = np.asarray(mesh.faces, np.int64)
    m = trimesh.Trimesh(V, F, process=True)
    if len(m.faces):
        m.update_faces(m.nondegenerate_faces(height=1e-12))
        m.update_faces(m.unique_faces())
        m.remove_unreferenced_vertices()
    info = dict(faces_in=int(len(F)), faces_clean=int(len(m.faces)), watertight_in=bool(m.is_watertight),
                winding_consistent_in=bool(m.is_winding_consistent) if len(m.faces) else None)
    return m, info


def decimated(m, n):
    if len(m.faces) <= n:
        out = m
    else:
        import fast_simplification
        v, f = fast_simplification.simplify(np.asarray(m.vertices), np.asarray(m.faces), target_count=int(n))
        out = trimesh.Trimesh(v, f, process=True)
    if len(out.faces) and not out.is_winding_consistent:
        out = out.copy()
        trimesh.repair.fix_normals(out, multibody=True)
    return out


# ------------------------------------------------------------------------------------------------ ray votes
def axis_votes(tris, lo, shape, pitch):
    """Six-direction ray votes at every node: (share (shape) float32 in [0, 1] of rays voting inside, signed (6, shape)
    int16 crossing counts). For each axis a the rays run along the grid columns (offset by a tiny fixed amount so a ray
    never meets a vertex or an edge exactly); a crossing above the node counts for the +a ray, one below for the -a ray;
    a ray votes inside if its signed count is non-zero or its crossing count is odd."""
    shape = tuple(int(s) for s in shape)
    inside_votes = np.zeros(shape, np.int8)
    signed = np.zeros((6,) + shape, np.int16)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    eps = 1e-4 * pitch * np.array([0.6180339887, 0.4142135624])
    for a in range(3):
        uv = [k for k in range(3) if k != a]
        nu, nv = shape[uv[0]], shape[uv[1]]
        cu = lo[uv[0]] + np.arange(nu) * pitch + eps[0]
        cv = lo[uv[1]] + np.arange(nv) * pitch + eps[1]
        Q = np.stack(np.meshgrid(cu, cv, indexing='ij'), -1).reshape(-1, 2)          # column c = iu * nv + iv
        T2 = tris[:, :, uv]
        ext = float(np.ptp(T2.reshape(-1, 2), axis=0).max())
        cell = max(ext / 256.0, pitch)
        qi, ti, b1, b2 = geom.pairs2d(T2, Q, cell)
        s = np.sign(nrm[ti, a]).astype(np.int64)
        keep = s != 0                                                                # faces parallel to the ray
        qi, ti, b1, b2, s = qi[keep], ti[keep], b1[keep], b2[keep], s[keep]
        h = tris[ti, 0, a] + b1 * (tris[ti, 1, a] - tris[ti, 0, a]) + b2 * (tris[ti, 2, a] - tris[ti, 0, a])
        na = shape[a]
        span = float(na * pitch + 1.0)
        key = qi.astype(np.float64) * span + (h - lo[a])
        o = np.argsort(key, kind='stable')
        key, s_sorted = key[o], s[o]
        cs = np.concatenate([[0], np.cumsum(s_sorted)])
        ncol = len(Q)
        cols = np.arange(ncol, dtype=np.float64)
        c0 = np.searchsorted(key, cols * span, 'left')
        c1 = np.searchsorted(key, (cols + 1) * span, 'left')
        z = np.arange(na) * pitch
        pos = np.searchsorted(key, (cols[:, None] * span + z[None, :]).ravel(), 'right').reshape(ncol, na)
        below_s = cs[pos] - cs[c0][:, None]
        below_n = pos - c0[:, None]
        up_s = (cs[c1] - cs[c0])[:, None] - below_s
        up_n = (c1 - c0)[:, None] - below_n
        perm = np.argsort([uv[0], uv[1], a])                                         # axes (u, v, a) -> (0, 1, 2)
        for j, (sg, n) in enumerate(((up_s, up_n), (-below_s, below_n))):
            vote = (sg != 0) | (n % 2 == 1)
            inside_votes += np.transpose(vote.reshape(nu, nv, na), perm).astype(np.int8)
            signed[2 * a + j] = np.transpose(np.clip(sg, -32000, 32000).reshape(nu, nv, na), perm)
    return inside_votes.astype(np.float32) / 6.0, signed


# ------------------------------------------------------------------------------------------------ the remesh
def _grid(m, pitch):
    lo = np.asarray(m.bounds[0], np.float64) - (PAD + GRID_SHIFT) * pitch
    hi = np.asarray(m.bounds[1], np.float64) + PAD * pitch
    shape = np.ceil((hi - lo) / pitch).astype(np.int64) + 1
    return lo, shape


def _distance(mq, lo, shape, pitch, info):
    """Unsigned distance at every node (exact within the band, BAND elsewhere) and the dense surface samples."""
    from scipy import ndimage
    from scipy.spatial import cKDTree
    area = float(mq.area)
    n = int(min(3_000_000, max(20_000, 4.0 * area / pitch ** 2)))
    P, _ = geom.surface_samples(mq, n, seed=SEED)
    spacing = math.sqrt(area / max(n, 1))
    band = BAND_NODES * pitch + spacing
    cell = np.zeros(shape, bool)
    ij = np.clip(np.floor((P - lo) / pitch + 0.5).astype(np.int64), 0, np.asarray(shape) - 1)
    cell[tuple(ij.T)] = True
    r = int(math.ceil(band / pitch)) + 1
    cand = ndimage.binary_dilation(cell, structure=np.ones((3, 3, 3), bool), iterations=r)
    ci = np.nonzero(cand.ravel())[0]
    X = lo + np.stack(np.unravel_index(ci, shape), 1) * pitch
    dk, _ = cKDTree(P).query(X, k=1, distance_upper_bound=band)
    near = np.isfinite(dk)
    d = np.full(int(np.prod(shape)), band, np.float64)
    if near.any():
        dn, _, _ = geom.Closest(mq).query(X[near])
        d[ci[near]] = np.minimum(dn, band)
    info.update(near_nodes=int(near.sum()), band_m=round(band, 6))
    return d.reshape(shape), P, band


def _occupancy(mq, lo, shape, pitch, d, info):
    from scipy import ndimage
    t = time.time()
    share, signed = axis_votes(geom._tris(mq), lo, shape, pitch)
    info['t_votes_s'] = round(time.time() - t, 2)
    inside = share > 0.5
    near = d < np.max(d)
    amb = near & (share >= 2 / 6 - 1e-6) & (share <= 4 / 6 + 1e-6)
    info['ambiguous_nodes'] = int(amb.sum())
    info['signed_vote_disagree'] = int(((share > 0.5) != (np.abs(signed).mean(0) >= 0.5)).sum())
    t = time.time()
    if amb.any():
        ia = np.nonzero(amb.ravel())[0]
        if len(ia) > REFINE_MAX:
            info.setdefault('flags', []).append('refine_capped')
            ia = ia[np.argsort(d.ravel()[ia], kind='stable')[:REFINE_MAX]]
        mg = decimated(mq, GWN_FACES)
        X = lo + np.stack(np.unravel_index(ia, shape), 1) * pitch
        g = np.abs(geom.winding_number(mg, X)) >= 0.5
        flat = inside.ravel()
        flat[ia] = g
        inside = flat.reshape(shape)
        info['refined_nodes'] = int(len(ia))
        info['gwn_faces'] = int(len(mg.faces))
    info['t_refine_s'] = round(time.time() - t, 2)
    return _cleanup(inside, info)


def _cleanup(inside, info):
    """Enclosed outside regions filled; the largest 6-connected inside component kept."""
    from scipy import ndimage
    n0 = int(inside.sum())
    inside = ndimage.binary_fill_holes(inside)
    info['enclosed_filled_nodes'] = int(inside.sum()) - n0
    lab, nlab = ndimage.label(inside)
    info['inside_components'] = int(nlab)
    if nlab > 1:
        sz = np.bincount(lab.ravel())
        sz[0] = 0
        k = int(np.argmax(sz))
        info['inside_kept_share'] = round(float(sz[k] / sz.sum()), 6)
        inside = lab == k
    return inside


def _mc(sdf, lo, pitch):
    from skimage import measure
    if not (sdf.min() < 0 < sdf.max()):
        return None
    v, f, _, _ = measure.marching_cubes(sdf.astype(np.float32), level=0.0, spacing=(pitch,) * 3, method='lewiner',
                                        allow_degenerate=False)
    m = trimesh.Trimesh(v + lo, f, process=True)
    if m.is_watertight and m.volume < 0:
        m.invert()
    return m


def _largest(m, info):
    parts = m.split(only_watertight=False)
    info['components'] = int(len(parts))
    if len(parts) <= 1:
        info['kept_volume_share'] = 1.0
        return m
    vols = np.array([abs(p.volume) if p.is_watertight else 0.0 for p in parts])
    k = int(np.argmax(vols)) if vols.max() > 0 else int(np.argmax([len(p.faces) for p in parts]))
    info['kept_volume_share'] = round(float(vols[k] / max(vols.sum(), 1e-18)), 6)
    return parts[k]


def _coverage(P, out, pitch):
    if out is None or not len(out.faces):
        return 0.0
    rng = np.random.default_rng(SEED)
    S = P if len(P) <= COVER_SAMPLES else P[rng.choice(len(P), COVER_SAMPLES, replace=False)]
    d, _, _ = geom.Closest(out).query(S)
    return float((d <= pitch).mean())


def decode_watertight(m):
    """V1 on an in-memory mesh: float32 vertices (the GLB round trip), the gmg's copy of the kit decode, zero-area
    faces dropped (score.decoded_mesh), watertight."""
    from gmg import score
    v32 = np.asarray(m.vertices, np.float32).astype(np.float64)
    try:
        v, f = score.kit_decode(trimesh.Trimesh(v32, np.asarray(m.faces), process=False))
    except ValueError:
        return False
    tri = v[f]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return bool(trimesh.Trimesh(v, f[ar > 1e-14], process=True).is_watertight)


def _budget(out, budget, pool):
    """fit_budget down the BUDGET_RETRY ladder; every try (mesh, record) is appended to POOL. Returns the accepted
    (mesh, tries) or (None, tries)."""
    from autokit import program
    tries = []
    for dr in BUDGET_RETRY:
        mb, binfo = program.fit_budget(out, [], int(budget) - dr)
        mb = trimesh.Trimesh(np.asarray(mb.vertices), np.asarray(mb.faces), process=True)
        if mb.is_watertight and mb.volume < 0:
            mb.invert()
        dec = decode_watertight(mb)
        da = binfo.get('solid_area_change')
        ok = bool(dec and (da is None or abs(da) <= AREA_TOL))
        rec = dict(budget=int(budget) - dr, faces=int(len(mb.faces)), watertight=bool(mb.is_watertight),
                   decode_watertight=dec, solid_area_change=da, accepted=ok)
        tries.append(rec)
        pool.append((mb, rec))
        if ok:
            return mb, tries
    return None, tries


def _surface(mq, lo, shape, pitch, info, thin_h=None):
    """Occupancy -> signed distance -> marching cubes -> largest component -> (mesh or None, samples)."""
    t = time.time()
    d, P, band = _distance(mq, lo, shape, pitch, info)
    info['t_udf_s'] = round(time.time() - t, 2)
    inside = _occupancy(mq, lo, shape, pitch, d, info)
    sdf = np.where(inside, -d, d)
    if thin_h is not None:                       # union with a shell of half-thickness thin_h around the surface
        sdf = np.minimum(sdf, d - thin_h)
        ins2 = _cleanup(sdf < 0, dict())
        sdf = np.where(ins2, -np.abs(sdf), np.abs(sdf))
    t = time.time()
    out = _mc(sdf, lo, pitch)
    if out is not None:
        out = _largest(out, info)
    info['t_mc_s'] = round(time.time() - t, 2)
    return out, P


def watertight(mesh, pitch=PITCH, budget=BUDGET):
    """SPEC section 7 M10. Returns (mesh within BUDGET faces, info). Raises ValueError on an empty input."""
    t0 = time.time()
    m, info = clean(mesh)
    if not len(m.faces):
        raise ValueError('remesh: empty mesh')
    flags = []
    info['flags'] = flags
    lo, shape = _grid(m, pitch)
    if int(np.prod(shape)) > MAX_NODES:
        pitch = float(pitch * (np.prod(shape) / MAX_NODES) ** (1 / 3) * 1.01)
        lo, shape = _grid(m, pitch)
        flags.append('pitch_raised')
    info.update(pitch_m=pitch, grid=[int(s) for s in shape], extent_m=np.round(m.extents, 5).tolist())
    t = time.time()
    mq = decimated(m, QUERY_FACES)
    info['faces_query'] = int(len(mq.faces))
    info['t_decimate_s'] = round(time.time() - t, 2)
    out, P = _surface(mq, lo, shape, pitch, info)
    cov = _coverage(P, out, pitch)
    info['coverage'] = round(cov, 4)
    if cov < COVER_MIN:
        flags.append('thin_union')
        info2 = dict(flags=[])
        out2, _ = _surface(mq, lo, shape, pitch, info2, thin_h=THIN_H * pitch)
        cov2 = _coverage(P, out2, pitch)
        info['thin_retry'] = dict(coverage=round(cov2, 4), components=info2.get('components'),
                                  kept_volume_share=info2.get('kept_volume_share'))
        if out2 is not None and cov2 > cov:
            out, cov = out2, cov2
            info['coverage_final'] = round(cov2, 4)
    if out is None or not len(out.faces):
        raise ValueError('remesh: no surface (the inside test found no inside node)')
    info['watertight_mc'] = bool(out.is_watertight)
    info['volume_m3'] = float(out.volume) if out.is_watertight else None
    info['faces_mc'] = int(len(out.faces))
    t = time.time()
    pool = []
    mb, tries = _budget(out, budget, pool)
    info['budget_tries'] = tries
    if len(tries) > 1:
        flags.append('budget_retry')
    if mb is None:
        for k in PITCH_FALLBACK:
            p2 = pitch * k
            lo2, shape2 = _grid(m, p2)
            i2 = dict(flags=[])
            out2, _ = _surface(mq, lo2, shape2, p2, i2, thin_h=(THIN_H * p2) if 'thin_union' in flags else None)
            if out2 is None:
                continue
            mb2, tries2 = _budget(out2, budget, pool)
            info.setdefault('pitch_fallback_tries', []).append(dict(pitch_m=p2, faces_mc=int(len(out2.faces)),
                                                                    tries=tries2))
            if mb2 is not None:
                flags.append('pitch_fallback')
                mb, out = mb2, out2
                info['pitch_final_m'] = p2
                info['coverage_fallback'] = round(_coverage(P, out2, pitch), 4)
                break
    if mb is None:                                # nothing accepted: the decoded-watertight try with the least area
        flags.append('budget_unaccepted')         # change, else the least area change overall
        mb, _ = min(pool, key=lambda x: (not x[1]['decode_watertight'], abs(x[1]['solid_area_change'] or 0)))
    final = next(r for m_, r in pool if m_ is mb)
    info['t_budget_s'] = round(time.time() - t, 2)
    info.update(faces_out=int(len(mb.faces)), vertices_out=int(len(mb.vertices)), watertight=bool(mb.is_watertight),
                decode_watertight=final['decode_watertight'], accepted=final['accepted'],
                area_change=final['solid_area_change'],
                t_total_s=round(time.time() - t0, 2))
    return mb, info
