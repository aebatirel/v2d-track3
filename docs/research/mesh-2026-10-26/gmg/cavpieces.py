"""Cavity-preserving convex pieces for every object of an F-I5 run (PREREG F-I5.4, INTERLOCK.md section 21.2).

New module of the collision-carve build (owner's extended waiver, 31 Oct). The old splitter (simpieces.decompose) is not
used in F-I5 runs. Routes, tried in order; a route whose pieces fail the pieces gate falls to the next:
  1 plate     F-I4.6 analytic boxes (plate pairs only; built by platebody, passed in by the caller)
  2 lathe     structure lathe accepted (rotc <= 3 sigma, A.6) and not plate-like: N_s sectors x height bands of the
              SHELL solid's profile about the structure axis, completed by revolution; solid bins = centre disc +
              N_s rim sectors; every band edge is a shared profile-bin edge, so the lowest wall band of each sector
              starts exactly at that sector's base top (no empty ring: the ev10 defect); wall-continuity check on
              rays every 0.5 mm x 1 deg; handle material (shell outside the body by > 3 sigma, >= 0.3 cm3) by route 3
  3 coacd     CoACD (threshold 0.02, preprocess auto, max_convex_hull = the object's piece cap) on the body mesh, then
              keep-out repair: a hull holding > 0.3 cm3 of keep-out is replaced by the hulls of the body points on the
              two sides of the plane that minimises the keep-out of the two children; no minimum-gain stop
  4 voxels    exact fallback: the 2 mm grid cells inside the body and outside the keep-out merged greedily into maximal
              axis-aligned boxes; over the cap a 4, 6, then 8 mm grid whose cells are kept only when all their 2 mm
              cells are kept

  piece_cap(n_objects)                         floor(165 / objects)
  Lathe.from_mesh(mesh, c, a, sigma)           the profile (exact radial intervals, see BUILD NOTE 1)
  Lathe.pieces(n_s, ...)                       default ring pieces (list of piece dicts) and their vertices
  Lathe.carve(pieces, K, ...)                  profile-space carve against convex solids K (exact, BUILD NOTE 2)
  continuity(lathe, pieces)                    the wall-continuity check (lathe_wall_gap)
  coacd_repair(body, ev, cap, k_inside)        route 3
  voxel_boxes(body, ev, cap, k_inside)         route 4
  keepout(...), gate(...)                      the F-I5.4 pieces gate (FREE weight 1, K weight 10, no distance limit)
  route_pieces(...)                            the route ladder for one object (default or carved body)

BUILD NOTES (decided while building, before any real run; logged in build/I.md and PREREG F-I5.11):
  1. The radial interval of a (sector, bin) is measured by casting rays from the axis through the SHELL mesh at three
     azimuths of the sector (median) instead of from the 2 mm sub-samples: the sub-sample interval lies up to about
     half a pitch inside the true surfaces, which on a 3 deg taper is about 10 mm of sink per side (the F-I5.3 (d)
     reasoning). Same quantity, measured exactly.
  2. A convex hull over the bins of a band refills per-bin inner radii that are not on the band's convex envelope, so
     the carve is applied per piece, not per bin: each conflicting piece (convex K piece inside it) takes the option
     that keeps the most volume among (i) a new inner face r(h) = alpha + beta h (linear programme over the vertices of
     K inside the piece: exact clearance), (ii) a new outer face (same LP, other side), (iii) its top or (iv) its
     bottom end moved to the extreme height of K inside it. Carved wall ranges are re-banded at <= 10 mm first.
GT-free: our candidate meshes, our grids (FREE state) and our tracks only.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from scipy.optimize import linprog
from scipy.spatial import ConvexHull

from gmg import guard

# name: (value, origin) -- PREREG F-I5.10
C = dict(
    n_sectors=(16, 'generic:F-I5.10 lathe_collision.py default 16 segments'),
    sector_fallback=((12, 8), 'generic:F-I5.10 12 / 8 sectors when the piece cap is exceeded'),
    band_m=(0.030, 'generic:F-I5.10 lathe_collision.py default 30 mm bands'),
    band_carved_m=(0.010, 'informed:F-I5.10 10 mm bands where carved (ev10w widened band)'),
    bin_m=(0.002, 'generic:F-I5.10 2 mm profile bins'),
    wall_k_sigma=(3.0, 'generic:F-I5.10 wall if inner radius > max(3 sigma, 2 mm)'),
    wall_min_m=(0.002, 'generic:F-I5.10 wall if inner radius > max(3 sigma, 2 mm)'),
    ray_dh_m=(0.0005, 'generic:F-I5.10 continuity rays every 0.5 mm'),
    ray_dphi_deg=(1.0, 'generic:F-I5.10 continuity rays every 1 deg'),
    handle_cm3=(0.3, 'generic:F-I5.10 handle residual 0.3 cm3 (= the keep-out tolerance)'),
    handle_k_sigma=(3.0, 'generic:F-I5.4 handle = shell outside the body by > 3 sigma'),
    coacd_thr=(0.02, 'generic:F-I5.10 CoACD 0.02 (finer than its 0.05 default)'),
    tol_cm3=(0.3, 'informed:F-I1.14 0.3 cm3 keep-out per hull'),
    lam=(10.0, 'informed:F-I1.14 weight 10 for the carve'),
    shapes_max=(165, 'informed:F-I1.14 165-shape cap (note 19)'),
    pitch_m=(0.002, 'generic:F-I5.10 2 mm keep-out / topology grid'),
    vox_pitches=((0.002, 0.004, 0.006, 0.008), 'generic:F-I5.10 voxel grids 2 / 4 / 6 / 8 mm'),
    maxv=(64, 'informed:F-I1.14 64 vertices per hull (MuJoCo limit)'),
    wall_keep_m=(0.0002, 'generic:numerical 0.2 mm thinnest wall a carved piece keeps (simpieces.clip limit)'),
    rays_per_sector=(3, 'generic:numerical 3 azimuths per sector for the profile rays (median)'),
)


def k_(name):
    v, o = C[name]
    if o.startswith('generic'):
        guard.constant(f'cp.{name}', v if not isinstance(v, tuple) else list(v), o)
    return v


def piece_cap(n_objects):
    """F-I5.4: floor(165 / number of objects in the episode) pieces per object."""
    return int(k_('shapes_max') // max(int(n_objects), 1))


# ------------------------------------------------------------------------------------------------ convex helpers
def hull_eq(V):
    return ConvexHull(V).equations


def unique_planes(eq, tol=1e-9):
    """Deduplicate qhull facet equations (coplanar triangles repeat one plane)."""
    out = []
    for e in eq:
        if not any(np.abs(e - f).max() < 1e-7 for f in out):
            out.append(e)
    return np.array(out)


def clip_vertices(V, planes):
    """Points of the convex polytope conv(V) intersected with the half-spaces n.x + d <= 0 (planes: rows (n, d)): the
    kept vertices plus the crossings of the hull's edges (triangulation edges included: their crossings lie on facets,
    inside the polytope). Returns None if the intersection is empty or has no volume. Exact up to float rounding."""
    V = np.asarray(V, np.float64)
    for e in np.atleast_2d(planes):
        s = V @ e[:3] + e[3]
        if (s <= 1e-12).all():
            continue
        if (s >= -1e-12).all():
            return None
        try:
            simp = ConvexHull(V).simplices
        except Exception:
            return None
        E = np.vstack([simp[:, [0, 1]], simp[:, [1, 2]], simp[:, [0, 2]]])
        E = np.unique(np.sort(E, axis=1), axis=0)
        ins = s <= 0
        X = E[ins[E[:, 0]] != ins[E[:, 1]]]
        t = s[X[:, 0]] / (s[X[:, 0]] - s[X[:, 1]])
        P = V[X[:, 0]] + t[:, None] * (V[X[:, 1]] - V[X[:, 0]])
        V = np.vstack([V[ins], P])
        if len(V) < 4:
            return None
    try:
        h = ConvexHull(V)
        if h.volume < 1e-12:
            return None
        return V[h.vertices]
    except Exception:
        return None


def hull_parts(V):
    """(vertices, unique facet planes, edge index pairs) of conv(V)."""
    h = ConvexHull(np.asarray(V, np.float64))
    W = h.points[h.vertices]
    h2 = ConvexHull(W)
    simp = h2.simplices
    E = np.unique(np.sort(np.vstack([simp[:, [0, 1]], simp[:, [1, 2]], simp[:, [0, 2]]]), axis=1), axis=0)
    return W, unique_planes(h2.equations), E


def _edge_plane_points(V, E, eq):
    """Crossings of the edges E of V with the planes eq (all pairs)."""
    A, B = V[E[:, 0]], V[E[:, 1]]
    sa = A @ eq[:, :3].T + eq[:, 3]                       # (edges, planes)
    sb = B @ eq[:, :3].T + eq[:, 3]
    m = (sa * sb) < 0
    if not m.any():
        return np.zeros((0, 3))
    ei, pi = np.nonzero(m)
    t = sa[ei, pi] / (sa[ei, pi] - sb[ei, pi])
    return A[ei] + t[:, None] * (B[ei] - A[ei])


def intersect_points(PA, PB, tol=1e-9):
    """Vertices of conv(A) intersected with conv(B), from their hull_parts (exact vertex enumeration: vertices of each
    inside the other plus edge-facet crossings inside both). Returns None when the intersection has no interior
    (empty or touching)."""
    VA, qA, EA = PA
    VB, qB, EB = PB
    P = np.vstack([VA, VB, _edge_plane_points(VA, EA, qB), _edge_plane_points(VB, EB, qA)])
    ok = np.all(P @ qA[:, :3].T + qA[:, 3] <= tol, axis=1) & np.all(P @ qB[:, :3].T + qB[:, 3] <= tol, axis=1)
    P = P[ok]
    if len(P) < 4:
        return None
    c = P.mean(0)
    if (c @ qA[:, :3].T + qA[:, 3]).max() > -1e-7 or (c @ qB[:, :3].T + qB[:, 3]).max() > -1e-7:
        return None
    return P


def offset_hull(V, c):
    """The face-offset polytope of conv(V): every face plane moved outward by c (contains the exact dilation by c)."""
    from scipy.spatial import HalfspaceIntersection
    if c <= 0:
        return np.asarray(V, np.float64)
    eq = unique_planes(hull_eq(V)).copy()
    eq[:, 3] -= c
    try:
        P = HalfspaceIntersection(eq, np.asarray(V, np.float64).mean(0)).intersections
        return P[ConvexHull(P).vertices]
    except Exception:
        return np.asarray(V, np.float64)


class Hulls:
    """Convex pieces with their equations and AABBs, for fast inside tests of many points."""

    def __init__(self, hulls):
        self.V = [np.asarray(V, np.float64) for V in hulls]
        self.eq = [hull_eq(V) for V in self.V]
        self.lo = np.array([V.min(0) for V in self.V]) if self.V else np.zeros((0, 3))
        self.hi = np.array([V.max(0) for V in self.V]) if self.V else np.zeros((0, 3))

    def __len__(self):
        return len(self.V)

    def inside(self, X, tol=1e-9, which=False):
        X = np.asarray(X, np.float64)
        hit = np.zeros(len(X), bool)
        idx = np.full(len(X), -1, np.int64)
        if not len(X) or not self.V:
            return (hit, idx) if which else hit
        for i, eq in enumerate(self.eq):
            m = np.all((X >= self.lo[i] - tol) & (X <= self.hi[i] + tol), axis=1)
            if not m.any():
                continue
            j = np.nonzero(m)[0]
            ok = np.all(X[j] @ eq[:, :3].T + eq[:, 3] <= tol, axis=1)
            hit[j[ok]] = True
            idx[j[ok]] = i
        return (hit, idx) if which else hit

    def bounds(self):
        return self.lo.min(0), self.hi.max(0)


def grid_points(lo, hi, pitch):
    n = np.maximum(np.ceil((np.asarray(hi) - np.asarray(lo)) / pitch).astype(int) + 1, 1)
    ax = [lo[k] + pitch * (np.arange(n[k]) + 0.5) for k in range(3)]
    return np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3), n


def reduce(V):
    from gmg.simpieces import reduce_hull
    return reduce_hull(np.asarray(V, np.float64), k_('maxv'))


# ------------------------------------------------------------------------------------------------ route 2: lathe
def _frame(a):
    a = np.asarray(a, np.float64); a = a / np.linalg.norm(a)
    t = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(a, t); e1 /= np.linalg.norm(e1)
    return a, e1, np.cross(a, e1)


def _intervals(mesh, O, D, rmax):
    """Radial intervals [r0, r1] along rays O + r D (r >= 0) inside the mesh (parity of the sorted, de-duplicated
    hits; a ray starting inside has an odd count)."""
    loc, ir, _ = mesh.ray.intersects_location(O, D, multiple_hits=True)
    out = [[] for _ in range(len(O))]
    if len(loc):
        r = np.einsum('ij,ij->i', loc - O[ir], D[ir])
        for i in range(len(O)):
            ri = np.sort(r[(ir == i) & (r >= -1e-9)])
            if len(ri) == 0:
                continue
            ri = ri[np.r_[True, np.diff(ri) > 1e-6]]
            if len(ri) % 2 == 1:
                ri = np.r_[0.0, ri]
            out[i] = [(float(ri[k]), float(ri[k + 1])) for k in range(0, len(ri) - 1, 2)]
    return out


class Lathe:
    """Profile of a body of revolution: bins along the axis (edges he), per bin the main radial interval (rin, rout)
    and kind (wall / solid); built from the SHELL mesh (BUILD NOTE 1)."""

    def __init__(self, c, a, he, rin, rout, kind, sigma, info):
        self.c = np.asarray(c, np.float64)
        self.a, self.e1, self.e2 = _frame(a)
        self.he, self.rin, self.rout, self.kind = np.asarray(he), np.asarray(rin), np.asarray(rout), list(kind)
        self.sigma = float(sigma)
        self.info = info

    # ---- coordinates
    def cyl(self, X):
        Y = np.asarray(X, np.float64) - self.c
        h = Y @ self.a
        x, y = Y @ self.e1, Y @ self.e2
        return h, np.hypot(x, y), np.arctan2(y, x)

    def pt(self, h, r, phi):
        h, r, phi = np.broadcast_arrays(np.asarray(h, float), np.asarray(r, float), np.asarray(phi, float))
        return (self.c + h[..., None] * self.a + (r * np.cos(phi))[..., None] * self.e1 +
                (r * np.sin(phi))[..., None] * self.e2)

    @classmethod
    def from_mesh(cls, mesh, c, a, sigma, n_s=None):
        """Profile from the mesh: 2 mm bins over the mesh's extent along a; per (sector, bin) the main (innermost)
        radial interval at three azimuths (median); per bin the median over the sectors that hold material; wall if
        the inner radius > max(3 sigma, 2 mm); more than two intervals in a bin (median count) -> complex (route 3);
        an empty bin between material bins -> complex. Returns (Lathe or None, info)."""
        n_s = n_s or k_('n_sectors')
        a_, e1, e2 = _frame(a)
        c = np.asarray(c, np.float64)
        V = np.asarray(mesh.vertices, np.float64)
        hv = (V - c) @ a_
        h0, h1 = float(hv.min()), float(hv.max())
        nb = max(int(math.ceil((h1 - h0) / k_('bin_m') - 1e-9)), 1)
        he = np.linspace(h0, h1, nb + 1)
        hc = 0.5 * (he[:-1] + he[1:])
        rmax = float(np.linalg.norm((V - c) - np.outer(hv, a_), axis=1).max()) + 0.01
        kps = k_('rays_per_sector')
        phis = np.array([(s + (k + 0.5) / kps) * 2 * math.pi / n_s for s in range(n_s) for k in range(kps)])
        O = (c + hc[:, None] * a_)[:, None, :].repeat(len(phis), 1).reshape(-1, 3)
        D = (np.cos(phis)[:, None] * e1 + np.sin(phis)[:, None] * e2)[None].repeat(nb, 0).reshape(-1, 3)
        iv = _intervals(mesh, O, D, rmax)
        rin = np.full(nb, np.nan); rout = np.full(nb, np.nan); nint = np.zeros(nb)
        for b in range(nb):
            si, so_, cnt = [], [], []
            for s in range(n_s):
                rows = [iv[b * len(phis) + s * kps + k] for k in range(kps)]
                has = [r for r in rows if r]
                if len(has) * 2 < kps:
                    continue
                si.append(np.median([r[0][0] for r in has])); so_.append(np.median([r[0][1] for r in has]))
                cnt.append(np.median([len(r) for r in has]))
            if si:
                rin[b], rout[b], nint[b] = np.median(si), np.median(so_), np.median(cnt)
        mat = np.isfinite(rout)
        info = dict(bins=nb, h_span_mm=[round(h0 * 1e3, 2), round(h1 * 1e3, 2)], material_bins=int(mat.sum()),
                    max_intervals=float(nint.max()) if nb else 0.0)
        if not mat.any():
            info['why'] = 'lathe_no_material'
            return None, info
        i0, i1 = np.nonzero(mat)[0][[0, -1]]
        if not mat[i0:i1 + 1].all():
            info['why'] = 'lathe_profile_complex (empty bin between material bins)'
            return None, info
        if (nint[i0:i1 + 1] > 2).any():
            info['why'] = 'lathe_profile_complex (more than two radial intervals in a bin)'
            return None, info
        he = he[i0:i1 + 2]; rin = rin[i0:i1 + 1]; rout = rout[i0:i1 + 1]
        thr = max(k_('wall_k_sigma') * float(sigma), k_('wall_min_m'))
        kind = ['wall' if r > thr else 'solid' for r in rin]
        rin = np.where(np.array(kind) == 'wall', rin, 0.0)
        info.update(wall_threshold_mm=round(thr * 1e3, 3), wall_bins=int(sum(k == 'wall' for k in kind)),
                    solid_bins=int(sum(k == 'solid' for k in kind)), two_interval_bins=int((nint[i0:i1 + 1] == 2).sum()),
                    r_out_mm=[round(float(rout.min()) * 1e3, 2), round(float(rout.max()) * 1e3, 2)])
        if not any(k == 'wall' for k in kind):
            info['note'] = 'no wall bin: a solid of revolution'
        return cls(c, a_, he, rin, rout, kind, sigma, info), info

    # ---- profile values at heights (linear between bin centres of the same run, clamped)
    def runs(self):
        out, s = [], 0
        for i in range(1, len(self.kind) + 1):
            if i == len(self.kind) or self.kind[i] != self.kind[s]:
                out.append((self.kind[s], s, i - 1)); s = i
        return out

    def prof(self, h, b0, b1):
        hc = 0.5 * (self.he[b0:b1 + 1] + self.he[b0 + 1:b1 + 2])
        ri = np.interp(h, hc, self.rin[b0:b1 + 1]); ro = np.interp(h, hc, self.rout[b0:b1 + 1])
        return ri, ro

    # ---- default pieces
    def band_edges(self, b0, b1, carved=None, lim_carved=None):
        """Bin-edge indices of the bands of the run b0..b1: <= 30 mm, <= 10 mm inside the carved height range
        (carved = (h_lo, h_hi) or None) with edges at the bin edges just outside the carve. lim_carved (PREREG F-I5.13
        diagnostic D2 only): the band limit inside the carve instead of 10 mm."""
        e = list(range(b0, b1 + 2))
        H = self.he
        band, bc = k_('band_m'), (k_('band_carved_m') if lim_carved is None else lim_carved)
        cut = {e[0], e[-1]}
        seg = None
        if carved is not None and carved[1] > carved[0]:
            lo = max([i for i in e if H[i] <= carved[0] + 1e-12] or [e[0]])
            hi = min([i for i in e if H[i] >= carved[1] - 1e-12] or [e[-1]])
            cut |= {lo, hi}
            seg = (lo, hi)
        cut = sorted(cut)
        out = []
        for x0, x1 in zip(cut[:-1], cut[1:]):
            lim = bc if (seg is not None and seg[0] <= x0 and x1 <= seg[1]) else band
            i = x0
            out.append(i)
            while True:
                nxt = max([j for j in range(i + 1, x1 + 1) if H[j] - H[i] <= lim + 1e-9] or [i + 1])
                if nxt >= x1:
                    break
                out.append(nxt); i = nxt
        out.append(cut[-1])
        return sorted(set(out))

    def pieces(self, n_s=None, carved=None, ring_gap_m=0.0, lim_carved=None):
        """Default piece dicts. carved: {sector: (h_lo, h_hi)} wall ranges to re-band at <= 10 mm. ring_gap_m (test
        x9 only): the lowest wall band of every sector starts this far above the base top (the ev10 defect)."""
        n_s = n_s or k_('n_sectors')
        out = []
        th = 2 * math.pi / n_s
        runs = self.runs()
        for kind, b0, b1 in runs:
            for s in range(n_s if kind == 'wall' else 1):
                edges = self.band_edges(b0, b1, (carved or {}).get(s) if kind == 'wall' else None, lim_carved)
                for x0, x1 in zip(edges[:-1], edges[1:]):
                    hk = self.he[x0:x1 + 1].copy()
                    if kind == 'wall' and ring_gap_m > 0 and x0 == b0 and b0 > 0:
                        hk[0] = hk[0] + ring_gap_m
                    ri, ro = self.prof(hk, b0, b1)
                    if kind == 'wall':
                        out.append(dict(kind='wall', s=s, phi=(s * th, (s + 1) * th), hk=hk, rin=ri, rout=ro))
                    else:
                        rc = 0.5 * float(ro.min())
                        out.append(dict(kind='disc', s=-1, phi=None, hk=hk[[0, -1]], rc=rc, n_s=n_s))
                        for ss in range(n_s):
                            out.append(dict(kind='rim', s=ss, phi=(ss * th, (ss + 1) * th), hk=hk,
                                            rin=np.full(len(hk), rc), rout=ro))
        return out

    def verts(self, p):
        if p['kind'] == 'disc':
            phis = np.arange(p['n_s']) * 2 * math.pi / p['n_s']
            V = np.array([self.pt(h, p['rc'], f) for h in p['hk'] for f in phis])
        else:
            V = np.array([self.pt(h, r, f) for f in p['phi'] for h, r in
                          list(zip(p['hk'], p['rin'])) + list(zip(p['hk'], p['rout']))])
        return reduce(V)

    def hulls(self, pieces):
        return [self.verts(p) for p in pieces]

    # ---- carve (BUILD NOTE 2)
    def _u(self, p):
        fm = 0.5 * (p['phi'][0] + p['phi'][1])
        return math.cos(fm) * self.e1 + math.sin(fm) * self.e2, math.cos(0.5 * (p['phi'][1] - p['phi'][0]))

    def _options(self, p, Q):
        """Options for piece p against the points Q (vertices of K inside p): list of (name, new piece or None for
        removal)."""
        h = (Q - self.c) @ self.a
        opts = []
        hk = p['hk']
        top, bot = float(h.min()), float(h.max())       # trim top to the lowest K height; trim bottom to the highest
        if p['kind'] == 'disc':
            if top > hk[0] + 1e-6:
                opts.append(('trim_top', dict(p, hk=np.array([hk[0], top]))))
            if bot < hk[-1] - 1e-6:
                opts.append(('trim_bottom', dict(p, hk=np.array([bot, hk[-1]]))))
            return opts
        if top > hk[0] + 1e-6:
            sel = hk < top - 1e-9
            nh = np.r_[hk[sel], top]
            opts.append(('trim_top', dict(p, hk=nh, rin=np.interp(nh, hk, p['rin']),
                                          rout=np.interp(nh, hk, p['rout']))))
        if bot < hk[-1] - 1e-6:
            sel = hk > bot + 1e-9
            nh = np.r_[bot, hk[sel]]
            opts.append(('trim_bottom', dict(p, hk=nh, rin=np.interp(nh, hk, p['rin']),
                                             rout=np.interp(nh, hk, p['rout']))))
        if p['kind'] == 'wall':
            u, cs = self._u(p)
            q = ((Q - self.c) @ u) / cs
            hm = float(hk.mean())
            A_h = np.c_[np.ones(len(h)), h - hm]
            A_k = np.c_[np.ones(len(hk)), hk - hm]
            wk = k_('wall_keep_m')
            # (i) widen: min sum(alpha + beta hk) s.t. alpha + beta h_v >= q_v, >= rin_k, <= rout_k - wk
            A = np.vstack([-A_h, -A_k, A_k]); b = np.r_[-q, -p['rin'], p['rout'] - wk]
            r = linprog(A_k.sum(0), A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
            if r.success:
                opts.append(('widen', dict(p, rin=A_k @ r.x)))
            # (ii) shrink the outer face: max sum s.t. alpha + beta h_v <= q_v, <= rout_k, >= rin_k + wk
            A = np.vstack([A_h, A_k, -A_k]); b = np.r_[q, p['rout'], -(p['rin'] + wk)]
            r = linprog(-A_k.sum(0), A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
            if r.success:
                opts.append(('shrink', dict(p, rout=A_k @ r.x)))
        return opts

    def carve(self, pieces, K, allow=None, log=None):
        """Remove the convex solids K (list of vertex arrays, already posed and offset by c) from the pieces, per piece
        by the option that keeps the most volume (BUILD NOTE 2). allow(points) -> bool: where carving is permitted
        (R+); a K-in-piece set none of whose points (vertices and centroid) is allowed is ignored. Iterates until no
        piece holds a K piece (each round re-checks the changed pieces). Returns (new pieces, report)."""
        KH = Hulls(K)
        KP = [hull_parts(V) for V in KH.V]
        al = allow if isinstance(allow, (list, tuple)) else [allow] * len(K)
        rep = dict(conflicts=0, options={}, removed_pieces=0, rounds=0, infeasible=0)
        P = [dict(p) for p in pieces]
        todo = list(range(len(P)))
        for rnd in range(6):
            rep['rounds'] = rnd + 1
            nxt = []
            for i in todo:
                p = P[i]
                if p is None:
                    continue
                V = self.verts(p)
                PP = hull_parts(V)
                lo, hi = V.min(0), V.max(0)
                cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0]
                Qs = []
                for j in cand:
                    Q = intersect_points(KP[j], PP)
                    if Q is None:
                        continue
                    if al[j] is not None and not al[j](np.vstack([Q, Q.mean(0)[None]])).any():
                        continue
                    Qs.append(Q)
                if not Qs:
                    continue
                rep['conflicts'] += 1
                Q = np.vstack(Qs)
                vol0 = ConvexHull(V).volume
                best = None
                for name, q in self._options(p, Q):
                    try:
                        vq = ConvexHull(self.verts(q)).volume
                    except Exception:
                        continue
                    if best is None or vq > best[2]:
                        best = (name, q, vq)
                if best is None:
                    P[i] = None
                    rep['removed_pieces'] += 1
                    rep['infeasible'] += 1
                    hq = (Q - self.c) @ self.a
                    rep.setdefault('infeasible_rows', []).append(dict(
                        kind=p['kind'], s=int(p['s']), h_mm=[round(float(p['hk'][0]) * 1e3, 2),
                                                          round(float(p['hk'][-1]) * 1e3, 2)],
                        K_h_mm=[round(float(hq.min()) * 1e3, 2), round(float(hq.max()) * 1e3, 2)],
                        K_r_mm=[round(float(x) * 1e3, 2) for x in np.percentile(self.cyl(Q)[1], [0, 100])]))
                    continue
                rep['options'][best[0]] = rep['options'].get(best[0], 0) + 1
                P[i] = best[1]
                P[i]['_removed_cm3'] = P[i].get('_removed_cm3', 0.0) + (vol0 - best[2]) * 1e6
                nxt.append(i)
            todo = nxt
            if not todo:
                break
        rep['unresolved_after_rounds'] = len(todo)
        return [p for p in P if p is not None], rep

    def carved_ranges(self, pieces, K, allow=None):
        """{sector: (h_lo, h_hi)} of K inside the wall pieces (for re-banding at <= 10 mm before the carve)."""
        KH = Hulls(K)
        KP = [hull_parts(V) for V in KH.V]
        al = allow if isinstance(allow, (list, tuple)) else [allow] * len(K)
        out = {}
        for p in pieces:
            if p['kind'] != 'wall':
                continue
            V = self.verts(p)
            PP = hull_parts(V)
            lo, hi = V.min(0), V.max(0)
            cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0]
            for j in cand:
                Q = intersect_points(KP[j], PP)
                if Q is None or (al[j] is not None and not al[j](np.vstack([Q, Q.mean(0)[None]])).any()):
                    continue
                h = (Q - self.c) @ self.a
                a0, a1 = out.get(p['s'], (np.inf, -np.inf))
                out[p['s']] = (min(a0, float(h.min())), max(a1, float(h.max())))
        return out


def continuity(lathe, hulls, pieces):
    """Wall-continuity check (F-I5.4): points at the middle of the wall polygon (between the inner and outer chords in
    the direction of the ray) every 0.5 mm in height from each sector's base top to its rim and every 1 deg in
    azimuth must each lie inside a piece. Returns dict(ok, gaps, checked, first_gaps)."""
    H = Hulls(hulls)
    walls = [p for p in pieces if p['kind'] == 'wall']
    if not walls:
        return dict(ok=True, gaps=0, checked=0, note='no wall')
    n_s = int(round(2 * math.pi / (walls[0]['phi'][1] - walls[0]['phi'][0])))
    th = math.pi / n_s
    runs = [r for r in lathe.runs() if r[0] == 'wall']
    pts, hh = [], []
    dphi = math.radians(k_('ray_dphi_deg'))
    for kind, b0, b1 in runs:
        h_lo, h_hi = lathe.he[b0], lathe.he[b1 + 1]
        hs = np.arange(h_lo, h_hi + 1e-12, k_('ray_dh_m'))
        hs = np.clip(hs, h_lo + 1e-6, h_hi - 1e-6)
        ri, ro = lathe.prof(hs, b0, b1)
        for phi in np.arange(0, 2 * math.pi, dphi):
            s = int(phi // (2 * th)) % n_s
            fm = (s + 0.5) * 2 * th
            k = math.cos(th) / max(math.cos(phi - fm), 1e-9)
            rm = 0.5 * (ri + ro) * k
            pts.append(lathe.pt(hs, rm, np.full(len(hs), phi)))
            hh.append(hs)
    X = np.vstack(pts)
    ins = H.inside(X, tol=1e-7)
    gaps = X[~ins]
    out = dict(ok=bool(ins.all()), gaps=int((~ins).sum()), checked=int(len(X)))
    if len(gaps):
        h, r, f = lathe.cyl(gaps)
        out['gap_h_mm'] = [round(float(h.min()) * 1e3, 2), round(float(h.max()) * 1e3, 2)]
    return out


def handle_residual(lathe, hulls, body, cap_left, k_inside=None, ev=None):
    """Shell material outside the lathe body by > 3 sigma (2 mm grid points of the body outside the pieces offset by
    3 sigma), 26-connected components >= 0.3 cm3, each decomposed by the route-3 repair from its convex hull."""
    from gmg.interlock import fast_inside
    pitch = k_('pitch_m')
    lo, hi = body.bounds
    G, n = grid_points(lo, hi, pitch)
    ins = fast_inside(body, G)
    off = Hulls([offset_hull(V, k_('handle_k_sigma') * lathe.sigma) for V in hulls])
    res = ins & ~off.inside(G)
    out = []
    info = dict(points=int(res.sum()), components=[])
    if not res.any():
        return out, info
    lab, m = ndimage.label(res.reshape(n), structure=np.ones((3, 3, 3)))
    lab = lab.ravel()
    for k in range(1, m + 1):
        idx = np.nonzero(lab == k)[0]
        cm3 = len(idx) * pitch ** 3 * 1e6
        if cm3 < k_('handle_cm3') or len(idx) < 4:
            continue
        P = G[idx]
        hl, rep = repair([P], P, body, ev, max(cap_left - len(out), 1), k_inside=k_inside, solid_points=P)
        out += hl
        info['components'].append(dict(cm3=round(cm3, 3), pieces=len(hl)))
    return out, info


# ------------------------------------------------------------------------------------------------ keep-out and gate
def keepout(body, ev, hulls, k_inside=None, pitch=None):
    """Keep-out points (F-I5.4) inside the union of HULLS: 2 mm grid points outside BODY (the default or the carved
    body) that lie in K inside R+ (k_inside, weight 10) or in a FREE voxel of the object's grid (weight 1). No distance
    limit. Returns (points, weights)."""
    from gmg.interlock import STATE_FREE, fast_inside
    pitch = pitch or k_('pitch_m')
    H = hulls if isinstance(hulls, Hulls) else Hulls(hulls)
    if not len(H):
        return np.zeros((0, 3)), np.zeros(0)
    lo, hi = H.bounds()
    G, _ = grid_points(lo - pitch, hi + pitch, pitch)
    G = G[H.inside(G)]
    w = np.zeros(len(G))
    if ev is not None and len(G):
        l, ok = ev.grid.lin(G)
        st = np.full(len(G), -1); st[ok] = ev.state[l[ok]]
        w[st == STATE_FREE] = 1.0
    if len(G) and body is not None and (w > 0).any():       # FREE counts only outside the body
        j = np.nonzero(w > 0)[0]
        w[j[fast_inside(body, G[j])]] = 0.0
    if k_inside is not None and len(G):                     # K inside R+ is outside the carved body by definition
        w[k_inside(G)] = k_('lam')
    sel = w > 0
    return G[sel], w[sel]


def excess(hulls, KP, KW, pitch=None):
    pitch = pitch or k_('pitch_m')
    vox = pitch ** 3 * 1e6
    if not len(KP):
        return [0.0] * len(hulls)
    H = Hulls(hulls)
    out = []
    for i in range(len(H)):
        m = np.all((KP >= H.lo[i] - 1e-9) & (KP <= H.hi[i] + 1e-9), axis=1)
        j = np.nonzero(m)[0]
        ok = np.all(KP[j] @ H.eq[i][:, :3].T + H.eq[i][:, 3] <= 1e-9, axis=1) if len(j) else np.zeros(0, bool)
        out.append(float(KW[j[ok]].sum()) * vox)
    return out


def gate(hulls, body, ev, k_inside=None):
    """Pieces gate: every hull holds <= 0.3 cm3 of keep-out (F-I5.4)."""
    KP, KW = keepout(body, ev, hulls, k_inside)
    ex = excess(hulls, KP, KW)
    tol = k_('tol_cm3')
    return dict(pass_=bool(all(e <= tol for e in ex)), n=len(hulls), max_cm3=round(max(ex), 4) if ex else 0.0,
                sum_cm3=round(sum(ex), 4), over_tol=int(sum(e > tol for e in ex)), keepout_points=int(len(KP)),
                keepout_cm3=round(float(KW.sum()) * k_('pitch_m') ** 3 * 1e6, 3))


# ------------------------------------------------------------------------------------------------ route 3
def _coacd_child(conn, V, F, thr, cap):
    try:
        import coacd as _c
        parts = _c.run_coacd(_c.Mesh(V, F), threshold=thr, max_convex_hull=int(cap), preprocess_mode='auto')
        conn.send(('ok', [np.asarray(v, np.float64) for v, f in parts if len(v) >= 4]))
    except Exception as e:                                          # noqa: BLE001
        conn.send(('error', f'{type(e).__name__}: {e}'))
    conn.close()


def coacd(body, cap, timeout_s=3600):
    """CoACD in a forked child process: CoACD 1.0.14 can abort the whole interpreter on a C++ assertion
    (intersection.h `d0 != d2`, T-I12 rack fixture, 18:14 UTC); an abort or error raises here, so the route ladder falls
    to route 4 instead of the run dying (code fix, no rule change)."""
    import multiprocessing as mp
    ctx = mp.get_context('fork')
    a, b = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_coacd_child, args=(b, np.asarray(body.vertices, np.float64),
                                               np.asarray(body.faces, np.int64), k_('coacd_thr'), int(cap)))
    p.start()
    b.close()
    out = None
    if a.poll(timeout_s):
        try:
            out = a.recv()
        except EOFError:
            out = None
    p.join(5)
    if p.is_alive():
        p.kill(); p.join()
    if out is None:
        raise RuntimeError(f'coacd child died (exit code {p.exitcode})')
    if out[0] != 'ok':
        raise RuntimeError(f'coacd child: {out[1]}')
    return out[1]


def repair(hulls, points, body, ev, cap, k_inside=None, solid_points=None, log=None):
    """Keep-out repair (F-I5.4 route 3): while a hull holds > 0.3 cm3 of keep-out and the cap allows, replace it by
    the convex hulls of the body points on the two sides of the plane that minimises the keep-out inside the two
    children (planes: the hull's and the keep-out's principal axes, the coordinate axes; offsets at 19 quantiles and
    at the keep-out's extremes); no minimum-gain stop. Body points of a hull = the body's 2 mm solid points and surface
    samples inside it. Returns (hulls, report)."""
    tol = k_('tol_cm3')
    pitch = k_('pitch_m')
    vox = pitch ** 3 * 1e6
    P = np.asarray(points, np.float64)
    allh = Hulls(hulls)
    KP, KW = keepout(body, ev, allh, k_inside)
    items = []
    for i, V in enumerate(hulls):
        eq = allh.eq[i]
        idx = np.nonzero(np.all(P @ eq[:, :3].T + eq[:, 3] <= 1e-9, axis=1))[0]
        k = np.all(KP @ eq[:, :3].T + eq[:, 3] <= 1e-9, axis=1) if len(KP) else np.zeros(0, bool)
        items.append(dict(V=np.asarray(V, np.float64), idx=idx, F=KP[k], FW=KW[k], ex=float(KW[k].sum()) * vox))
    steps, stuck = 0, 0

    def mk(idx):
        Q = P[idx]
        try:
            h = ConvexHull(Q)
        except Exception:
            return None
        eq = h.equations
        k = np.all(KP @ eq[:, :3].T + eq[:, 3] <= 1e-9, axis=1) if len(KP) else np.zeros(0, bool)
        return dict(V=Q[h.vertices], idx=idx, F=KP[k], FW=KW[k], ex=float(KW[k].sum()) * vox)
    while len(items) < cap:
        items.sort(key=lambda d: -d['ex'])
        it = items[0]
        if it['ex'] <= tol:
            break
        Q = P[it['idx']]
        if len(Q) < 8:
            it['ex'] = -it['ex'] - 1e-9; stuck += 1; continue
        axes = list(np.linalg.svd(Q - Q.mean(0), full_matrices=False)[2]) + list(np.eye(3))
        if len(it['F']) >= 3:
            axes += list(np.linalg.svd(it['F'] - it['F'].mean(0), full_matrices=False)[2])
        U = []
        for u in axes:
            u = u / np.linalg.norm(u)
            if all(abs(u @ w) < 0.985 for w in U):
                U.append(u)
        best = None
        for u in U:
            s = Q @ u
            offs = list(np.quantile(s, np.linspace(0.05, 0.95, 19)))
            if len(it['F']):
                fs = it['F'] @ u
                offs += [fs.min() - 0.5 * pitch, fs.max() + 0.5 * pitch, float(np.median(fs))]
            for o in offs:
                L, R = it['idx'][s <= o + pitch / 2], it['idx'][s >= o - pitch / 2]
                if len(L) < 4 or len(R) < 4 or len(L) == len(it['idx']) or len(R) == len(it['idx']):
                    continue
                try:
                    eL, eR = ConvexHull(P[L]).equations, ConvexHull(P[R]).equations
                except Exception:
                    continue
                F, FW = it['F'], it['FW']
                sc = (FW[np.all(F @ eL[:, :3].T + eL[:, 3] <= 1e-9, axis=1)].sum() +
                      FW[np.all(F @ eR[:, :3].T + eR[:, 3] <= 1e-9, axis=1)].sum()) * vox
                if best is None or sc < best[0]:
                    best = (sc, L, R)
        if best is None:
            it['ex'] = -it['ex'] - 1e-9; stuck += 1; continue
        l, r = mk(best[1]), mk(best[2])
        if l is None or r is None:
            it['ex'] = -it['ex'] - 1e-9; stuck += 1; continue
        items = items[1:] + [l, r]
        steps += 1
    out = [reduce(d['V']) for d in items]
    ex = excess(out, KP, KW)
    return out, dict(steps=steps, stuck=stuck, pieces=len(out), max_excess_cm3=round(max(ex), 4) if ex else 0.0,
                     cap=int(cap))


def body_points(body, pitch=None, n_surf=20000):
    """The body's 2 mm solid grid points plus surface samples (the point sets the repair hulls are built from)."""
    from gmg.interlock import fast_inside
    from gmg import geom
    pitch = pitch or k_('pitch_m')
    lo, hi = body.bounds
    G, _ = grid_points(lo - pitch, hi + pitch, pitch)
    S = geom.surface_samples(body, n_surf, seed=0)[0]
    return np.vstack([S, G[fast_inside(body, G)]])


def route3(body, ev, cap, k_inside=None, log=None):
    t = __import__('time').time()
    hl = coacd(body, cap)
    pts = body_points(body)
    out, rep = repair(hl, pts, body, ev, cap, k_inside=k_inside)
    rep.update(coacd_pieces=len(hl), sec=round(__import__('time').time() - t, 1))
    return out, rep


# ------------------------------------------------------------------------------------------------ route 4
def _boxes(occ):
    """Greedy maximal axis-aligned boxes covering a boolean grid exactly (x, then y, then z growth)."""
    occ = occ.copy()
    nx, ny, nz = occ.shape
    out = []
    for i, j, k in zip(*np.nonzero(occ)):
        if not occ[i, j, k]:
            continue
        x1 = i
        while x1 + 1 < nx and occ[x1 + 1, j, k]:
            x1 += 1
        y1 = j
        while y1 + 1 < ny and occ[i:x1 + 1, y1 + 1, k].all():
            y1 += 1
        z1 = k
        while z1 + 1 < nz and occ[i:x1 + 1, j:y1 + 1, z1 + 1].all():
            z1 += 1
        occ[i:x1 + 1, j:y1 + 1, k:z1 + 1] = False
        out.append((i, j, k, x1, y1, z1))
    return out


def voxel_boxes(body, ev, cap, k_inside=None):
    """Route 4: the 2 mm cells inside the body (centre inside) and outside the keep-out (FREE outside the body, K)
    merged into maximal boxes; over the cap a 4, 6, 8 mm grid (cells kept only if all their 2 mm cells are)."""
    from gmg.interlock import STATE_FREE, fast_inside
    p0 = k_('vox_pitches')[0]
    lo, hi = body.bounds
    lo = lo - p0; hi = hi + p0
    G, n = grid_points(lo, hi, p0)
    keep = fast_inside(body, G)
    if k_inside is not None:
        keep &= ~k_inside(G)
    occ = keep.reshape(n)
    for p in k_('vox_pitches'):
        f = int(round(p / p0))
        m = [int(math.ceil(s / f)) for s in n]
        pad = np.zeros([x * f for x in m], bool)
        pad[:n[0], :n[1], :n[2]] = occ
        coarse = pad.reshape(m[0], f, m[1], f, m[2], f).all(axis=(1, 3, 5)) if f > 1 else occ
        B = _boxes(coarse)
        if len(B) <= cap:
            hulls = []
            for i, j, k, x1, y1, z1 in B:
                a = lo + np.array([i, j, k]) * p
                b = lo + (np.array([x1, y1, z1]) + 1) * p
                hulls.append(np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])]))
            return hulls, dict(pitch_mm=p * 1e3, boxes=len(B), cells=int(coarse.sum()), cap=int(cap))
    return None, dict(why='voxel_boxes_over_cap', cap=int(cap))


