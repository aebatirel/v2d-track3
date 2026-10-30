"""Mesh queries used by the gmg score and producers (build step B1). GT-free geometry only: no file access.

  surface_samples(mesh, n, seed)        area-weighted surface samples with their face ids (trimesh, seeded)
  winding_number(mesh, X)               generalised winding number (exact solid-angle sum, van Oosterom-Strackee),
                                        chunked in torch (CPU); >= 0.5 means inside (PREREG A.3 V2 (a))
  closest(mesh, X)                      exact unsigned distance to the surface and the normal of the nearest face
                                        (candidate faces from a KD-tree over dense surface samples, then exact
                                        point-triangle distances)
  inside(mesh, X)                       winding number >= 0.5: signed ray crossings for watertight meshes (exact for
                                        closed oriented meshes, overlaps included), checked against the exact winding
                                        number on a random subset (else exact for all)
  ray_ranges(tris_c, P_c)               exact first-hit range along camera rays (perspective bucketing; PREREG A.4)
  first_hit(mesh, O, D)                 brute-force Moller-Trumbore reference (tests)
  volume_samples(mesh, n, seed, axis)   uniform samples of the enclosed volume by column parity along one axis
                                        (watertight meshes; PREREG A.3 V4)

Constants here are numerical (chunk sizes, epsilons, sampling densities), not model constants; none is registered
with the guard.
"""
from __future__ import annotations

import numpy as np
import trimesh
from scipy.spatial import cKDTree

CHUNK = 192                 # queries per torch chunk (x faces): memory, not a model constant
EPS_DET = 1e-12             # Moller-Trumbore parallel-ray epsilon
T_MIN = 1e-6                # ray hits closer than 1 um to the origin are ignored
SAMPLE_SPACING = 0.0007     # closest(): dense surface samples about every 0.7 mm (candidate faces only)
K_FACES = 12                # closest(): candidate faces from the 12 nearest dense samples
_THREADS = None


def _torch():
    import torch
    global _THREADS
    if _THREADS is None:
        _THREADS = max(1, min(3, torch.get_num_threads()))
        torch.set_num_threads(_THREADS)
    return torch


def _tris(mesh):
    V = np.asarray(mesh.vertices, np.float64)
    F = np.asarray(mesh.faces, np.int64)
    return V[F]


def surface_samples(mesh, n, seed=0):
    """(points (n,3), face ids (n,)) area-weighted, reproducible (trimesh.sample.sample_surface with seed)."""
    if len(mesh.faces) == 0:
        return np.zeros((0, 3)), np.zeros(0, np.int64)
    P, fi = trimesh.sample.sample_surface(mesh, int(n), seed=seed)
    return np.asarray(P, np.float64), np.asarray(fi, np.int64)


def winding_number(mesh, X):
    """Generalised winding number of every query point (exact sum of signed solid angles / 4 pi)."""
    X = np.asarray(X, np.float64).reshape(-1, 3)
    if len(X) == 0 or len(mesh.faces) == 0:
        return np.zeros(len(X))
    torch = _torch()
    T = torch.from_numpy(_tris(mesh).astype(np.float32))      # (F,3,3); float32 is ample for the 0.5 cut
    out = np.empty(len(X))
    Xt = torch.from_numpy(X.astype(np.float32))
    for s in range(0, len(X), CHUNK):
        q = Xt[s:s + CHUNK, None, None, :]                    # (c,1,1,3)
        R = T[None] - q                                       # (c,F,3,3)
        a, b, c = R[:, :, 0], R[:, :, 1], R[:, :, 2]
        la, lb, lc = a.norm(dim=-1), b.norm(dim=-1), c.norm(dim=-1)
        det = (a * torch.cross(b, c, dim=-1)).sum(-1)
        den = la * lb * lc + (a * b).sum(-1) * lc + (b * c).sum(-1) * la + (c * a).sum(-1) * lb
        out[s:s + CHUNK] = (2.0 * torch.atan2(det, den)).sum(-1).numpy() / (4.0 * np.pi)
    return out


def _seg_dist2(X, A, B):
    ab = B - A
    ap = X - A
    h = np.clip(np.einsum('ij,ij->i', ap, ab) / np.maximum(np.einsum('ij,ij->i', ab, ab), 1e-30), 0.0, 1.0)
    d = ap - h[:, None] * ab
    return np.einsum('ij,ij->i', d, d)


