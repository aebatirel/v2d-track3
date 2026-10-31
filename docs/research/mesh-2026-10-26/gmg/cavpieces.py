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
    def band_edges(self, b0, b1, carved=None):
        """Bin-edge indices of the bands of the run b0..b1: <= 30 mm, <= 10 mm inside the carved height range
        (carved = (h_lo, h_hi) or None) with edges at the bin edges just outside the carve."""
        e = list(range(b0, b1 + 2))
        H = self.he
        band, bc = k_('band_m'), k_('band_carved_m')
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

    def pieces(self, n_s=None, carved=None, ring_gap_m=0.0):
        """Default piece dicts. carved: {sector: (h_lo, h_hi)} wall ranges to re-band at <= 10 mm. ring_gap_m (test
        x9 only): the lowest wall band of every sector starts this far above the base top (the ev10 defect)."""
        n_s = n_s or k_('n_sectors')
        out = []
        th = 2 * math.pi / n_s
        runs = self.runs()
        for kind, b0, b1 in runs:
            for s in range(n_s if kind == 'wall' else 1):
                edges = self.band_edges(b0, b1, (carved or {}).get(s) if kind == 'wall' else None)
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
                eqp = unique_planes(hull_eq(V))
                lo, hi = V.min(0), V.max(0)
                cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0]
                Qs = []
                for j in cand:
                    Q = clip_vertices(KH.V[j], eqp)
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
        al = allow if isinstance(allow, (list, tuple)) else [allow] * len(K)
        out = {}
        for p in pieces:
            if p['kind'] != 'wall':
                continue
            V = self.verts(p)
            eqp = unique_planes(hull_eq(V))
            lo, hi = V.min(0), V.max(0)
            cand = np.nonzero(np.all((KH.lo <= hi + 1e-9) & (KH.hi >= lo - 1e-9), axis=1))[0]
            for j in cand:
                Q = clip_vertices(KH.V[j], eqp)
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
def coacd(body, cap):
    import coacd as _c
    parts = _c.run_coacd(_c.Mesh(np.asarray(body.vertices, np.float64), np.asarray(body.faces, np.int64)),
                         threshold=k_('coacd_thr'), max_convex_hull=int(cap), preprocess_mode='auto')
    return [np.asarray(v, np.float64) for v, f in parts if len(v) >= 4]


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