# ------------------------------------------------------------------------------------------------ the ladder
def lathe_route(body, lathe_axis, sigma, cap, ev=None, k_inside=None, ring_gap_m=0.0, log=None):
    """Route 2 default pieces: profile, ring pieces at 16 (12, 8 over the cap) sectors, handle residual, continuity
    check. Returns (hulls or None, report, (lathe, pieces))."""
    c, a = lathe_axis
    L, info = Lathe.from_mesh(body, c, a, sigma)
    rep = dict(profile=info)
    if L is None:
        rep['why'] = info.get('why')
        return None, rep, None
    for n_s in (k_('n_sectors'),) + tuple(k_('sector_fallback')):
        pcs = L.pieces(n_s, ring_gap_m=ring_gap_m)
        hl = L.hulls(pcs)
        if len(hl) <= cap:
            break
    else:
        rep['why'] = 'lathe_over_cap'
        return None, rep, None
    rep['n_sectors'] = n_s
    rep['ring_pieces'] = len(hl)
    cont = continuity(L, hl, pcs)
    rep['continuity'] = cont
    if not cont['ok']:
        rep['why'] = 'lathe_wall_gap'
        return None, rep, (L, pcs)
    extra, hinfo = handle_residual(L, hl, body, cap - len(hl), k_inside=k_inside, ev=ev)
    rep['handle'] = hinfo
    if len(hl) + len(extra) > cap:
        rep['why'] = 'lathe_over_cap (with the handle)'
        return None, rep, (L, pcs)
    return hl + extra, rep, (L, pcs)