def point_triangle_dist(X, A, B, C):
    """Exact distance from X[i] to triangle (A[i], B[i], C[i]); all (n,3)."""
    n = np.cross(B - A, C - A)
    nn = np.linalg.norm(n, axis=1)
    ok = nn > 1e-20
    nh = np.zeros_like(n)
    nh[ok] = n[ok] / nn[ok, None]
    dp = np.einsum('ij,ij->i', X - A, nh)
    P = X - dp[:, None] * nh
    # barycentric inside test of the projection
    v0, v1, v2 = B - A, C - A, P - A
    d00 = np.einsum('ij,ij->i', v0, v0); d01 = np.einsum('ij,ij->i', v0, v1); d11 = np.einsum('ij,ij->i', v1, v1)
    d20 = np.einsum('ij,ij->i', v2, v0); d21 = np.einsum('ij,ij->i', v2, v1)
    den = d00 * d11 - d01 * d01
    with np.errstate(divide='ignore', invalid='ignore'):
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
    inside = ok & (np.abs(den) > 1e-30) & (v >= 0) & (w >= 0) & (v + w <= 1)
    d2 = np.minimum(np.minimum(_seg_dist2(X, A, B), _seg_dist2(X, B, C)), _seg_dist2(X, C, A))
    d2 = np.where(inside, np.minimum(d2, dp * dp), d2)
    return np.sqrt(d2)


class Closest:
    """Reusable nearest-surface query structure for one mesh."""

    def __init__(self, mesh, seed=0):
        self.mesh = mesh
        self.T = _tris(mesh)
        self.fn = np.asarray(mesh.face_normals, np.float64) if len(mesh.faces) else np.zeros((0, 3))
        area = float(mesh.area) if len(mesh.faces) else 0.0
        n = int(min(2_000_000, max(20000, area / SAMPLE_SPACING ** 2)))
        P, fi = surface_samples(mesh, n, seed=seed)
        cen = self.T.mean(1)
        self.P = np.vstack([P, cen])                            # every face has at least its centroid
        self.fi = np.concatenate([fi, np.arange(len(cen))])
        self.tree = cKDTree(self.P) if len(self.P) else None

    def query(self, X):
        """(distance (n,), nearest face id (n,), normal of that face (n,3))."""
        X = np.asarray(X, np.float64).reshape(-1, 3)
        if len(X) == 0 or self.tree is None:
            return np.full(len(X), np.inf), np.full(len(X), -1), np.zeros((len(X), 3))
        k = min(K_FACES, len(self.P))
        _, idx = self.tree.query(X, k=k)
        idx = idx.reshape(len(X), -1)
        cand = self.fi[idx]                                     # (n,k) face ids (duplicates allowed)
        Xr = np.repeat(X, cand.shape[1], axis=0)
        cf = cand.ravel()
        d = point_triangle_dist(Xr, self.T[cf, 0], self.T[cf, 1], self.T[cf, 2]).reshape(cand.shape)
        j = d.argmin(1)
        face = cand[np.arange(len(X)), j]
        return d[np.arange(len(X)), j], face, self.fn[face]


def closest(mesh, X):
    return Closest(mesh).query(X)


def pairs2d(T2, Q, cell):
    """Candidate (query, triangle) pairs whose 2-D triangle contains the 2-D query point, exactly (bucketing on a
    square grid of side CELL, then a barycentric test). T2 (F,3,2), Q (n,2). Returns (qi, ti, b1, b2) with the
    barycentric coordinates of the query in the triangle (point = A + b1 (B - A) + b2 (C - A))."""
    T2 = np.asarray(T2, np.float64); Q = np.asarray(Q, np.float64)
    e = np.zeros(0, np.int64)
    if len(T2) == 0 or len(Q) == 0:
        return e, e, np.zeros(0), np.zeros(0)
    lo = np.minimum(T2.reshape(-1, 2).min(0), Q.min(0)) - cell
    tmin = np.floor((T2.min(1) - lo) / cell).astype(np.int64)
    tmax = np.floor((T2.max(1) - lo) / cell).astype(np.int64)
    ncol = int(max(tmax[:, 1].max(), np.floor((Q[:, 1] - lo[1]) / cell).max())) + 2
    nx = tmax[:, 0] - tmin[:, 0] + 1; ny = tmax[:, 1] - tmin[:, 1] + 1
    cnt = nx * ny
    tri = np.repeat(np.arange(len(T2)), cnt)
    off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    cx = tmin[tri, 0] + off // ny[tri]; cy = tmin[tri, 1] + off % ny[tri]
    key = cx * ncol + cy
    o = np.argsort(key, kind='stable'); key, tri = key[o], tri[o]
    qc = np.floor((Q - lo) / cell).astype(np.int64)
    qk = qc[:, 0] * ncol + qc[:, 1]
    a = np.searchsorted(key, qk, 'left'); b = np.searchsorted(key, qk, 'right')
    n = b - a
    qi = np.repeat(np.arange(len(Q)), n)
    if len(qi) == 0:
        return e, e, np.zeros(0), np.zeros(0)
    ti = tri[np.repeat(a, n) + (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n))]
    A = T2[ti, 0]; d1 = T2[ti, 1] - A; d2 = T2[ti, 2] - A; p = Q[qi] - A
    den = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = np.abs(den) > 1e-30
    den = np.where(ok, den, 1.0)
    b1 = (p[:, 0] * d2[:, 1] - d2[:, 0] * p[:, 1]) / den
    b2 = (d1[:, 0] * p[:, 1] - p[:, 0] * d1[:, 1]) / den
    ins = ok & (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)
    return qi[ins], ti[ins], b1[ins], b2[ins]


def winding_ray(mesh, X, axis=2):
    """Winding number of each query from signed crossings of the ray along +AXIS: every face crossed above the query
    adds the sign of its normal's AXIS component (+1 leaving, -1 entering). Exact for a closed, consistently oriented
    mesh, overlapping or self-intersecting bodies included (the winding number of a closed surface is the signed
    crossing count of any ray); a ray through an edge or vertex can miscount (measure zero). Returns int (n,)."""
    X = np.asarray(X, np.float64).reshape(-1, 3)
    T = _tris(mesh)
    if len(X) == 0 or len(T) == 0:
        return np.zeros(len(X), np.int64)
    a = int(axis); uv = [k for k in range(3) if k != a]
    ext = float(np.ptp(T.reshape(-1, 3)[:, uv], axis=0).max())
    cell = max(ext / 128.0, 1e-5)
    qi, ti, b1, b2 = pairs2d(T[:, :, uv], X[:, uv], cell)
    h = T[ti, 0, a] + b1 * (T[ti, 1, a] - T[ti, 0, a]) + b2 * (T[ti, 2, a] - T[ti, 0, a])
    na = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])[:, a]
    above = h > X[qi, a]
    return np.bincount(qi[above], weights=np.sign(na[ti[above]]), minlength=len(X)).round().astype(np.int64)


def inside_parity(mesh, X, axis=2):
    """Ray parity along +AXIS (odd crossing count). Kept for tests; inside() uses winding_ray."""
    X = np.asarray(X, np.float64).reshape(-1, 3)
    T = _tris(mesh)
    if len(X) == 0 or len(T) == 0:
        return np.zeros(len(X), bool)
    a = int(axis); uv = [k for k in range(3) if k != a]
    ext = float(np.ptp(T.reshape(-1, 3)[:, uv], axis=0).max())
    cell = max(ext / 128.0, 1e-5)
    qi, ti, b1, b2 = pairs2d(T[:, :, uv], X[:, uv], cell)
    h = T[ti, 0, a] + b1 * (T[ti, 1, a] - T[ti, 0, a]) + b2 * (T[ti, 2, a] - T[ti, 0, a])
    above = h > X[qi, a]
    c = np.bincount(qi[above], minlength=len(X))
    return (c % 2) == 1