def route_pieces(body, ev, cap, lathe_axis=None, lathe_ok=False, plate_like=False, plate_hulls=None, sigma=None,
                 k_inside=None, ring_gap_m=0.0, skip=(), log=None):
    """The F-I5.4 ladder for one (default) body. Returns dict(route, hulls, gate, report, tried, lathe)."""
    tried = []
    log = log or (lambda *a: None)
    if plate_hulls is not None:
        g = gate(plate_hulls, body, ev, k_inside)
        tried.append(dict(route='1_plate', gate=g))
        if g['pass_']:
            return dict(route='1_plate', hulls=plate_hulls, gate=g, tried=tried, lathe=None)
    if lathe_ok and not plate_like and lathe_axis is not None and '2' not in skip:
        hl, rep, lp = lathe_route(body, lathe_axis, sigma, cap, ev=ev, k_inside=k_inside, ring_gap_m=ring_gap_m)
        row = dict(route='2_lathe', report=rep)
        if hl is not None:
            g = gate(hl, body, ev, k_inside)
            row['gate'] = g
            if g['pass_']:
                tried.append(row)
                return dict(route='2_lathe', hulls=hl, gate=g, tried=tried, lathe=lp, n_handle=len(hl) - rep['ring_pieces'])
        tried.append(row)
        log('route 2 failed', rep.get('why') or row.get('gate'))
    elif lathe_ok and plate_like:
        tried.append(dict(route='2_lathe', skipped='plate-like (F-I5.4: a flat plate passes rotc alone)'))
    if '3' not in skip:
        try:
            hl, rep = route3(body, ev, cap, k_inside=k_inside)
            g = gate(hl, body, ev, k_inside)
            tried.append(dict(route='3_coacd', report=rep, gate=g))
            if g['pass_'] and len(hl) <= cap:
                return dict(route='3_coacd', hulls=hl, gate=g, tried=tried, lathe=None)
        except Exception as e:                                      # noqa: BLE001
            tried.append(dict(route='3_coacd', error=f'{type(e).__name__}: {e}'))
    hl, rep = voxel_boxes(body, ev, cap, k_inside=k_inside)
    if hl is None:
        tried.append(dict(route='4_voxels', report=rep))
        return dict(route=None, hulls=None, gate=None, tried=tried, lathe=None, why='no compliant pieces')
    g = gate(hl, body, ev, k_inside)
    tried.append(dict(route='4_voxels', report=rep, gate=g))
    return dict(route='4_voxels', hulls=hl, gate=g, tried=tried, lathe=None)