def inside(mesh, X, check=2000, seed=0):
    """Generalised winding number >= 0.5 (PREREG A.3 V2 (a)). For a watertight mesh the winding number is taken from
    signed ray crossings (median over the three axis directions, so a ray through an edge cannot decide alone) and
    checked against the exact solid-angle winding number on CHECK random queries (seed); on any disagreement, or for a
    mesh that is not watertight, the exact winding number is computed for every query. Returns (bool (n,), info)."""
    X = np.asarray(X, np.float64).reshape(-1, 3)
    info = dict(method='gwn', checked=0, disagree=0)
    if len(X) == 0:
        return np.zeros(0, bool), info
    if mesh.is_watertight:
        w = np.median(np.stack([winding_ray(mesh, X, k) for k in range(3)]), axis=0)
        ins = w >= 0.5
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=min(int(check), len(X)), replace=False)
        g = winding_number(mesh, X[idx]) >= 0.5
        info.update(checked=int(len(idx)), disagree=int((g != ins[idx]).sum()))
        if info['disagree'] == 0:
            info['method'] = 'signed ray crossings (checked against gwn)'
            return ins, info
    return winding_number(mesh, X) >= 0.5, info


def ray_ranges(tris_c, P_c, cell=0.004):
    """First-hit range along the ray from the camera (origin) through each point P_c (camera coordinates), against
    triangles tris_c (F,3,3) in the same coordinates (all in front of the camera: z > 0). Exact: a ray through
    normalised image point q hits a triangle iff q lies in the triangle's perspective projection. Returns (n,) ranges
    (inf where no triangle is hit). cell: bucket side in normalised image units."""
    P_c = np.asarray(P_c, np.float64)
    out = np.full(len(P_c), np.inf)
    if len(P_c) == 0 or len(tris_c) == 0:
        return out
    front = (tris_c[:, :, 2] > 1e-4).all(1)
    T = tris_c[front]
    if len(T) == 0:
        return out
    T2 = T[:, :, :2] / T[:, :, 2:3]
    Q = P_c[:, :2] / P_c[:, 2:3]
    qi, ti, b1, b2 = pairs2d(T2, Q, cell)
    if len(qi) == 0:
        return out
    # exact ray-plane intersection of the unit ray d with the hit triangle's plane
    d = P_c[qi] / np.linalg.norm(P_c[qi], axis=1, keepdims=True)
    A = T[ti, 0]; n = np.cross(T[ti, 1] - A, T[ti, 2] - A)
    den = np.einsum('ij,ij->i', n, d)
    ok = np.abs(den) > 1e-30
    t = np.where(ok, np.einsum('ij,ij->i', n, A) / np.where(ok, den, 1.0), np.inf)
    t = np.where(t > T_MIN, t, np.inf)
    np.minimum.at(out, qi, t)
    return out


def first_hit(mesh, O, D):
    """Range along unit direction D[i] from origin O[i] to the first triangle hit (either side); inf if none
    (brute force Moller-Trumbore in torch; reference implementation for tests, ray_ranges is the fast path)."""
    O = np.asarray(O, np.float64).reshape(-1, 3)
    D = np.asarray(D, np.float64).reshape(-1, 3)
    if len(O) == 0 or len(mesh.faces) == 0:
        return np.full(len(O), np.inf)
    torch = _torch()
    T = torch.from_numpy(_tris(mesh))
    v0 = T[:, 0]
    e1 = T[:, 1] - v0
    e2 = T[:, 2] - v0
    out = np.empty(len(O))
    Ot, Dt = torch.from_numpy(O), torch.from_numpy(D)
    inf = torch.tensor(float('inf'), dtype=torch.float64)
    for s in range(0, len(O), CHUNK):
        o = Ot[s:s + CHUNK, None, :]
        d = Dt[s:s + CHUNK, None, :].expand(-1, len(v0), -1)
        p = torch.cross(d, e2[None].expand_as(d), dim=-1)
        det = (e1[None] * p).sum(-1)
        ok = det.abs() > EPS_DET
        inv = torch.where(ok, 1.0 / torch.where(ok, det, torch.ones_like(det)), torch.zeros_like(det))
        tv = o - v0[None]
        u = (tv * p).sum(-1) * inv
        q = torch.cross(tv, e1[None].expand_as(tv), dim=-1)
        v = (d * q).sum(-1) * inv
        t = (e2[None] * q).sum(-1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > T_MIN)
        out[s:s + CHUNK] = torch.where(hit, t, inf).min(dim=1).values.numpy()
    return out