# ================================================================================================================
# Round 2 (PREREG F-I5.15 (1), (2), (4a) and F-I5.16 (2); INTERLOCK.md 21.13.2-21.13.5, 21.14.3). New functions only:
# the round-1 path above is unchanged and stays reachable (collcarve rev 1).
#   Profile2(mesh, c, a, sigma)        per-ray profile: construction rays every 1 deg x 1 mm (exact slice-ray hits),
#                                      wall / solid 2 mm bins, axial rays through the base every 1 mm x 1 deg
#   Profile2.layout(n_s, edges, base)  cavity-safe rings: per sector band the inner face tangent from outside (least
#                                      linear rho with rho >= r_in cos(phi - phi_m) on every construction ray), the
#                                      outer face a chord (greatest linear R with R cos(theta) / cos(phi - phi_m) <=
#                                      r_out); base b1 (one N_s-gon prism per base band) or b2 (disc + rim sectors)
#   search_layout(...)                 F-I5.16 (2): the smallest layout (ascending ring pieces, ties larger volume),
#                                      checks (i) min wall, (ii) intrusion, (iii) continuity vs the SHELL, (iv) gate,
#                                      (v) share >= 0.5 with the handle hulls; ends at floor(165 / objects)
#   continuity2(prof, hulls, ...)      F-I5.15 (1e): rays intersected with the SHELL (parity) and the pieces (exact)
#   intrusion2(prof, hulls, ...)       F-I5.15 (1f): SHELL inner radius minus the pieces' first radius on a ray
#   reference_rings(prof)              F-I5.15 (4a): 64 sectors, bands <= 10 mm, b2 base, no cap
#   carve2(prof, lay, K)               profile-space carve of the rings by convex solids K (round-1 options, exact)
#   route_pieces2(...)                 the F-I5.15 ladder: 1 plate, 2 search_layout, 3 CoACD floor(cap/2) + repair to
#                                      the cap, 4 voxel boxes
#   exact_volume / exact_share / exact_props / ray_hull_intervals / topology_ct (helpers, exact or 1 mm grid)
# GT-free: our SHELL candidates and our grids only.
# ================================================================================================================
C2 = dict(
    ray_dphi_deg=(1.0, 'generic:F-I5.15 (10) construction rays every 1 deg'),
    ray_dh_m=(0.001, 'generic:F-I5.15 (10) construction rays every 1 mm (the topology pitch)'),
    sectors=((8, 12, 16, 20, 24, 32), 'generic:F-I5.15 (10) sector set {8, 12, 16, 20, 24, 32}'),
    split_m=(0.001, 'generic:F-I5.15 (10) greedy 1 mm band splits'),
    base_band_m=(0.030, 'generic:F-I5.15 (10) base bands <= 30 mm'),
    bin_m=(0.002, 'generic:F-I5.15 (1a) wall / solid 2 mm bins (F-I5.4)'),
    intr_tol_m=(1e-6, 'generic:F-I5.15 (10) construction intrusion <= 1e-6 m'),
    cont_dh_m=(0.0005, 'generic:F-I5.15 (10) continuity rays every 0.5 mm'),
    cont_dphi_deg=(1.0, 'generic:F-I5.15 (10) continuity rays every 1 deg'),
    cont_off_deg=(0.5, 'generic:F-I5.15 (10) continuity azimuths offset 0.5 deg'),
    axial_dr_m=(0.001, 'generic:F-I5.15 (10) axial rays every 1 mm in radius'),
    cover=(0.5, 'generic:F-I5.15 (10) a ray is covered when the pieces cover >= 50 % of the SHELL interval'),
    gap_share=(0.01, 'generic:F-I5.15 (10) gaps <= 1 % of the rays'),
    height_share=(0.5, 'generic:F-I5.15 (10) gaps <= 50 % of the azimuths at one height'),
    w_min_m=(0.0015, 'generic:F-I5.15 (10) w_min 1.5 mm (one 1 mm cell plus half a cell; Andres et al. 1997)'),
    f_keep=(0.5, 'informed:F-I5.15 (10) f_keep 0.5 (verify_cc_1 ring cell shares 45-68 %)'),
    ref_sectors=(64, 'generic:F-I5.15 (10) reference rings 64 sectors'),
    ref_band_m=(0.010, 'generic:F-I5.15 (10) reference bands <= 10 mm'),
    coacd_share=(0.5, 'decision:orchestrator 31 Oct ~21:50 UTC: max_convex_hull = floor(cap / 2)'),
    hit_dedup_m=(1e-7, 'generic:numerical duplicate ray hits within 1e-7 m'),
    eps_h_m=(1.3e-7, 'generic:numerical ray heights offset 1.3e-7 m off the mesh vertex levels'),
)


def k2_(name):
    v, o = C2[name]
    if o.startswith('generic'):
        guard.constant(f'cp2.{name}', v if not isinstance(v, tuple) else list(v), o)
    return v


# ------------------------------------------------------------------------------------------------ exact helpers
def _manifold(V):
    import trimesh
    return trimesh.convex.convex_hull(np.asarray(V, np.float64))


def union_mesh(hulls):
    """Exact union of convex pieces (manifold boolean)."""
    import trimesh
    ms = [_manifold(V) for V in hulls]
    if len(ms) == 1:
        return ms[0]
    return trimesh.boolean.union(ms, engine='manifold')


def exact_volume(hulls):
    """Exact volume (m3) of the union of the pieces."""
    return float(union_mesh(hulls).volume) if len(hulls) else 0.0


def exact_share(hulls, body):
    """Share of the SHELL's exact volume inside the union of the pieces (F-I5.15 (4c)(i)), and the volume of the
    pieces outside the SHELL (m3)."""
    import trimesh
    U = union_mesh(hulls)
    inter = trimesh.boolean.intersection([U, body], engine='manifold')
    vb = float(body.volume)
    vi = float(inter.volume) if len(inter.faces) else 0.0
    return dict(share=vi / max(vb, 1e-15), shell_cm3=vb * 1e6, inside_cm3=vi * 1e6,
                outside_cm3=(float(U.volume) - vi) * 1e6, union_cm3=float(U.volume) * 1e6)


def exact_props(hulls, mass):
    """COM and inertia about the COM of the uniform solid of the exact union (V1 N2), mass MASS."""
    U = union_mesh(hulls)
    vol = float(U.volume)
    mp = U.mass_properties
    I = np.asarray(mp['inertia'], np.float64) * (mass / max(float(mp['mass']), 1e-15))
    return dict(com=np.asarray(mp['center_mass'], np.float64).tolist(), inertia=I.tolist(), mass=float(mass),
                volume_cm3=round(vol * 1e6, 3), source='exact union (manifold)')


def ray_hull_intervals(hulls, O, D, t_min=0.0):
    """Exact entry / exit parameters of rays O + t D (t >= t_min) in each convex piece: arrays (rays, pieces) of lo and
    hi, NaN where the ray misses the piece."""
    O = np.asarray(O, np.float64); D = np.asarray(D, np.float64)
    H = hulls if isinstance(hulls, Hulls) else Hulls(hulls)
    n = len(O)
    LO = np.full((n, len(H)), np.nan); HI = np.full((n, len(H)), np.nan)
    for i, eq in enumerate(H.eq):
        A = O @ eq[:, :3].T + eq[:, 3]
        B = D @ eq[:, :3].T
        with np.errstate(divide='ignore', invalid='ignore'):
            t = -A / B
        lo = np.where(B < -1e-15, t, -np.inf).max(1)
        hi = np.where(B > 1e-15, t, np.inf).min(1)
        par = (np.abs(B) <= 1e-15) & (A > 1e-12)
        ok = ~par.any(1)
        lo = np.maximum(lo, t_min)
        ok &= hi > lo + 1e-12
        LO[ok, i] = lo[ok]; HI[ok, i] = hi[ok]
    return LO, HI


def covered_length(LO, HI, a, b):
    """Length of [a, b] (per ray) covered by the union of the intervals (rays, pieces)."""
    lo = np.clip(np.where(np.isfinite(LO), LO, np.inf), a[:, None], b[:, None])
    hi = np.clip(np.where(np.isfinite(HI), HI, -np.inf), a[:, None], b[:, None])
    o = np.argsort(lo, axis=1)
    lo = np.take_along_axis(lo, o, 1); hi = np.take_along_axis(hi, o, 1)
    run = np.maximum.accumulate(np.concatenate([a[:, None], hi], 1), axis=1)[:, :-1]
    return np.maximum(0.0, hi - np.maximum(lo, run)).sum(1)


def topology_ct(occ):
    """(C, T) of a boolean 3-D grid (F-I5.15 (6.3)): C = 26-connected components, T = C + V - chi with chi the Euler
    number at 26-connectivity and V = enclosed voids (6-connected background components of the padded grid - 1)."""
    from skimage.measure import euler_number
    if not occ.any():
        return 0, 0
    P = np.pad(occ, 1)
    _, c = ndimage.label(P, structure=np.ones((3, 3, 3)))
    _, nb = ndimage.label(~P, structure=ndimage.generate_binary_structure(3, 1))
    chi = int(euler_number(P, connectivity=3))
    v = int(nb) - 1
    return int(c), int(c + v - chi)


# ------------------------------------------------------------------------------------------------ slice-ray hits
def _tri_crossings(V2, F, s):
    """Segments where the plane s = 0 cuts the triangles (s per vertex; zeros perturbed to +0): (segments, 2, k) of
    the vertex coordinates V2 interpolated."""
    s = np.where(s == 0.0, 1e-300, s)
    S = s[F]                                            # (tris, 3)
    E = [(0, 1), (1, 2), (2, 0)]
    cross = np.stack([S[:, i] * S[:, j] < 0 for i, j in E], 1)
    tri = cross.sum(1) == 2
    if not tri.any():
        return np.zeros((0, 2, V2.shape[1]))
    Ft, St, Ct = F[tri], S[tri], cross[tri]
    pts = []
    for e, (i, j) in enumerate(E):
        t = St[:, i] / (St[:, i] - St[:, j])
        P = V2[Ft[:, i]] + t[:, None] * (V2[Ft[:, j]] - V2[Ft[:, i]])
        pts.append(np.where(Ct[:, e][:, None], P, np.nan))
    P3 = np.stack(pts, 1)                               # (tris, 3 edges, k)
    sel = np.argsort(~Ct, axis=1, kind='stable')[:, :2]
    return np.take_along_axis(P3, sel[:, :, None], 1)


def _line_hits(seg, coord, val, other, keep=None):
    """Hits of the lines coord = val (one per entry of VAL) with the segments: matrix (hits, len(val)) of the OTHER
    coordinate, sorted, duplicates removed (NaN-padded), and the hit counts."""
    if not len(seg):
        return np.full((0, len(val)), np.nan), np.zeros(len(val), int)
    a0, a1 = seg[:, 0, coord][:, None], seg[:, 1, coord][:, None]
    b0, b1 = seg[:, 0, other][:, None], seg[:, 1, other][:, None]
    v = np.asarray(val)[None, :]
    d0 = np.where(a0 - v == 0, 1e-300, a0 - v); d1 = np.where(a1 - v == 0, 1e-300, a1 - v)
    m = d0 * d1 < 0
    with np.errstate(divide='ignore', invalid='ignore'):
        t = d0 / (d0 - d1)
    X = np.where(m, b0 + t * (b1 - b0), np.nan)
    if keep is not None:
        X = np.where(keep(X), X, np.nan)
    X = np.sort(X, axis=0)
    if len(X) > 1:
        dup = np.r_[np.zeros((1, X.shape[1]), bool), np.diff(X, axis=0) < k2_('hit_dedup_m')]
        X = np.sort(np.where(dup, np.nan, X), axis=0)
    cnt = np.isfinite(X).sum(0)
    kmax = int(cnt.max()) if len(cnt) else 0
    return X[:max(kmax, 1)], cnt


class Profile2:
    """Per-ray profile of a SHELL about its structure axis (F-I5.15 (1a)). Lathe frame: origin c, z along a, x along e1
    rotated by PHASE. Construction rays: azimuths j deg (j = 0..359), heights h_lo + (k + 1/2) mm; per ray the
    innermost radial interval [r_in, r_out] (r_in = 0 when the ray starts in material) and the interval count."""

    def __init__(self, mesh, c, a, sigma, phase=0.0):
        self.mesh = mesh
        self.c = np.asarray(c, np.float64)
        a_, e1, e2 = _frame(a)
        if phase:
            e1, e2 = math.cos(phase) * e1 + math.sin(phase) * e2, -math.sin(phase) * e1 + math.cos(phase) * e2
        self.a, self.e1, self.e2 = a_, e1, e2
        self.sigma = float(sigma)
        self.R = np.stack([e1, e2, a_], 1)               # object -> lathe: (X - c) @ R
        self.V = (np.asarray(mesh.vertices, np.float64) - self.c) @ self.R
        self.F = np.asarray(mesh.faces, np.int64)
        self.h_lo, self.h_hi = float(self.V[:, 2].min()), float(self.V[:, 2].max())
        self.rmax = float(np.hypot(self.V[:, 0], self.V[:, 1]).max())
        dh = k2_('ray_dh_m')
        n = max(int(math.floor((self.h_hi - self.h_lo) / dh + 1e-9)), 1)
        self.levels = self.h_lo + dh * np.arange(n + 1)
        if self.levels[-1] < self.h_hi - 1e-9:
            self.levels = np.r_[self.levels, self.h_hi]
        self.H = 0.5 * (self.levels[:-1] + self.levels[1:]) + k2_('eps_h_m')
        self.phis = np.radians(np.arange(0.0, 360.0, k2_('ray_dphi_deg')))
        self.rin, self.rout, self.nint = self.radial(self.H, self.phis)
        self._cache = {}
        self.info = dict(rows=len(self.H), azimuths=len(self.phis), h_span_mm=[round(self.h_lo * 1e3, 2),
                                                                           round(self.h_hi * 1e3, 2)])

    # ---- coordinates
    def to_obj(self, h, r, phi):
        h, r, phi = np.broadcast_arrays(np.asarray(h, float), np.asarray(r, float), np.asarray(phi, float))
        L = np.stack([r * np.cos(phi), r * np.sin(phi), h], -1)
        return L @ self.R.T + self.c

    def cyl(self, X):
        L = (np.asarray(X, np.float64) - self.c) @ self.R
        return L[:, 2], np.hypot(L[:, 0], L[:, 1]), np.arctan2(L[:, 1], L[:, 0])

    # ---- exact slice-ray hits
    def _slice(self, phi):
        s = -self.V[:, 0] * math.sin(phi) + self.V[:, 1] * math.cos(phi)
        u = self.V[:, 0] * math.cos(phi) + self.V[:, 1] * math.sin(phi)
        return _tri_crossings(np.c_[u, self.V[:, 2]], self.F, s)

    def radial(self, H, phis):
        """Innermost radial interval and interval count on the rays (height H, azimuth phi) from the axis."""
        rin = np.full((len(H), len(phis)), np.nan); rout = rin.copy(); nint = np.zeros((len(H), len(phis)), int)
        for j, phi in enumerate(phis):
            seg = self._slice(phi)
            X, cnt = _line_hits(seg, 1, H, 0, keep=lambda X: X >= 0)
            odd = cnt % 2 == 1
            has = cnt > 0
            r0 = np.where(odd, 0.0, X[0]); r1 = np.where(odd, X[0], X[1] if len(X) > 1 else np.nan)
            rin[has, j] = r0[has]; rout[has, j] = r1[has]
            nint[:, j] = (cnt + 1) // 2
        return rin, rout, nint

    def axial(self, radii, phis):
        """Sorted hits (z) of rays parallel to the axis at (radius, azimuth), from below: list per azimuth of a
        (hits, radii) matrix."""
        out = []
        for phi in phis:
            seg = self._slice(phi)
            X, cnt = _line_hits(seg, 0, radii, 1)
            out.append(X)
        return out

    # ---- kinds and runs (2 mm bins, F-I5.4 rule)
    def runs(self):
        if 'runs' in self._cache:
            return self._cache['runs']
        nb = len(self.H)
        bins = [list(range(i, min(i + 2, nb))) for i in range(0, nb, 2)]
        thr = max(k_('wall_k_sigma') * self.sigma, k_('wall_min_m'))
        kind, ok = [], []
        info = dict(wall_threshold_mm=round(thr * 1e3, 3))
        for rows in bins:
            ri = self.rin[rows]; ni = self.nint[rows]
            has = np.isfinite(ri)
            if not has.any():
                kind.append(None); continue
            if np.median(ni[has]) > 2:
                info['why'] = 'lathe_profile_complex (more than two radial intervals in a bin)'
                self._cache['runs'] = (None, info)
                return self._cache['runs']
            kind.append('wall' if float(np.median(ri[has])) > thr else 'solid')
        mat = [k is not None for k in kind]
        if not any(mat):
            info['why'] = 'lathe_no_material'
            self._cache['runs'] = (None, info); return self._cache['runs']
        i0 = mat.index(True); i1 = len(mat) - 1 - mat[::-1].index(True)
        if not all(mat[i0:i1 + 1]):
            info['why'] = 'lathe_profile_complex (empty bin between material bins)'
            self._cache['runs'] = (None, info); return self._cache['runs']
        out, s = [], i0
        for i in range(i0 + 1, i1 + 2):
            if i == i1 + 1 or kind[i] != kind[s]:
                r0, r1 = bins[s][0], bins[i - 1][-1]
                out.append(dict(kind=kind[s], row0=r0, row1=r1, lo=float(self.levels[r0]),
                                hi=float(self.levels[r1 + 1])))
                s = i
        info.update(runs=[(r['kind'], round(r['lo'] * 1e3, 2), round(r['hi'] * 1e3, 2)) for r in out])
        self._cache['runs'] = (out, info)
        return self._cache['runs']

    # ---- per-sector rows (completion by revolution)
    def sector_rows(self, n_s, s):
        key = ('rows', n_s, s)
        if key in self._cache:
            return self._cache[key]
        th = math.pi / n_s
        fm = (2 * s + 1) * th
        d = np.angle(np.exp(1j * (self.phis - fm)))
        sel = np.nonzero(np.abs(d) <= th + 1e-9)[0]
        psi = d[sel]
        ri = self.rin[:, sel].copy(); ro = self.rout[:, sel].copy()
        has = np.isfinite(ro)
        med_i = np.nanmedian(np.where(np.isfinite(self.rout), self.rin, np.nan), axis=1) \
            if np.isfinite(self.rout).any() else None
        med_o = np.nanmedian(self.rout, axis=1) if np.isfinite(self.rout).any() else None
        few = has.sum(1) * 2 < len(sel)
        if few.any():
            ri[few] = med_i[few][:, None]; ro[few] = med_o[few][:, None]
        y = np.nanmax(ri * np.cos(psi)[None], axis=1)            # inner constraint per row
        z = np.nanmin(ro * np.cos(psi)[None] / math.cos(th), axis=1)   # outer constraint per row
        self._cache[key] = (y, z, int(few.sum()))
        return self._cache[key]

    # ---- axial base data (cached per sector count)
    def base_data(self):
        if 'base' in self._cache:
            return self._cache['base']
        dr = k2_('axial_dr_m')
        radii = dr * (np.arange(int(math.ceil(self.rmax / dr)) + 1) + 0.5)
        self._cache['base'] = (radii, self.axial(radii, self.phis))
        return self._cache['base']

    def base_surfaces(self, run):
        """Per axial construction ray (azimuth, radius) of a solid run: the bottom (lowest hit) and the cavity floor
        (top of the first interval when it ends within the run + 1 mm), NaN where absent."""
        radii, Xs = self.base_data()
        lo, hi = run['lo'], run['hi']
        bot = np.full((len(self.phis), len(radii)), np.nan); flo = bot.copy(); top = bot.copy()
        for j, X in enumerate(Xs):
            if X.shape[0] < 2:
                continue
            for k in range(0, X.shape[0] - 1, 2):
                a_, b_ = X[k], X[k + 1]
                m = np.isfinite(a_) & np.isfinite(b_) & (b_ > lo) & (a_ < hi) & ~np.isfinite(bot[j])
                bot[j, m] = a_[m]; top[j, m] = b_[m]
                f = m & (b_ <= hi + k2_('ray_dh_m'))
                flo[j, f] = b_[f]
        return radii, bot, flo, top