def volume_samples(mesh, n, seed=0, axis=2, cells=256):
    """n uniform samples of the volume enclosed by a watertight mesh: columns along AXIS on a cells x cells grid over
    the bounding box; each column's sorted crossings are paired by parity into inside intervals; intervals are drawn
    with probability proportional to their length and a point uniformly inside. Returns (points (m,3), info); m = n
    unless the mesh encloses nothing."""
    rng = np.random.default_rng(seed)
    T = _tris(mesh)
    info = dict(axis=int(axis), cells=int(cells), columns_odd=0, intervals=0)
    if len(T) == 0:
        return np.zeros((0, 3)), info
    a = int(axis)
    u_, v_ = [k for k in range(3) if k != a]
    lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
    pitch = max(hi[u_] - lo[u_], hi[v_] - lo[v_]) / cells
    pitch = max(pitch, 1e-5)
    nu = int(np.ceil((hi[u_] - lo[u_]) / pitch)) + 1
    nv = int(np.ceil((hi[v_] - lo[v_]) / pitch)) + 1
    cols, hs = [], []
    for tri in T:
        U, Vv, H = tri[:, u_], tri[:, v_], tri[:, a]
        i0 = int(np.floor((U.min() - lo[u_]) / pitch - 0.5)); i1 = int(np.ceil((U.max() - lo[u_]) / pitch - 0.5))
        j0 = int(np.floor((Vv.min() - lo[v_]) / pitch - 0.5)); j1 = int(np.ceil((Vv.max() - lo[v_]) / pitch - 0.5))
        i0, j0 = max(i0, 0), max(j0, 0); i1, j1 = min(i1, nu - 1), min(j1, nv - 1)
        if i1 < i0 or j1 < j0:
            continue
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing='ij')
        cu = lo[u_] + (ii.ravel() + 0.5) * pitch
        cv = lo[v_] + (jj.ravel() + 0.5) * pitch
        # 2-D barycentric (half-open edge rule via >= 0 / > 0 split is not needed at random-free centres: ties are
        # measure-zero for these centres; odd columns are counted and skipped)
        x0, y0 = U[0], Vv[0]
        d1u, d1v, d2u, d2v = U[1] - x0, Vv[1] - y0, U[2] - x0, Vv[2] - y0
        den = d1u * d2v - d2u * d1v
        if abs(den) < 1e-20:
            continue
        pu, pv = cu - x0, cv - y0
        b1 = (pu * d2v - d2u * pv) / den
        b2 = (d1u * pv - pu * d1v) / den
        ins = (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)
        if not ins.any():
            continue
        h = H[0] + b1[ins] * (H[1] - H[0]) + b2[ins] * (H[2] - H[0])
        cols.append(ii.ravel()[ins] * nv + jj.ravel()[ins])
        hs.append(h)
    if not cols:
        return np.zeros((0, 3)), info
    col = np.concatenate(cols); hh = np.concatenate(hs)
    o = np.lexsort((hh, col)); col, hh = col[o], hh[o]
    uc, start, cnt = np.unique(col, return_index=True, return_counts=True)
    ivc, ia, ib = [], [], []
    for c_, s_, k_ in zip(uc, start, cnt):
        if k_ % 2:
            info['columns_odd'] += 1
            continue
        z = hh[s_:s_ + k_]
        ivc.append(np.full(k_ // 2, c_)); ia.append(z[0::2]); ib.append(z[1::2])
    if not ivc:
        return np.zeros((0, 3)), info
    ivc = np.concatenate(ivc); ia = np.concatenate(ia); ib = np.concatenate(ib)
    L = ib - ia
    info['intervals'] = int(len(L))
    if L.sum() <= 0:
        return np.zeros((0, 3)), info
    pick = rng.choice(len(L), size=int(n), p=L / L.sum())
    X = np.zeros((int(n), 3))
    X[:, u_] = lo[u_] + (ivc[pick] // nv + 0.5) * pitch
    X[:, v_] = lo[v_] + (ivc[pick] % nv + 0.5) * pitch
    X[:, a] = ia[pick] + rng.random(int(n)) * L[pick]
    info['pitch_mm'] = round(pitch * 1e3, 3)
    return X, info