# ------------------------------------------------------------------------------------------------ envelopes
def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def env_line(h, y, hm, upper):
    """Linear function f(x) = v + g (x - hm) that is >= y (upper) or <= y (lower) at every point and extremal at hm
    (least for upper, greatest for lower): the hull edge of the points spanning hm. Returns (v, g) or None."""
    m = np.isfinite(y)
    h = np.asarray(h, float)[m]; y = np.asarray(y, float)[m]
    if not len(h):
        return None
    if len(h) == 1:
        return float(y[0]), 0.0
    hull = []
    for p in zip(h.tolist(), y.tolist()):
        while len(hull) >= 2 and ((_cross(hull[-2], hull[-1], p) >= 0) if upper else (_cross(hull[-2], hull[-1], p) <= 0)):
            hull.pop()
        hull.append(p)
    if len(hull) == 1:
        return float(hull[0][1]), 0.0
    i = 0
    while i < len(hull) - 2 and hull[i + 1][0] < hm:
        i += 1
    (x0, y0), (x1, y1) = hull[i], hull[i + 1]
    g = (y1 - y0) / (x1 - x0) if x1 > x0 else 0.0
    v = y0 + g * (hm - x0)
    res = y - (v + g * (h - hm))                        # exactness against rounding
    v += float(res.max()) if upper else float(res.min())
    return float(v), float(g)


# ------------------------------------------------------------------------------------------------ ring layout
def _wall_piece(prof, n_s, s, h0, h1, run_i):
    """Sector-band wall piece: inner face tangent from outside, outer face a chord (F-I5.15 (1b))."""
    th = math.pi / n_s
    y, z, _ = prof.sector_rows(n_s, s)
    H = prof.H
    rows = np.nonzero((H >= h0 - 1e-9) & (H <= h1 + 1e-9))[0]
    if not len(rows):                                    # band thinner than a row: the nearest row
        rows = np.array([int(np.argmin(np.abs(H - 0.5 * (h0 + h1))))])
    hm = 0.5 * (h0 + h1)
    li = env_line(H[rows], y[rows], hm, True)
    lo = env_line(H[rows], z[rows], hm, False)
    if li is None or lo is None:
        return None
    rho0, rho1 = li[0] + li[1] * (h0 - hm), li[0] + li[1] * (h1 - hm)
    R0, R1 = lo[0] + lo[1] * (h0 - hm), lo[0] + lo[1] * (h1 - hm)
    return dict(kind='wall', s=int(s), n_s=int(n_s), run=int(run_i), h0=float(h0), h1=float(h1), rho0=float(rho0),
                rho1=float(rho1), R0=float(R0), R1=float(R1))


def piece_wall_min(p):
    """Min wall left of a wall piece (mid: R cos(theta) - rho; edges: R - rho / cos(theta), at both ends)."""
    th = math.pi / p['n_s']
    c = math.cos(th)
    return float(min(p['R0'] * c - p['rho0'], p['R1'] * c - p['rho1'], p['R0'] - p['rho0'] / c, p['R1'] - p['rho1'] / c))


def piece_volume(p):
    th = math.pi / p['n_s']
    if p['kind'] == 'wall':
        sc, tn = math.sin(th) * math.cos(th), math.tan(th)

        def A(rho, R):
            return R * R * sc - rho * rho * tn
        return (p['h1'] - p['h0']) / 6.0 * (A(p['rho0'], p['R0']) + 4 * A(0.5 * (p['rho0'] + p['rho1']),
                                                                         0.5 * (p['R0'] + p['R1'])) + A(p['rho1'], p['R1']))
    if p['kind'] == 'base1':
        return (p['h1'] - p['h0']) * p['n_s'] * p['R'] ** 2 * math.sin(th) * math.cos(th)
    if p['kind'] == 'disc':
        return (p['h1'] - p['h0']) * p['n_s'] * p['rc'] ** 2 * math.sin(th) * math.cos(th)
    return (p['h1'] - p['h0']) * (p['R'] ** 2 - p['rc'] ** 2) * math.sin(th) * math.cos(th)


def _face_planes(prof, p):
    """The inner face {x . u >= rho(h)} and the outer chord {x . u <= R(h) cos(theta)} of a wall piece as half-spaces
    n . x + d <= 0 in the object frame."""
    th = math.pi / p['n_s']
    fm = (2 * p['s'] + 1) * th
    u = math.cos(fm) * prof.e1 + math.sin(fm) * prof.e2
    a, c0 = prof.a, prof.c
    dh = max(p['h1'] - p['h0'], 1e-12)
    si = (p['rho1'] - p['rho0']) / dh
    so = (p['R1'] - p['R0']) / dh * math.cos(th)
    n_in = -u + si * a
    d_in = u @ c0 - si * (a @ c0) + p['rho0'] - si * p['h0']
    n_out = u - so * a
    d_out = -(u @ c0) + so * (a @ c0) - p['R0'] * math.cos(th) + so * p['h0']
    return np.array([np.r_[n_in, d_in], np.r_[n_out, d_out]])


def piece_verts(prof, p):
    """Vertices of a piece. A wall piece is the hull of its 8 face vertices; where its wall would be negative (the
    outer chord inside the tangent inner face) it is clipped by both face planes, and None when nothing is left (so a
    piece never reaches into the cavity, whatever the candidate; such a candidate fails check (i))."""
    th = math.pi / p['n_s']
    if p['kind'] == 'wall':
        fm = (2 * p['s'] + 1) * th
        c = math.cos(th)
        rows = []
        for h, rho, R in ((p['h0'], p['rho0'], p['R0']), (p['h1'], p['rho1'], p['R1'])):
            for f in (fm - th, fm + th):
                rows += [(h, rho / c, f), (h, R, f)]
        h, r, f = np.array(rows).T
        V = prof.to_obj(h, r, f)
        if piece_wall_min(p) < 0:
            return clip_vertices(V, _face_planes(prof, p))
        return V
    if p['kind'] in ('base1', 'disc'):
        r = p['R'] if p['kind'] == 'base1' else p['rc']
        f = 2 * th * np.arange(p['n_s'])
        return np.vstack([prof.to_obj(np.full(p['n_s'], h), np.full(p['n_s'], r), f) for h in (p['h0'], p['h1'])])
    fm = (2 * p['s'] + 1) * th
    rows = [(h, r, f) for h in (p['h0'], p['h1']) for f in (fm - th, fm + th) for r in (p['rc'], p['R'])]
    h, r, f = np.array(rows).T
    return prof.to_obj(h, r, f)


def _base_pieces(prof, n_s, run, kind, lowest):
    """Base pieces of a solid run: b1 = one N_s-gon prism per base band (top at the run's lowest cavity floor, bottom at
    the run's lowest SHELL bottom point; F-I5.16 (2)); b2 = centre disc (r / 2) plus N_s rim sectors, per piece top at
    or below the floor and bottom at or above the bottom surface on its axial rays (F-I5.15 (1c)). Returns (pieces,
    per-sector base top, info)."""
    th = math.pi / n_s
    radii, bot, flo, top = prof.base_surfaces(run)
    Rs = []
    rows_all = np.arange(run['row0'], run['row1'] + 1)
    for s in range(n_s):
        y, z, _ = prof.sector_rows(n_s, s)
        Rs.append(float(np.nanmin(z[rows_all])))
    R = float(min(Rs))
    fl = np.where(np.isfinite(flo), flo, np.nan)
    tp = np.where(np.isfinite(top), top, np.nan)
    inside = radii[None, :] <= R + 1e-9
    has_floor = np.isfinite(fl) & inside
    top_all = float(np.nanmin(fl[has_floor])) if has_floor.any() else float(np.nanmin(np.where(inside, tp, np.nan)))
    bmask = np.isfinite(bot) & inside
    bottom = float(np.nanmin(bot[bmask]) if lowest else np.nanmax(bot[bmask])) if bmask.any() else run['lo']
    info = dict(R_mm=round(R * 1e3, 3), top_mm=round(top_all * 1e3, 3), bottom_mm=round(bottom * 1e3, 3),
                floor_rays=int(has_floor.sum()))
    out = []
    if kind == 'b1':
        nb = max(int(math.ceil((top_all - bottom) / k2_('base_band_m') - 1e-9)), 1)
        e = np.linspace(bottom, top_all, nb + 1)
        for h0, h1 in zip(e[:-1], e[1:]):
            rows = np.nonzero((prof.H >= h0) & (prof.H <= h1))[0]
            Rb = R if not len(rows) else float(min(np.nanmin(prof.sector_rows(n_s, s)[1][rows]) for s in range(n_s)))
            out.append(dict(kind='base1', n_s=n_s, s=-1, h0=float(h0), h1=float(h1), R=Rb))
        return out, [top_all] * n_s, info
    rc = 0.5 * R
    phij = prof.phis
    ins_c = radii[None, :] < rc
    t_d = float(np.nanmin(np.where(ins_c & np.isfinite(fl), fl, np.nan))) if (ins_c & np.isfinite(fl)).any() else top_all
    b_d = float(np.nanmax(np.where(ins_c & np.isfinite(bot), bot, np.nan))) if (ins_c & np.isfinite(bot)).any() else bottom
    out.append(dict(kind='disc', n_s=n_s, s=-1, h0=b_d, h1=t_d, rc=rc))
    tops = []
    for s in range(n_s):
        fm = (2 * s + 1) * th
        d = np.abs(np.angle(np.exp(1j * (phij - fm)))) <= th + 1e-9
        m = d[:, None] & (radii[None, :] >= rc) & (radii[None, :] <= Rs[s] * math.cos(th))
        ts = float(np.nanmin(np.where(m & np.isfinite(fl), fl, np.nan))) if (m & np.isfinite(fl)).any() else top_all
        bs = float(np.nanmax(np.where(m & np.isfinite(bot), bot, np.nan))) if (m & np.isfinite(bot)).any() else bottom
        out.append(dict(kind='rim', n_s=n_s, s=s, h0=bs, h1=ts, rc=rc, R=Rs[s]))
        tops.append(ts)
    return out, tops, info


def build_layout(prof, n_s, base, edges, forced=None):
    """Pieces of one layout: N_s sectors, base kind ('b1' / 'b2'), EDGES = {wall run index: interior band edges
    (heights)} common to the sectors of the run; FORCED = extra edges (heights) per run (the carve's ends)."""
    runs, rinfo = prof.runs()
    pieces, starts, binfo = [], {}, []
    tops_prev = None
    for i, r in enumerate(runs):
        if r['kind'] == 'solid':
            ps, tops, inf = _base_pieces(prof, n_s, r, base, lowest=(i == 0))
            pieces += ps
            binfo.append(inf)
            tops_prev = tops
        else:
            starts[i] = tops_prev if (i > 0 and tops_prev is not None) else [r['lo']] * n_s
            tops_prev = None
    for i, r in enumerate(runs):
        if r['kind'] != 'wall':
            continue
        e_in = sorted(set(list(edges.get(i, [])) + list((forced or {}).get(i, []))))
        for s in range(n_s):
            st = starts[i][s]
            E = [st] + [e for e in e_in if st + 1e-6 < e < r['hi'] - 1e-6] + [r['hi']]
            for h0, h1 in zip(E[:-1], E[1:]):
                p = _wall_piece(prof, n_s, s, h0, h1, i)
                if p is not None:
                    pieces.append(p)
    nd = len(pieces)
    n_nominal = nd                                        # N_s B_w + base pieces (the search order, F-I5.16 (2))
    walls_all = [piece_wall_min(p) for p in pieces if p['kind'] == 'wall']
    pieces = [p for p in pieces if p['kind'] != 'wall' or piece_wall_min(p) >= 0 or piece_verts(prof, p) is not None]
    n_wall = sum(p['kind'] == 'wall' for p in pieces)
    vol = sum(max(piece_volume(p), 0.0) for p in pieces)
    walls = walls_all
    return dict(n_s=int(n_s), base=base, dropped_negative_wall=nd - len(pieces), edges={int(k): [float(x) for x in v] for k, v in edges.items()},
                forced={int(k): [float(x) for x in v] for k, v in (forced or {}).items()}, pieces=pieces,
                n_r=n_nominal, n_pieces=len(pieces), n_wall=n_wall, ring_cm3=vol * 1e6, min_wall_mm=(min(walls) * 1e3 if walls else None),
                base_info=binfo)


def layout_hulls(prof, lay):
    return [reduce(V) for V in (piece_verts(prof, p) for p in lay['pieces']) if V is not None]


def greedy_edges(prof, n_s, max_bands, start_of_run):
    """F-I5.15 (1d) greedy nested band edges: one band per wall run, then repeatedly the one 1 mm split (over all
    bands) that gains the most ring volume. Returns the list of edge dicts for B_w = W_r, W_r + 1, ..., max_bands."""
    runs, _ = prof.runs()
    walls = [i for i, r in enumerate(runs) if r['kind'] == 'wall']
    if not walls:
        return [{}]
    bands = {i: [(start_of_run[i], runs[i]['hi'])] for i in walls}
    cache = {}

    def vol(i, h0, h1):
        key = (i, round(h0, 9), round(h1, 9))
        if key not in cache:
            v = 0.0
            for s in range(n_s):
                p = _wall_piece(prof, n_s, s, h0, h1, i)
                v += piece_volume(p) if p is not None else 0.0
            cache[key] = v
        return cache[key]
    seq = [{i: [] for i in walls}]
    nb = len(walls)
    lv = prof.levels
    while nb < max_bands:
        best = None
        for i in walls:
            for bi, (h0, h1) in enumerate(bands[i]):
                v0 = vol(i, h0, h1)
                for x in lv[(lv > h0 + 1e-6) & (lv < h1 - 1e-6)]:
                    g = vol(i, h0, x) + vol(i, x, h1) - v0
                    if best is None or g > best[0] + 1e-15:
                        best = (g, i, bi, float(x))
        if best is None:
            break
        _, i, bi, x = best
        h0, h1 = bands[i][bi]
        bands[i][bi:bi + 1] = [(h0, x), (x, h1)]
        nb += 1
        seq.append({j: [b[0] for b in bands[j][1:]] for j in walls})
    return seq


def _wall_starts(prof, n_s, base):
    runs, _ = prof.runs()
    st = {}
    prev = None
    for i, r in enumerate(runs):
        if r['kind'] == 'solid':
            _, tops, _ = _base_pieces(prof, n_s, r, base, lowest=(i == 0))
            prev = tops
        else:
            st[i] = min(prev) if prev is not None else r['lo']
            prev = None
    return st


# ------------------------------------------------------------------------------------------------ checks
def _sector_start(lay, prof, phi):
    """Wall start height (per sector) and the run of each wall band, from the layout's lowest wall pieces."""
    n_s = lay['n_s']
    s = (np.floor(np.mod(phi, 2 * math.pi) / (2 * math.pi / n_s))).astype(int) % n_s
    return s


def _wall_rays(prof, lay, H, phis, rin, rout):
    """Radial rays of the wall runs at heights H (>= the ray's sector wall start) x azimuths: (O, D, a, b, h, phi)."""
    runs, _ = prof.runs()
    st = _wall_starts(prof, lay['n_s'], lay['base'])     # from the SHELL (base tops), never from the pieces
    rows, cols = [], []
    for i, r in enumerate(runs):
        if r['kind'] != 'wall':
            continue
        lo = np.full(len(phis), st.get(i, r['lo']))
        m = (H[:, None] >= lo[None, :]) & (H[:, None] <= r['hi'])
        a, b = np.nonzero(m)
        rows.append(a); cols.append(b)
    if not rows:
        return None
    a = np.concatenate(rows); b = np.concatenate(cols)
    h, f = H[a], phis[b]
    O = prof.to_obj(h, np.zeros_like(h), f)
    D = np.cos(f)[:, None] * prof.e1 + np.sin(f)[:, None] * prof.e2
    return O, D, rin[a, b], rout[a, b], h, f, a, b


def intrusion2(prof, lay, hulls, H=None, phis=None, rin=None, rout=None):
    """Max intrusion of the pieces into the cavity (SHELL inner radius minus the pieces' first radius, positive =
    inside the cavity) on the radial rays of the wall runs (default: the construction rays)."""
    if H is None:
        H, phis, rin, rout = prof.H, prof.phis, prof.rin, prof.rout
    R = _wall_rays(prof, lay, H, phis, rin, rout)
    if R is None:
        return dict(max_mm=None, rays=0)
    O, D, a, b, h, f, _, _ = R
    ok = np.isfinite(a) & (a > 0)
    LO, HI = ray_hull_intervals(hulls, O[ok], D[ok])
    first = np.nanmin(np.where(np.isfinite(LO), LO, np.nan), axis=1) if LO.shape[1] else np.full(ok.sum(), np.nan)
    hit = np.isfinite(first)
    intr = a[ok][hit] - first[hit]
    return dict(max_mm=round(float(intr.max()) * 1e3, 6) if len(intr) else None, rays=int(ok.sum()),
                rays_hit=int(hit.sum()), max_m=float(intr.max()) if len(intr) else None,
                n_positive=int((intr > k2_('intr_tol_m')).sum()))


def continuity2(prof, lay, hulls):
    """F-I5.15 (1e): rays from the axis every 0.5 mm x 1 deg (offset 0.5 deg) over each wall run and axial rays every
    1 mm x 1 deg through the base, intersected with the SHELL (parity) and with the union of the pieces (exact). A ray
    is a gap when the SHELL has a wall (base) interval on it and the pieces cover < 50 % of it. Rejected
    (lathe_wall_gap) when gaps > 1 % of the rays with a SHELL interval or > 50 % of the azimuths at one height."""
    key = 'cont'
    if key not in prof._cache:
        dh = k2_('cont_dh_m')
        Hc = np.arange(prof.h_lo + 0.5 * dh, prof.h_hi, dh) + k2_('eps_h_m')
        phc = np.radians(np.arange(0.0, 360.0, k2_('cont_dphi_deg')) + k2_('cont_off_deg'))
        rin, rout, _ = prof.radial(Hc, phc)
        dr = k2_('axial_dr_m')
        radii = dr * (np.arange(int(math.ceil(prof.rmax / dr)) + 1) + 0.5)
        prof._cache[key] = (Hc, phc, rin, rout, radii, prof.axial(radii, phc))
    Hc, phc, rin, rout, radii, Xs = prof._cache[key]
    out = dict()
    R = _wall_rays(prof, lay, Hc, phc, rin, rout)
    n_sh = 0; n_gap = 0
    worst_h = 0.0
    if R is not None:
        O, D, a, b, h, f, ia, ib = R
        ok = np.isfinite(a) & np.isfinite(b) & (b > a)
        LO, HI = ray_hull_intervals(hulls, O[ok], D[ok])
        cov = covered_length(LO, HI, a[ok], b[ok])
        gap = cov < k2_('cover') * (b[ok] - a[ok])
        first = np.nanmin(np.where(np.isfinite(LO), LO, np.nan), axis=1) if LO.shape[1] else np.full(ok.sum(), np.nan)
        hit = np.isfinite(first) & (a[ok] > 0)
        intr = a[ok][hit] - first[hit]
        n_sh += int(ok.sum()); n_gap += int(gap.sum())
        rows = ia[ok]
        if len(rows):
            tot = np.bincount(rows, minlength=len(Hc)); gp = np.bincount(rows, weights=gap, minlength=len(Hc))
            share = np.where(tot > 0, gp / np.maximum(tot, 1), 0.0)
            worst_h = float(share.max())
            out['worst_height_mm'] = round(float(Hc[int(np.argmax(share))]) * 1e3, 2)
        out.update(radial_rays=int(ok.sum()), radial_gaps=int(gap.sum()),
                   cover_share_min=round(float((cov / (b[ok] - a[ok])).min()), 4) if ok.any() else None,
                   cover_share_median=round(float(np.median(cov / (b[ok] - a[ok]))), 4) if ok.any() else None,
                   intrusion_max_mm=round(float(intr.max()) * 1e3, 4) if len(intr) else None)
        if gap.any():
            out['gap_h_mm'] = [round(float(h[ok][gap].min()) * 1e3, 2), round(float(h[ok][gap].max()) * 1e3, 2)]
    # axial rays through the solid runs
    runs, _ = prof.runs()
    sol = [(i, r) for i, r in enumerate(runs) if r['kind'] == 'solid']
    n_ax = 0; g_ax = 0; any_base = False
    z0 = prof.h_lo - 0.01
    for i, r in sol:
        A_, B_, rr, ff = [], [], [], []
        for j, X in enumerate(Xs):
            if X.shape[0] < 2:
                continue
            for k in range(0, X.shape[0] - 1, 2):
                za, zb = X[k], X[k + 1]
                m = np.isfinite(za) & np.isfinite(zb) & (zb > r['lo']) & (za < r['hi'])
                if i > 0:
                    za = np.maximum(za, r['lo'])
                zb = np.minimum(zb, r['hi'])
                sel = np.nonzero(m)[0]
                A_.append(za[sel]); B_.append(zb[sel]); rr.append(radii[sel]); ff.append(np.full(len(sel), phc[j]))
        if not A_:
            continue
        za = np.concatenate(A_); zb = np.concatenate(B_); rr = np.concatenate(rr); ff = np.concatenate(ff)
        if not len(za):
            continue
        any_base = True
        O = prof.to_obj(np.full(len(rr), z0), rr, ff)
        D = np.tile(prof.a, (len(rr), 1))
        LO, HI = ray_hull_intervals(hulls, O, D)
        cov = covered_length(LO, HI, za - z0, zb - z0)
        gap = cov < k2_('cover') * (zb - za)
        n_ax += len(za); g_ax += int(gap.sum())
    out.update(axial_rays=n_ax, axial_gaps=g_ax)
    if not any_base:
        out['flag'] = 'shell_bottomless'
    n_all = n_sh + n_ax
    g_all = n_gap + g_ax
    out.update(rays=n_all, gaps=g_all, gap_share=round(g_all / max(n_all, 1), 5), worst_height_gap_share=round(worst_h, 4))
    out['ok'] = bool(g_all <= k2_('gap_share') * n_all and worst_h <= k2_('height_share'))
    return out


# ------------------------------------------------------------------------------------------------ the search
def _n_base(prof, n_s, base):
    runs, _ = prof.runs()
    n = 0
    for i, r in enumerate(runs):
        if r['kind'] == 'solid':
            n += len(_base_pieces(prof, n_s, r, base, lowest=(i == 0))[0])
    return n


def search_layout(prof, body, ev, cap, k_inside=None, sectors=None, bases=('b1', 'b2'), log=None, stop_at=None):
    """F-I5.16 (2): the smallest cavity-safe ring layout. Candidates N_s x greedy nested bands x base (b1, then b2);
    order ascending ring pieces, ties larger exact ring volume; accepted at the first candidate passing (i) min wall >=
    1.5 mm, (ii) construction intrusion <= 1e-6 m, (iii) continuity against the SHELL, (iv) the pieces gate with the
    handle hulls, (v) share of the SHELL volume >= 0.5 with the handle hulls. The search ends when n_r + n_h > cap.
    Returns (accepted dict or None, report)."""
    log = log or (lambda *a: None)
    runs, rinfo = prof.runs()
    rep = dict(profile=dict(prof.info, **rinfo), tried=[])
    if runs is None:
        rep['why'] = rinfo.get('why')
        return None, rep
    sectors = tuple(sectors or k2_('sectors'))
    W_r = sum(r['kind'] == 'wall' for r in runs)
    cands = []
    for n_s in sectors:
        for base in bases:
            nb = _n_base(prof, n_s, base)
            mb = (cap - nb) // n_s if W_r else 0
            if W_r and mb < W_r:
                continue
            seq = greedy_edges(prof, n_s, mb, _wall_starts(prof, n_s, base)) if W_r else [{}]
            for e in seq:
                cands.append(build_layout(prof, n_s, base, e))
    order = {'b1': 0, 'b2': 1}
    cands.sort(key=lambda L: (L['n_r'], -round(L['ring_cm3'], 6), order[L['base']]))
    wmin = k2_('w_min_m') * 1e3
    for lay in cands:
        row = dict(n_s=lay['n_s'], base=lay['base'], B_w=sum(len(v) + 1 for v in lay['edges'].values()),
                   n_r=lay['n_r'], ring_cm3=round(lay['ring_cm3'], 3), min_wall_mm=None if lay['min_wall_mm'] is None
                   else round(lay['min_wall_mm'], 3))
        rep['tried'].append(row)
        if lay['n_r'] > cap:
            row['fail'] = 'search_end (n_r > cap)'
            break
        if lay['min_wall_mm'] is not None and lay['min_wall_mm'] < wmin - 1e-9:
            row['fail'] = 'min_wall'; continue
        hl = layout_hulls(prof, lay)
        it = intrusion2(prof, lay, hl)
        row['intrusion_construction_mm'] = it['max_mm']
        if it['max_m'] is not None and it['max_m'] > k2_('intr_tol_m'):
            row['fail'] = 'ring_intrusion (code error)'; continue
        cont = continuity2(prof, lay, hl)
        row['continuity'] = cont
        if not cont['ok']:
            row['fail'] = 'lathe_wall_gap'; continue
        extra, hinfo = handle_residual(prof, hl, body, max(cap - len(hl), 1), k_inside=k_inside, ev=ev)
        row['n_h'] = len(extra); row['handle'] = hinfo
        if len(hl) + len(extra) > cap:
            row['fail'] = 'search_end (n_r + n_h > cap)'
            break
        g = gate(hl + extra, body, ev, k_inside)
        row['gate'] = g
        if not g['pass_']:
            row['fail'] = 'gate'; continue
        sh = exact_share(hl + extra, body)
        row['share'] = round(sh['share'], 4)
        row['share_detail'] = {k: round(v, 3) for k, v in sh.items()}
        if sh['share'] < k2_('f_keep') - 1e-12:
            row['fail'] = 'share'; continue
        row['accepted'] = True
        rep['accepted'] = dict(n_s=lay['n_s'], base=lay['base'], n_r=lay['n_r'], n_h=len(extra))
        log('F-I5.16 layout accepted', row)
        return dict(layout=lay, hulls=hl + extra, ring_hulls=hl, handle_hulls=extra, gate=g, share=sh, row=row), rep
    rep['why'] = 'no_accepted_layout'
    return None, rep


def forced_layout(prof, lay, forced):
    """The layout with extra band edges FORCED ({run: heights}, snapped outward to the 1 mm levels; the carve's ends,
    D2 (b))."""
    return build_layout(prof, lay['n_s'], lay['base'], lay['edges'], forced)


def reference_rings(prof, handle_hulls=()):
    """F-I5.15 (4a): the round-2 rings at 64 sectors with bands <= 10 mm and no cap (b2 base, F-I5.15 (1c)), plus the
    handle hulls. Never delivered."""
    n_s = k2_('ref_sectors')
    runs, info = prof.runs()
    if runs is None:
        return None, None
    st = _wall_starts(prof, n_s, 'b2')
    edges = {}
    for i, r in enumerate(runs):
        if r['kind'] != 'wall':
            continue
        L = r['hi'] - st[i]
        nb = max(int(math.ceil(L / k2_('ref_band_m') - 1e-9)), 1)
        e = st[i] + L * np.arange(1, nb) / nb
        lv = prof.levels
        edges[i] = sorted(set(float(lv[int(np.argmin(np.abs(lv - x)))]) for x in e))
    lay = build_layout(prof, n_s, 'b2', edges)
    return layout_hulls(prof, lay) + [np.asarray(V) for V in handle_hulls], lay


# ------------------------------------------------------------------------------------------------ carve (rings)
def _wall_u(prof, p):
    th = math.pi / p['n_s']
    fm = (2 * p['s'] + 1) * th
    return math.cos(fm) * prof.e1 + math.sin(fm) * prof.e2, math.cos(th)


def _lin(p, key, h):
    t = (h - p['h0']) / max(p['h1'] - p['h0'], 1e-12)
    return p[key + '0'] + t * (p[key + '1'] - p[key + '0'])


def _options2(prof, p, Q, wk):
    h = (Q - prof.c) @ prof.a
    opts = []
    hmin, hmax = float(h.min()), float(h.max())
    if hmin > p['h0'] + 1e-6:                               # trim the top to below K
        q = dict(p, h1=hmin)
        if p['kind'] == 'wall':
            q.update(rho1=_lin(p, 'rho', hmin), R1=_lin(p, 'R', hmin))
        opts.append(('trim_top', q))
    if hmax < p['h1'] - 1e-6:                               # trim the bottom to above K
        q = dict(p, h0=hmax)
        if p['kind'] == 'wall':
            q.update(rho0=_lin(p, 'rho', hmax), R0=_lin(p, 'R', hmax))
        opts.append(('trim_bottom', q))
    if p['kind'] == 'wall':
        u, cs = _wall_u(prof, p)
        qv = (Q - prof.c) @ u
        hm = 0.5 * (p['h0'] + p['h1'])
        Ah = np.c_[np.ones(len(h)), h - hm]
        Ak = np.array([[1.0, p['h0'] - hm], [1.0, p['h1'] - hm]])
        rho_o = np.array([p['rho0'], p['rho1']]); R_o = np.array([p['R0'], p['R1']])
        # (i) widen: least rho with rho(h_v) >= q_v, rho >= old rho, rho <= R cos(theta) - wk at the ends
        A = np.vstack([-Ah, -Ak, Ak]); b = np.r_[-qv, -rho_o, R_o * cs - wk]
        r = linprog([1.0, 0.0], A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
        if r.success:
            v = Ak @ r.x
            opts.append(('widen', dict(p, rho0=float(v[0]), rho1=float(v[1]))))
        # (ii) shrink: greatest R with R(h_v) cos(theta) <= q_v, R <= old R, R cos(theta) >= rho + wk at the ends
        A = np.vstack([Ah * cs, Ak, -Ak * cs]); b = np.r_[qv, R_o, -(rho_o + wk)]
        r = linprog([-1.0, 0.0], A_ub=A, b_ub=b, bounds=[(None, None)] * 2, method='highs')
        if r.success:
            v = Ak @ r.x
            opts.append(('shrink', dict(p, R0=float(v[0]), R1=float(v[1]))))
    return opts


def carve2(prof, lay, K, wk=None):
    """Remove the convex solids K (exact fragments of K inside R+, posed in the receiver frame) from the ring pieces:
    per conflicting piece the option (trim top / bottom, widen the inner face, shrink the outer chord; exact: every
    vertex of K inside the piece ends on the removed side of a plane) that keeps the most volume; no option -> the
    piece is removed. Iterates until no piece holds a K fragment (<= 6 rounds). Returns (pieces, report)."""
    wk = k_('wall_keep_m') if wk is None else wk
    KH = Hulls(K)
    KP = [hull_parts(V) for V in KH.V]
    P = [dict(p) for p in lay['pieces']]
    rep = dict(conflicts=0, options={}, removed_pieces=0, rounds=0)
    todo = list(range(len(P)))
    for rnd in range(6):
        rep['rounds'] = rnd + 1
        nxt = []
        for i in todo:
            p = P[i]
            if p is None:
                continue
            V = piece_verts(prof, p)
            try:
                PP = hull_parts(V)
            except Exception:
                continue
            lo, hi = V.min(0), V.max(0)
            cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0] if len(KH) else []
            Qs = [Q for Q in (intersect_points(KP[j], PP) for j in cand) if Q is not None]
            if not Qs:
                continue
            rep['conflicts'] += 1
            Q = np.vstack(Qs)
            v0 = piece_volume(p)
            best = None
            for name, q in _options2(prof, p, Q, wk):
                if q['h1'] <= q['h0'] + 1e-6:
                    continue
                vq = piece_volume(q)
                if best is None or vq > best[2]:
                    best = (name, q, vq)
            if best is None:
                P[i] = None
                rep['removed_pieces'] += 1
                continue
            rep['options'][best[0]] = rep['options'].get(best[0], 0) + 1
            P[i] = best[1]
            P[i]['_removed_cm3'] = p.get('_removed_cm3', 0.0) + (v0 - best[2]) * 1e6
            nxt.append(i)
        todo = nxt
        if not todo:
            break
    rep['unresolved_after_rounds'] = len(todo)
    out = dict(lay, pieces=[p for p in P if p is not None])
    out['n_r'] = len(out['pieces'])
    walls = [piece_wall_min(p) for p in out['pieces'] if p['kind'] == 'wall']
    out['min_wall_mm'] = min(walls) * 1e3 if walls else None
    out['ring_cm3'] = sum(piece_volume(p) for p in out['pieces']) * 1e6
    return out, rep


def carved_heights(prof, lay, K):
    """{wall run: [h_lo, h_hi]} heights of the K fragments inside the wall pieces (for the forced band edges)."""
    KH = Hulls(K)
    KP = [hull_parts(V) for V in KH.V]
    out = {}
    for p in lay['pieces']:
        if p['kind'] != 'wall':
            continue
        V = piece_verts(prof, p)
        PP = hull_parts(V)
        lo, hi = V.min(0), V.max(0)
        cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0] if len(KH) else []
        for j in cand:
            Q = intersect_points(KP[j], PP)
            if Q is None:
                continue
            h = (Q - prof.c) @ prof.a
            a0, a1 = out.get(p['run'], (np.inf, -np.inf))
            out[p['run']] = (min(a0, float(h.min())), max(a1, float(h.max())))
    lv = prof.levels
    snap = {}
    for r, (a0, a1) in out.items():
        lo_ = lv[lv <= a0 + 1e-9]; hi_ = lv[lv >= a1 - 1e-9]
        snap[r] = [float(lo_.max()) if len(lo_) else a0, float(hi_.min()) if len(hi_) else a1]
    return snap


# ------------------------------------------------------------------------------------------------ route 3 (rev 2)
def route3_r2(body, ev, cap, k_inside=None):
    """F-I5.15 (2): CoACD with max_convex_hull = floor(cap / 2), then the keep-out repair up to the cap."""
    t = __import__('time').time()
    ask = max(int(math.floor(cap * C2['coacd_share'][0])), 1)
    hl = coacd(body, ask)
    pts = body_points(body)
    out, rep = repair(hl, pts, body, ev, cap, k_inside=k_inside)
    rep.update(coacd_asked=ask, coacd_pieces=len(hl), sec=round(__import__('time').time() - t, 1))
    return out, rep


def route_pieces2(body, ev, cap, lathe_axis=None, lathe_ok=False, plate_like=False, plate_hulls=None, sigma=None,
                  k_inside=None, skip=(), log=None, sectors=None, phase=0.0):
    """The F-I5.15 ladder for one (default) body: 1 plate, 2 the smallest cavity-safe ring layout (F-I5.16 (2)),
    3 CoACD floor(cap / 2) + repair, 4 voxel boxes. Returns dict(route, hulls, gate, tried, lathe=(prof, layout))."""
    tried = []
    log = log or (lambda *a: None)
    if plate_hulls is not None:
        g = gate(plate_hulls, body, ev, k_inside)
        tried.append(dict(route='1_plate', gate=g))
        if g['pass_']:
            return dict(route='1_plate', hulls=plate_hulls, gate=g, tried=tried, lathe=None)
    if lathe_ok and not plate_like and lathe_axis is not None and '2' not in skip:
        t = __import__('time').time()
        prof = Profile2(body, lathe_axis[0], lathe_axis[1], sigma, phase=phase)
        acc, rep = search_layout(prof, body, ev, cap, k_inside=k_inside, sectors=sectors, log=log)
        rep['sec'] = round(__import__('time').time() - t, 1)
        row = dict(route='2_lathe', report=rep)
        tried.append(row)
        if acc is not None:
            row['gate'] = acc['gate']
            return dict(route='2_lathe', hulls=acc['hulls'], gate=acc['gate'], tried=tried, lathe=(prof, acc['layout']),
                        n_handle=len(acc['handle_hulls']), handle_hulls=acc['handle_hulls'], share=acc['share'])
        log('route 2 (rev 2) failed', rep.get('why'))
    elif lathe_ok and plate_like:
        tried.append(dict(route='2_lathe', skipped='plate-like (F-I5.4: a flat plate passes rotc alone)'))
    if '3' not in skip:
        try:
            hl, rep = route3_r2(body, ev, cap, k_inside=k_inside)
            g = gate(hl, body, ev, k_inside)
            tried.append(dict(route='3_coacd', report=rep, gate=g))
            if g['pass_'] and len(hl) <= cap:
                return dict(route='3_coacd', hulls=hl, gate=g, tried=tried, lathe=None)
        except Exception as e:                                      # noqa: BLE001
            tried.append(dict(route='3_coacd', error=f'{type(e).__name__}: {e}'))
    hl, rep = voxel_boxes(body, ev, cap, k_inside=k_inside)
    if hl is None:
        tried.append(dict(route='4_voxels', report=rep))
        return dict(route=None, hulls=None, gate=None, tried=tried, lathe=None, why='no compliant pieces')
    g = gate(hl, body, ev, k_inside)
    tried.append(dict(route='4_voxels', report=rep, gate=g))
    return dict(route='4_voxels', hulls=hl, gate=g, tried=tried, lathe=None)


def faithful_boxes(body, pitch=None):
    """F-I5.15 (3): the SHELL's 2 mm cells (centre inside) merged into maximal boxes, no cap. Returns (boxes as 8-vertex
    arrays, occupancy dict(lo, pitch, occ))."""
    from gmg.interlock import fast_inside
    pitch = pitch or k_('pitch_m')
    lo, hi = body.bounds
    lo = lo - pitch; hi = hi + pitch
    G, n = grid_points(lo, hi, pitch)
    occ = fast_inside(body, G).reshape(n)
    out = []
    for i, j, k, x1, y1, z1 in _boxes(occ):
        a = lo + np.array([i, j, k]) * pitch
        b = lo + (np.array([x1, y1, z1]) + 1) * pitch
        out.append(np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])]))
    return out, dict(lo=lo, pitch=pitch, occ=occ, n=n)
