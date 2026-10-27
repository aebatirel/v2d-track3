#!/usr/bin/env python
"""Family A primitive assembly: white_pot and white_pot_lid fitted to OUR observed stereo points (obs_points.py).

Pre-registered round 2026-10-27 (docs/work-log.md). No ground truth: this code never reads the scans, *_align.npz,
mocap or parquet poses; its only input is one obs_points.py npz (pts, cam, frame) in the object (track) frame.

white_pot     = thin-walled lathe body with a CLOSED floor + flat bar handle + marker balls.
  Axis: lathe_obs.fit_axis (line complex + PCA + opening candidates, rotational self-consistency, opening rule).
  Profile: polar parameterization of the (r, h) half-plane about an interior point O = (0, h_O). Each point is
  OUTER-seen or INNER-seen by the sign of its view direction along the polar ray (in the (r, h) plane); per
  (polar-angle bin, azimuth sector) the median polar radius, then the median over >= MINSEC sectors (a handle or a
  marker fills 1-3 of 24 sectors and drops out). Wall thickness t = median distance between the outer and inner
  curves where both were seen. Mid-surface = outer - t/2 and inner + t/2 (along the curve normals); the shell is
  mid +- t/2, so the never-seen underside of the floor is the observed inner floor offset by t (closed floor), and a
  rounded bottom corner is followed instead of being filled. The rim is capped at the robust rim height.
  Handle: the largest residual cluster that reaches far from the axis; PCA long axis, top plane by a trimmed fit to
  top-seen points, width = 3..97 % lateral extent (median over length bins), thickness from side-seen points
  (2 x median depth below the top plane), bar from inside the wall to the 99.5 % tip, rounded tip (semicircle of the
  bar's half width). Hole: a closed gap in the top-surface occupancy grid (2 mm, after a 1-cell closing) near the
  tip, cut as a circle of the gap's area, only if the gap exists.
white_pot_lid = thin domed sheet + handle strap (arch) + marker balls on stems.
  Axis: smallest PCA direction (disc normal), up = towards the cameras (the underside is never seen); centre by a
  circle fit to the per-sector outer edge. Top surface h(r): per (radius bin, sector) median, median over sectors,
  two passes (points > SURF_D above the first-pass surface are residual: arch, markers); near the axis, under the
  arch, h(r) is extended by a quadratic dome fitted on r in [RC0, RC1]. Underside = top - t_lid (prior, never
  observed). Arch: largest residual cluster, PCA long axis in the disc plane; per 3 mm bin along it the top height
  (75th pct of top-seen points) and lateral centre; the strap (width W from the lateral extent, thickness T from
  side-seen points or prior) is swept along the smoothed top curve offset by T/2, ends pushed into the sheet.
Marker balls (both): compact residual clusters (bbox diagonal <= 40 mm, >= MK_MIN points) not explained by the
  other parts; sphere fit (free radius kept only if 5-9.5 mm and well supported, else the 7 mm prior from our own
  stereo); a stem cylinder from the ball to the body surface only if >= STEM_MIN points lie in the gap.
All parts are unioned with manifold3d into one watertight mesh (no hidden internal faces enter the scorer's area
sampling).

Variants (at most 4 for the family; parameters shared by pot and lid and across episodes):
  fit    : body + fitted parts (handle bar / arch) + marker spheres (+ stems where supported)
  nostem : as fit, markers as bare spheres (no stems)
  tsdf   : fitted body + the library_v3 TSDF mesh's faces lying outside the body by > 4 mm (handle, markers):
           the earlier "body + TSDF handle" construction, with the new body (the library mesh is our own TSDF)
  thick  : as fit, but body wall / sheet thickness doubled (sensitivity of the registration scale to thickness)
Usage: prim_potlid.py {pot,lid} OBS.npz OUT.glb [--variant fit] [--lib LIB.glb]
"""
import argparse, json, math, os, sys
import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lathe_obs as L                                     # noqa: E402
import manifold3d as mf                                   # noqa: E402

VOX = 0.0015          # voxel downsample of the observed points (m)
NSEC = 24             # azimuth sectors
MINSEC = 6            # sectors needed for a profile bin to belong to the body of revolution
MIN_PTS = 8           # points per (bin, sector) cell
DPHI = math.radians(2.0)
APP_D = 0.008         # residual: farther than this outside the body (stereo noise reaches 5-10 mm)
CL_VOX = 0.003        # residual clustering voxel
MK_MIN = 60           # points for a marker cluster
MK_DIAG = (0.006, 0.035)   # marker cluster 3..97 % bbox diagonal
MK_RES = 0.002        # sphere-fit median residual
MK_GAP = (-0.003, 0.020)   # ball surface to body/handle surface
MK_R0 = 0.007         # marker-ball radius prior (our own stereo, measured earlier)
MK_RMIN, MK_RMAX = 0.005, 0.0095
STEM_MIN = 15         # points in the ball-to-surface gap that support a stem
STEM_R = 0.0035       # stem radius
T_MIN, T_MAX = 0.002, 0.006
T_LID = 0.0025        # lid sheet thickness prior (task brief: ~2-3 mm)
BAR_T0 = 0.005        # handle / strap thickness prior when no side evidence
NSEG = 64             # revolve segments


# ------------------------------------------------------------------------------------------------ utilities
def load_obs(path, vox=VOX):
    Z = np.load(path)
    P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    key = np.floor(P / vox).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    return P[first], C[first]


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def to_mf(m):
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                            tri_verts=np.asarray(m.faces, np.uint32)))
    if M.status() != mf.Error.NoError or M.is_empty():
        raise RuntimeError(f'manifold conversion failed: {M.status()}')
    return M


def from_mf(M):
    mm = M.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3].astype(np.float64), np.asarray(mm.tri_verts),
                           process=True)


def frame_T(R, t):
    """3x4 affine (manifold3d) from a rotation (columns = local axes in the object frame) and a translation."""
    return np.c_[R, t].astype(np.float64)


def mf_cylinder(a, b, r, seg=20):
    a, b = np.asarray(a, float), np.asarray(b, float)
    L_ = float(np.linalg.norm(b - a))
    z = (b - a) / L_
    e1, e2, _ = L.frame_from(z)
    return mf.Manifold.cylinder(L_, r, r, seg).transform(frame_T(np.stack([e1, e2, z], 1), a))


def mf_sphere(c, r, seg=24):
    return mf.Manifold.sphere(float(r), seg).translate(tuple(map(float, c)))


def binned_sector_median(x, val, th, sel, x0, dx, nb, nsec=NSEC, min_pts=MIN_PTS, minsec=MINSEC, q=50):
    """Per (x bin, azimuth sector) q-th percentile of val; then the median over sectors where >= minsec sectors
    have >= min_pts points. Returns (nb,) with NaN elsewhere, and the per-bin sector counts."""
    xb = np.floor((x - x0) / dx).astype(int)
    ok = sel & (xb >= 0) & (xb < nb)
    sb = ((th + np.pi) / (2 * np.pi) * nsec).astype(int) % nsec
    out = np.full((nb, nsec), np.nan)
    key = xb[ok] * nsec + sb[ok]; vv = val[ok]
    order = np.argsort(key, kind='stable'); key, vv = key[order], vv[order]
    u, start, cnt = np.unique(key, return_index=True, return_counts=True)
    for k, s0, n in zip(u, start, cnt):
        if n >= min_pts:
            out[k // nsec, k % nsec] = np.percentile(vv[s0:s0 + n], q)
    ns = np.isfinite(out).sum(1)
    med = np.full(nb, np.nan)
    good = ns >= minsec
    if good.any():
        med[good] = np.nanmedian(out[good], 1)
    return med, ns


def fill_smooth(y, med=5, avg=3):
    x = np.arange(len(y)); ok = np.isfinite(y)
    if ok.sum() == 0:
        return y
    z = y.copy(); z[~ok] = np.interp(x[~ok], x[ok], y[ok])
    z = ndimage.median_filter(z, size=med, mode='nearest')
    return ndimage.uniform_filter1d(z, avg, mode='nearest')


def curve_normals(Q):
    """Outward normals of an ordered 2-D polyline (r, h) running from the axis bottom round to the rim:
    tangent rotated by -90 deg."""
    T = np.gradient(Q, axis=0); T = unit(T)
    return np.stack([T[:, 1], -T[:, 0]], 1)


def resample(Q, ds):
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    n = max(int(round(s[-1] / ds)), 2)
    si = np.linspace(0, s[-1], n + 1)
    return np.stack([np.interp(si, s, Q[:, 0]), np.interp(si, s, Q[:, 1])], 1)


def poly_dist(Q, X, step=0.0005):
    """Distance from 2-D points X to the polyline Q (densely sampled)."""
    pts = [Q[:1]]
    for a, b in zip(Q[:-1], Q[1:]):
        n = max(int(np.linalg.norm(b - a) / step), 1)
        pts.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
    S = np.concatenate(pts)
    return cKDTree(S).query(X)[0]


def revolve_to_object(prof, c, e1, e2, d, nseg=NSEG):
    mesh = L.revolve(prof, nseg=nseg)
    R = np.stack([e1, e2, d], 1)
    mesh.apply_transform(np.r_[np.c_[R, c], [[0, 0, 0, 1]]])
    return mesh


def clusters(A, vox=CL_VOX, min_pts=MK_MIN):
    """Voxel-connectivity clusters of 3-D points: list of index arrays (>= min_pts), largest first."""
    if len(A) == 0:
        return []
    lo = A.min(0) - 2 * vox
    idx = np.floor((A - lo) / vox).astype(int)
    shp = idx.max(0) + 3
    occ = np.zeros(shp, bool); occ[tuple(idx.T)] = True
    occ = ndimage.binary_dilation(occ, iterations=1)
    lab, nl = ndimage.label(occ, structure=np.ones((3, 3, 3)))
    pl = lab[tuple(idx.T)]
    out = [np.nonzero(pl == q)[0] for q in range(1, nl + 1)]
    out = [o for o in out if len(o) >= min_pts]
    return sorted(out, key=len, reverse=True)


# ------------------------------------------------------------------------------------------------ markers
def fit_sphere(Q, V, force_prior=False):
    """Marker ball from its observed cap. Q points, V unit view directions (point -> camera).
    Free algebraic + geometric fit; kept only if the radius is plausible and the cap is not too flat; otherwise a
    fixed-radius (MK_R0) fit started behind the cap (away from the cameras)."""
    info = dict(n=int(len(Q)))
    A = np.c_[2 * Q, np.ones(len(Q))]; b = (Q ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c = sol[:3]; r2 = sol[3] + c @ c
    free_ok = False
    if r2 > 0:
        r = math.sqrt(r2)
        for _ in range(10):                                       # Gauss-Newton on |q - c| - r
            D = Q - c; dn = np.linalg.norm(D, axis=1); J = np.c_[-D / dn[:, None], -np.ones(len(Q))]
            res = dn - r
            step = np.linalg.lstsq(J, -res, rcond=None)[0]
            c = c + step[:3]; r = r + step[3]
        res = np.abs(np.linalg.norm(Q - c, axis=1) - r)
        # angular support of the cap as seen from the fitted centre
        dirs = unit(Q - c); spread = 1 - np.linalg.norm(dirs.mean(0))
        info.update(free_r_mm=round(r * 1e3, 2), free_res_mm=round(float(np.median(res)) * 1e3, 2),
                    spread=round(float(spread), 3))
        free_ok = MK_RMIN <= r <= MK_RMAX and np.median(res) < 0.0012 and spread > 0.08
    if free_ok and not force_prior:
        info['mode'] = 'free'
        return c, r, info
    r = MK_R0
    c = Q.mean(0) - r * unit(V.mean(0))
    for _ in range(15):
        D = Q - c; dn = np.linalg.norm(D, axis=1); J = -D / dn[:, None]
        step = np.linalg.lstsq(J, -(dn - r), rcond=None)[0]
        c = c + step
    info['mode'] = 'prior'
    return c, r, info


def markers_from(Rp, Rv, Rz, Pall, surf_tm, variant):
    """Spheres (+ supported stems) for compact residual clusters. Rp/Rv residual points and unit view directions,
    Pall all observed points (stem evidence), surf_tm the body (+ handle) surface. Acceptance (GT-free): >= MK_MIN
    points, 3..97 % bbox diagonal MK_DIAG, sphere-fit median residual < MK_RES, ball surface within MK_GAP of the
    body/handle surface (markers sit on short stems). Returns manifold parts and an info list (rejections too)."""
    parts, infos = [], []
    if len(Rp) < MK_MIN:
        return parts, infos
    pq = trimesh.proximity.ProximityQuery(surf_tm)
    tree = cKDTree(Pall)
    queue = [(idx, 0) for idx in clusters(Rp)]
    while queue:
        idx, level = queue.pop(0)
        Q, V = Rp[idx], Rv[idx]
        diag = float(np.linalg.norm(np.percentile(Q, 97, 0) - np.percentile(Q, 3, 0)))
        if not MK_DIAG[0] <= diag <= MK_DIAG[1]:
            infos.append(dict(n=int(len(idx)), rejected='size', diag_mm=round(diag * 1e3, 1), level=level))
            if diag > MK_DIAG[1] and level == 0:
                # a marker merged with a noise band or a rim: re-cluster the points standing higher above the body
                hi = idx[Rz[idx] > APP_D + 0.004]
                queue += [(hi[j], 1) for j in clusters(Rp[hi])] if len(hi) >= MK_MIN else []
            continue
        c, r, info = fit_sphere(Q, V)
        res = float(np.median(np.abs(np.linalg.norm(Q - c, axis=1) - r)))
        sp, sd, _ = pq.on_surface(c[None])
        dist = float(sd[0]); gap = dist - r
        if info['mode'] == 'free' and not MK_GAP[0] <= gap <= MK_GAP[1]:      # free radius implausible here
            c, r, info2 = fit_sphere(Q, V, force_prior=True); info.update(info2)
            res = float(np.median(np.abs(np.linalg.norm(Q - c, axis=1) - r)))
            sp, sd, _ = pq.on_surface(c[None]); dist = float(sd[0]); gap = dist - r
        info.update(centre=[round(float(x), 4) for x in c], r_mm=round(r * 1e3, 2), gap_mm=round(gap * 1e3, 1),
                    diag_mm=round(diag * 1e3, 1), res_mm=round(res * 1e3, 2))
        if res > MK_RES or not MK_GAP[0] <= gap <= MK_GAP[1]:
            info['rejected'] = 'fit' if res > MK_RES else 'gap'
            infos.append(info)
            continue
        parts.append(mf_sphere(c, r))
        if variant != 'nostem' and gap > 0.003:
            b = sp[0]; ax = unit(b - c); L_ = float(np.linalg.norm(b - c))
            def count(a0):
                X = Pall[tree.query_ball_point(0.5 * (a0 + a0 + ax * L_), 0.5 * L_ + 0.005)] - a0
                if len(X) == 0:
                    return 0
                tp = X @ ax; pp = np.linalg.norm(X - tp[:, None] * ax, axis=1)
                return int(np.sum((pp < STEM_R + 0.0015) & (tp > r + 0.0005) & (tp < L_ - 0.003)))
            n_stem = count(c)
            side = unit(np.cross(ax, L.frame_from(ax)[0]))
            n_ctl = max(count(c + 0.02 * side), count(c - 0.02 * side))
            info.update(stem_pts=n_stem, stem_ctl=n_ctl)
            if n_stem >= STEM_MIN and n_stem >= 2 * n_ctl:
                parts.append(mf_cylinder(c, b + 0.002 * ax, STEM_R))       # 2 mm into the surface
                info['stem'] = True
        infos.append(info)
    return parts, infos


# ------------------------------------------------------------------------------------------------ pot
def fib_hemisphere(n):
    i = np.arange(n) + 0.5
    z = i / n                                                     # upper hemisphere, uniform in z
    t = np.pi * (1 + 5 ** 0.5) * i
    rr = np.sqrt(1 - z * z)
    return np.stack([rr * np.cos(t), rr * np.sin(t), z], 1)


def pot_axis(P, C, info, n_dirs=600):
    """Axis of an open container from observed points (no GT). For a direction a the axis line is placed by the
    line-complex least squares (lathe_obs._place); the open end is the end with fewer points near the axis (a floor
    exists only at the closed end); score J = rim flatness (median absolute deviation over 24 sectors of the
    per-sector 98th-percentile height of points in the rim radius window [0.6 R, R + 20 mm], R = median radius) +
    rotational self-consistency (lathe_obs.rot_consistency), both in mm. Global search over a hemisphere of
    directions, then two finer local grids around the three best. fit_axis's candidates are scored too.
    (lathe_obs.fit_axis alone gave axes 5-36 deg apart on three episodes of the same pot; the rim term agreed.)"""
    rng = np.random.default_rng(0)
    sub = rng.choice(len(P), min(20000, len(P)), replace=False)
    Ps, Cs = P[sub], C[sub]
    c0 = Ps.mean(0); X = Ps - c0
    n, planar = L.normals(X, Cs - c0)
    nb = np.cross(X, n)
    small = rng.choice(len(Ps), min(6000, len(Ps)), replace=False)

    def J(a, Q):
        a = a / np.linalg.norm(a)
        abar = L._place(n, nb, planar, a)
        c = c0 + np.cross(a, abar)
        h, r, th, _ = L.cyl(Q, c, a)
        R = np.median(r); H_ = np.ptp(h)
        n_lo = np.sum((r < 0.4 * R) & (h < h.min() + 0.25 * H_)); n_hi = np.sum((r < 0.4 * R) & (h > h.max() - 0.25 * H_))
        if n_hi > n_lo:
            a = -a; h = -h; th = -th
        sec = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
        win = (r > 0.6 * R) & (r < R + 0.02)
        tops = [np.percentile(h[win & (sec == q)], 98) for q in range(NSEC) if np.sum(win & (sec == q)) >= 10]
        if len(tops) < NSEC // 2:
            return 1e9, a, c
        tops = np.array(tops); mad = float(np.median(np.abs(tops - np.median(tops))))
        return (mad + L.rot_consistency(Q, c, a)) * 1e3, a, c

    cands = [J(a, Ps[small]) + (a,) for a in fib_hemisphere(n_dirs)]
    cost0, cfa, dfa, _ = L.fit_axis(Ps, Cs)
    cands.append(J(dfa, Ps[small]) + (dfa,))
    cands.sort(key=lambda x: x[0])
    best = None
    for j0, _, _, a0 in cands[:3]:
        cur = (J(a0, Ps)[0], a0)
        for span, step in ((6.0, 2.0), (2.0, 0.7)):
            e1, e2, _ = L.frame_from(cur[1])
            for i in np.arange(-span, span + 1e-9, step):
                for k in np.arange(-span, span + 1e-9, step):
                    a = cur[1] + math.tan(math.radians(i)) * e1 + math.tan(math.radians(k)) * e2
                    jj = J(a, Ps)[0]
                    if jj < cur[0]:
                        cur = (jj, a / np.linalg.norm(a))
        if best is None or cur[0] < best[0]:
            best = cur
    jbest, a, c = J(best[1], Ps)
    info.update(axis_J_mm=round(jbest, 3), axis_fitaxis_deg=round(math.degrees(math.acos(min(1, abs(a @ dfa)))), 1))
    return c, a


def pot_body(P, C, info, thick=1.0, axis=None):
    if axis is None:
        c, d = pot_axis(P, C, info)
    else:
        c, d = np.asarray(axis['centre']), np.asarray(axis['axis'])
    cost = L.rot_consistency(P[np.random.default_rng(1).choice(len(P), min(20000, len(P)), replace=False)], c, d) * 1e3
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    v = unit(C - P)
    # open end: a container has surface near its axis only at the closed end (floor); the open end has none
    body0 = r < np.percentile(r, 60) + 0.02
    hlo, hhi = np.percentile(h[body0], [0.5, 99.5])
    Rb = np.percentile(r[body0], 90); H_ = hhi - hlo
    n_lo = int(np.sum((r < 0.4 * Rb) & (h < hlo + 0.25 * H_)))
    n_hi = int(np.sum((r < 0.4 * Rb) & (h > hhi - 0.25 * H_)))
    info['axial_pts_lo_hi'] = [n_lo, n_hi]
    if n_hi > n_lo:
        h, r, th, (e1, e2, d) = L.cyl(P, c, -d)
        hlo, hhi = -hhi, -hlo
    radial = np.stack([np.cos(th), np.sin(th)], 1)
    vr = (v @ e1) * radial[:, 0] + (v @ e2) * radial[:, 1]; vh = v @ d
    # polar parameterization about O = (0, hO)
    hO = hlo + 0.6 * (hhi - hlo)
    Y = h - hO; rho = np.hypot(r, Y); phi = np.arctan2(Y, r)
    ux, uy = r / np.maximum(rho, 1e-9), Y / np.maximum(rho, 1e-9)
    s = vr * ux + vh * uy
    outer, inner = s > 0.3, s < -0.3
    p0 = -np.pi / 2; nb = int(math.ceil((np.pi / 2 - p0) / DPHI))
    pc = p0 + (np.arange(nb) + 0.5) * DPHI
    ro, nso = binned_sector_median(phi, rho, th, outer, p0, DPHI, nb)
    ri, nsi = binned_sector_median(phi, rho, th, inner, p0, DPHI, nb)
    ro[ri >= ro] = np.nan
    have = np.isfinite(ro) | np.isfinite(ri)
    if have.sum() < 10:
        raise SystemExit('pot: too few profile bins')
    last = np.nonzero(have)[0].max()
    U = np.stack([np.cos(pc), np.sin(pc)], 1)
    # curves (filled for normals only)
    def curve(rr):
        z = fill_smooth(rr)
        return np.stack([z * U[:, 0], hO + z * U[:, 1]], 1)
    Qo, Qi = curve(ro), curve(ri)
    No, Ni = curve_normals(Qo), curve_normals(Qi)
    both = np.isfinite(ro) & np.isfinite(ri)
    if both.sum() >= 3:
        Xin = np.stack([ri[both] * U[both, 0], hO + ri[both] * U[both, 1]], 1)
        t = float(np.median(poly_dist(Qo[np.isfinite(ro)], Xin)))
    else:
        t = 0.004
    t_meas = t
    t = float(np.clip(t, T_MIN, T_MAX)) * thick
    # mid-surface polar radius per bin
    co = np.maximum(np.einsum('ij,ij->i', No, U), 0.3); ci = np.maximum(np.einsum('ij,ij->i', Ni, U), 0.3)
    mo = ro - 0.5 * t_meas / co; mi = ri + 0.5 * t_meas / ci
    mid = np.where(np.isfinite(mo) & np.isfinite(mi), 0.5 * (mo + mi), np.where(np.isfinite(mo), mo, mi))
    mid[last + 1:] = np.nan
    pcs, mids = pc[:last + 1], fill_smooth(mid[:last + 1])
    M = np.stack([mids * np.cos(pcs), hO + mids * np.sin(pcs)], 1)
    M = np.r_[[[0.0, hO - mids[0]]], M]                           # start exactly on the axis
    # rim height: per sector 99th pct of h of points within 8 mm of the mid curve, median over sectors
    dm = poly_dist(M, np.stack([r, h], 1))
    near = dm < 0.008
    tops = []
    sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    for q in range(NSEC):
        m = near & (sb == q) & (r > 0.5 * np.max(M[:, 0]))
        if m.sum() > 30:
            tops.append(np.percentile(h[m], 99))
    h_top = float(np.median(tops)) if tops else float(M[-1, 1])
    keep = M[:, 1] <= h_top
    j = np.nonzero(~keep)[0]
    if len(j) and j[0] > 0:                                       # cut at the first crossing of h_top
        a_, b_ = M[j[0] - 1], M[j[0]]
        f = (h_top - a_[1]) / (b_[1] - a_[1])
        M = np.r_[M[:j[0]], [a_ + f * (b_ - a_)]]
    else:                                                         # never reaches h_top: extend straight up
        M = np.r_[M, [[M[-1, 0], h_top]]]
    M = resample(M, 0.003)
    M[0, 0] = 0.0
    N = curve_normals(M); N[0] = [0, -1]
    Out = M + 0.5 * t * N; In = M - 0.5 * t * N
    Out[:, 0] = np.maximum(Out[:, 0], 1e-4); In[:, 0] = np.maximum(In[:, 0], 1e-4)
    Out[0, 0] = In[0, 0] = 0.0
    prof = [(0.0, float(Out[0, 1]))] + [tuple(map(float, q)) for q in Out[1:]] + \
           [tuple(map(float, q)) for q in In[:0:-1]] + [(0.0, float(In[0, 1]))]
    body = revolve_to_object(prof, c, e1, e2, d)
    # solid hull (outer curve + axis) for the residual test
    hull = np.r_[Out, [[0.0, Out[-1, 1]]]]
    info.update(axis_rotcons_mm=round(cost, 3), axis=[round(float(x), 4) for x in d], centre=[round(float(x), 4) for x in c],
                t_meas_mm=round(t_meas * 1e3, 2), t_mm=round(t * 1e3, 2), h_top_mm=round((h_top - hlo) * 1e3, 1),
                rmax_mm=round(float(Out[:, 0].max()) * 1e3, 1), bins_outer=int(np.isfinite(ro).sum()),
                bins_inner=int(np.isfinite(ri).sum()), bins_both=int(both.sum()))
    geo = dict(c=c, d=d, e1=e1, e2=e2, h=h, r=r, th=th, Out=Out, hull=hull, t=t, h_top=h_top, M=M)
    return body, geo


def residual_mask(geo, h, r, app_d=APP_D):
    from skimage.measure import points_in_poly
    X = np.stack([r, h], 1)
    inside = points_in_poly(X, geo['hull'])
    dist = poly_dist(geo['Out'], X)
    return (~inside) & (dist > app_d)


def bar_handle(Hp, Hv, geo, info):
    """Flat bar handle from its residual points (object frame). Returns a manifold and the bar frame."""
    c, d = geo['c'], geo['d']
    m0 = Hp.mean(0)
    w_, V = np.linalg.eigh(np.cov((Hp - m0).T))
    u = V[:, 2]
    rad = (m0 - c) - ((m0 - c) @ d) * d
    if u @ rad < 0:
        u = -u
    n = V[:, 0]
    if n @ d < 0:
        n = -n
    # top plane: trimmed least squares on top-seen points
    top = (Hv @ n) > 0.3
    T_ = Hp[top] if top.sum() > 50 else Hp
    for _ in range(4):
        mt = T_.mean(0); w2, V2 = np.linalg.eigh(np.cov((T_ - mt).T)); n2 = V2[:, 0]
        if n2 @ n < 0:
            n2 = -n2
        res = (T_ - mt) @ n2
        T_ = T_[np.abs(res - np.median(res)) < 2.5 * 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-4]
    n = n2; u = unit(u - (u @ n) * n); w = np.cross(n, u)
    p_top = mt
    s = (Hp - p_top) @ u; a = (Hp - p_top) @ w; b = (Hp - p_top) @ n
    # width and lateral centre per 5 mm bin
    W, A, S = [], [], []
    for s0 in np.arange(np.percentile(s, 1), np.percentile(s, 99), 0.005):
        mm = (s >= s0) & (s < s0 + 0.005)
        if mm.sum() >= 15:
            lo, hi = np.percentile(a[mm], [3, 97]); W.append(hi - lo); A.append(0.5 * (lo + hi)); S.append(s0 + 0.0025)
    W, A, S = np.array(W), np.array(A), np.array(S)
    width = float(np.median(W))
    k = np.polyfit(S, A, 1) if len(S) >= 4 else np.array([0.0, float(np.median(A))])
    # lateral centre line a = k0 * s + k1 -> rotate u within the plane so the bar is straight along u
    ang = math.atan(k[0]); u2 = unit(math.cos(ang) * u + math.sin(ang) * w); w2 = np.cross(n, u2)
    origin = p_top + k[1] * w
    s = (Hp - origin) @ u2; a = (Hp - origin) @ w2; b = (Hp - origin) @ n
    side = np.abs(Hv @ w2) > 0.5
    btop = float(np.median(b[top])) if top.sum() > 30 else 0.0
    if side.sum() > 50:
        T = float(np.clip(2 * np.median(btop - b[side]), 0.003, 0.008))
        t_src = 'side'
    else:
        T, t_src = BAR_T0, 'prior'
    s_tip = float(np.percentile(s, 99.5))
    # inner end: inside the wall (start where the bar's axis point is at radius rmax - 2 t)
    rmax = float(geo['Out'][:, 0].max())
    ss = np.linspace(np.percentile(s, 0.5) - 0.06, s_tip, 400)
    pts = origin + ss[:, None] * u2
    rr = np.linalg.norm((pts - c) - ((pts - c) @ d)[:, None] * d, axis=1)
    inside = rr < rmax - 2 * geo['t']
    s_in = float(ss[inside].max()) if inside.any() else float(ss[0])
    half = 0.5 * width
    L_ = s_tip - half - s_in
    cs = mf.CrossSection.square((L_, width)).translate((s_in, -half))
    cs = cs + mf.CrossSection.circle(half, 32).translate((s_tip - half, 0.0))
    # hole: closed gap of the top-surface occupancy near the tip
    hole = None
    tp = top & (s > s_in)
    if tp.sum() > 200:
        g = 0.002
        gi = np.floor((s[tp] - s_in) / g).astype(int); ga = np.floor((a[tp] + half) / g).astype(int)
        ok = (ga >= 0) & (ga < int(width / g) + 1)
        occ = np.zeros((gi.max() + 3, int(width / g) + 3), bool)
        occ[gi[ok] + 1, ga[ok] + 1] = True
        occ = ndimage.binary_closing(occ, iterations=1)
        holes = ndimage.binary_fill_holes(occ) & ~occ
        lab, nl = ndimage.label(holes)
        best = None
        for q in range(1, nl + 1):
            cells = np.argwhere(lab == q)
            area = len(cells) * g * g
            cs_ = (cells.mean(0) - 1 + 0.5) * g
            sc, ac = cs_[0] + s_in, cs_[1] - half
            if area >= 40e-6 and sc > s_tip - 0.06 and abs(ac) < 0.5 * half:
                if best is None or area > best[0]:
                    best = (area, sc, ac)
        if best is not None:
            rh = math.sqrt(best[0] / math.pi)
            hole = dict(s_mm=round((s_tip - best[1]) * 1e3, 1), a_mm=round(best[2] * 1e3, 1), d_mm=round(2 * rh * 1e3, 1))
            cs = cs - mf.CrossSection.circle(rh, 32).translate((best[1], best[2]))
    bar = cs.extrude(T)                                           # z in [0, T]
    R = np.stack([u2, w2, n], 1)
    bar = bar.transform(frame_T(R, origin + (btop - T) * n))
    info['handle'] = dict(n=int(len(Hp)), width_mm=round(width * 1e3, 1), T_mm=round(T * 1e3, 1), T_src=t_src,
                          length_mm=round((s_tip - s_in) * 1e3, 1), tilt_deg=round(math.degrees(math.asin(abs(n @ d))), 1),
                          hole=hole)
    # bar distance for the residual split (markers on the handle)
    frame = dict(origin=origin + (btop - T) * n, R=R, L=(s_in, s_tip), width=width, T=T)
    return bar, frame


def in_bar(X, fr, margin):
    Q = (X - fr['origin']) @ fr['R']
    return ((Q[:, 0] > fr['L'][0] - margin) & (Q[:, 0] < fr['L'][1] + margin) & (np.abs(Q[:, 1]) < 0.5 * fr['width'] + margin)
            & (Q[:, 2] > -margin) & (Q[:, 2] < fr['T'] + margin))


def build_pot(P, C, variant, lib=None, axis_cache=None):
    info = dict(object='white_pot', variant=variant, n_pts=int(len(P)))
    axis = json.load(open(axis_cache)) if axis_cache and os.path.exists(axis_cache) else None
    body, geo = pot_body(P, C, info, thick=2.0 if variant == 'thick' else 1.0, axis=axis)
    if axis_cache and axis is None:
        json.dump(dict(centre=geo['c'].tolist(), axis=geo['d'].tolist(), J_mm=info.get('axis_J_mm')), open(axis_cache, 'w'))
    parts = [to_mf(body)]
    res = residual_mask(geo, geo['h'], geo['r'])
    Rp, Rv = P[res], unit(C - P)[res]
    info['residual_pts'] = int(res.sum())
    if variant == 'tsdf':
        return tsdf_parts(body, geo, lib, info)
    cl = clusters(Rp, min_pts=200)
    # handle = the largest cluster reaching > 60 mm beyond the body
    rmax = float(geo['Out'][:, 0].max())
    hid = None
    for idx in cl:
        X = Rp[idx] - geo['c']; rr = np.linalg.norm(X - (X @ geo['d'])[:, None] * geo['d'], axis=1)
        if np.percentile(rr, 99) > rmax + 0.06:
            hid = idx; break
    if hid is None:
        info['handle'] = None
        frame = None
    else:
        bar, frame = bar_handle(Rp[hid], Rv[hid], geo, info)
        parts.append(bar)
    # markers: residual points not explained by the bar (its noise band = APP_D)
    keep = np.ones(len(Rp), bool)
    if frame is not None:
        keep &= ~in_bar(Rp, frame, APP_D)
    surf = union(parts)
    Rz = poly_dist(geo['Out'], np.stack([geo['r'][res], geo['h'][res]], 1))
    mk, minfo = markers_from(Rp[keep], Rv[keep], Rz[keep], P, surf, variant)
    parts += mk
    info['markers'] = minfo
    return union(parts), info


def tsdf_parts(body, geo, lib, info):
    """Body + faces of our library TSDF mesh lying outside the body by > MARGIN (hybrid.py rule)."""
    src = trimesh.load(lib, force='mesh')
    c, d, e1, e2 = geo['c'], geo['d'], geo['e1'], geo['e2']
    X = src.triangles_center - c; h = X @ d; r = np.linalg.norm(X - h[:, None] * d, axis=1)
    keep = residual_mask(geo, h, r)
    app = src.submesh([np.nonzero(keep)[0]], append=True)
    info['tsdf_faces'] = int(keep.sum())
    full = trimesh.util.concatenate([body, app])
    return full, info


def union(parts):
    U = mf.Manifold.batch_boolean(parts, mf.OpType.Add) if len(parts) > 1 else parts[0]
    return from_mf(U)


# ------------------------------------------------------------------------------------------------ lid
def lid_top_profile(r, h, th, sel, dr=0.002, rc=(0.015, 0.035)):
    nb = int(math.ceil((r[sel].max() + 1e-6) / dr))
    med, ns = binned_sector_median(r, h, th, sel, 0.0, dr, nb, minsec=MINSEC)
    rc_ = (np.arange(nb) + 0.5) * dr
    ok = np.isfinite(med)
    # dome near the axis (under the arch): quadratic h = a + b r^2 on r in rc
    m = ok & (rc_ >= rc[0]) & (rc_ <= rc[1])
    if m.sum() >= 4:
        k = np.polyfit(rc_[m] ** 2, med[m], 1)
        med = np.where(rc_ < rc[0], k[1] + k[0] * rc_ ** 2, med)
    return rc_, med, ns


def build_lid(P, C, variant, lib=None):
    info = dict(object='white_pot_lid', variant=variant, n_pts=int(len(P)))
    v = unit(C - P)
    m0 = P.mean(0)
    w_, V = np.linalg.eigh(np.cov((P - m0).T)); d = V[:, 0]
    if (v @ d).mean() < 0:
        d = -d
    # centre: circle fit to the per-sector outer edge (98th pct radius), iterated twice
    c = m0.copy()
    for _ in range(3):
        h, r, th, (e1, e2, d) = L.cyl(P, c, d)
        sb = ((th + np.pi) / (2 * np.pi) * 36).astype(int) % 36
        E = []
        for q in range(36):
            mm = sb == q
            if mm.sum() > 50:
                rq = np.percentile(r[mm], 98); sel = mm & (r > rq - 0.003)
                E.append(P[sel].mean(0))
        E = np.array(E) - c
        x, y = E @ e1, E @ e2
        A = np.c_[2 * x, 2 * y, np.ones(len(x))]; sol = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)[0]
        c = c + sol[0] * e1 + sol[1] * e2
    # re-fit the disc normal on the flange (r > 40 mm, near the median surface) and re-centre the height origin
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    fl = (r > 0.04) & (r < 0.08)
    hb = np.median(h[fl])
    fl &= np.abs(h - hb) < 0.006
    # plane normal of the flange annulus (rotationally symmetric -> its best-fit plane normal is the axis)
    Fp = P[fl]; mf_ = Fp.mean(0); w2, V2 = np.linalg.eigh(np.cov((Fp - mf_).T)); d2 = V2[:, 0]
    if d2 @ d < 0:
        d2 = -d2
    d = d2
    # tilt refinement (rotational consistency of a lathe disc): per (4 mm radius bin, sector) median height of the
    # surface points; least squares h_ij = h0_i + r_i (gx cos th_j + gy sin th_j); the residual slope (gx, gy) is an
    # axis tilt -> d <- unit(d - gx e1 - gy e2); three iterations
    for _ in range(3):
        h, r, th, (e1, e2, d) = L.cyl(P, c, d)
        rb = np.floor(r / 0.002).astype(int)
        med = ndimage.median(h, rb, np.arange(rb.max() + 1)) if len(h) else None
        med = np.asarray(med, float)
        surf0 = np.abs(h - med[rb]) < 0.004
        R_hi = np.percentile(r[surf0], 98) - 0.002
        sel = surf0 & (r > 0.02) & (r < R_hi)
        rbin = np.floor(r[sel] / 0.004).astype(int); sbin = ((th[sel] + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
        key = rbin * NSEC + sbin
        uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        mh = np.asarray(ndimage.median(h[sel], inv, np.arange(len(uk))), float)
        good = cnt >= MIN_PTS
        ri_ = (uk // NSEC)[good]; tj = ((uk % NSEC)[good] + 0.5) / NSEC * 2 * np.pi - np.pi; y_ = mh[good]
        ur, ir = np.unique(ri_, return_inverse=True)
        rr_ = (ri_ + 0.5) * 0.004
        A = np.zeros((len(y_), len(ur) + 2)); A[np.arange(len(y_)), ir] = 1
        A[:, -2] = rr_ * np.cos(tj); A[:, -1] = rr_ * np.sin(tj)
        sol = np.linalg.lstsq(A, y_, rcond=None)[0]
        gx, gy = sol[-2], sol[-1]
        d = unit(d - gx * e1 - gy * e2)
    info['tilt_last_deg'] = round(math.degrees(math.atan(math.hypot(gx, gy))), 3)
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    vh = v @ d
    # top surface, pass 1 on all points, pass 2 on points within SURF_D of pass 1
    rc_, top1, _ = lid_top_profile(r, h, th, np.ones(len(P), bool))
    t1 = np.interp(r, rc_, fill_smooth(top1, 3, 3))
    surf = np.abs(h - t1) < 0.004
    rc_, top2, ns = lid_top_profile(r, h, th, surf)
    ok = np.isfinite(top2)
    # edge: the outermost bin seen by >= MINSEC sectors
    last = np.nonzero(ok)[0].max()
    rc_, top = rc_[:last + 1], fill_smooth(top2[:last + 1], 3, 3)
    r_edge = float(np.median([np.percentile(r[surf & (((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC == q)], 99.5)
                              for q in range(NSEC) if (surf & (((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC == q)).sum() > 30]))
    r_edge = max(r_edge, float(rc_[-1]))
    tl = T_LID * (2.0 if variant == 'thick' else 1.0)
    Tp = np.stack([rc_, top], 1)
    Tp = np.r_[[[0.0, top[0]]], Tp, [[r_edge, top[-1]]]]
    Tp = resample(Tp, 0.003); Tp[0, 0] = 0.0
    # outward normal of the top surface = up (+h) for a curve running from the axis outward: rotate tangent +90
    Tg = unit(np.gradient(Tp, axis=0)); Nu = np.stack([-Tg[:, 1], Tg[:, 0]], 1); Nu[0] = [0, 1]
    Bt = Tp - tl * Nu
    Bt[:, 0] = np.maximum(Bt[:, 0], 0.0); Bt[0, 0] = 0.0
    # profile: bottom from axis outward, then top from the edge inward
    prof = [(0.0, float(Bt[0, 1]))] + [tuple(map(float, q)) for q in Bt[1:]] + \
           [tuple(map(float, q)) for q in Tp[:0:-1]] + [(0.0, float(Tp[0, 1]))]
    body = revolve_to_object(prof, c, e1, e2, d)
    info.update(axis=[round(float(x), 4) for x in d], centre=[round(float(x), 4) for x in c], t_mm=round(tl * 1e3, 2),
                r_edge_mm=round(r_edge * 1e3, 1), dome_mm=round(float(top[0] - top.min()) * 1e3, 1),
                prof_bins=int(ok.sum()))
    geo = dict(c=c, d=d, e1=e1, e2=e2, rc=Tp[:, 0], top=Tp[:, 1], r_edge=r_edge, t=tl)
    parts = [to_mf(body)]
    # residual: above the top surface by > APP_D (arch, markers); within the edge radius + 15 mm
    htop = np.interp(r, Tp[:, 0], Tp[:, 1])
    res = (h > htop + APP_D) & (r < r_edge + 0.015)
    if variant == 'tsdf':
        src = trimesh.load(lib, force='mesh')
        X = src.triangles_center - c; hh = X @ d; rr = np.linalg.norm(X - hh[:, None] * d, axis=1)
        keep = hh > np.interp(rr, Tp[:, 0], Tp[:, 1]) + APP_D
        app = src.submesh([np.nonzero(keep)[0]], append=True)
        info['tsdf_faces'] = int(keep.sum())
        return trimesh.util.concatenate([body, app]), info
    Rp, Rv = P[res], v[res]
    info['residual_pts'] = int(res.sum())
    cl = clusters(Rp, min_pts=100)
    arch, frame = None, None
    for idx in cl:
        X = Rp[idx]
        ext = np.ptp((X - c) @ e1), np.ptp((X - c) @ e2)
        if max(ext) > 0.05:
            arch, frame = arch_strap(Rp[idx], Rv[idx], geo, info)
            break
    if arch is not None:
        parts.append(arch)
    keep = np.ones(len(Rp), bool)
    if frame is not None:
        keep &= frame['dist'](Rp) > APP_D
    surf = union(parts)
    Rz = (h - htop)[res]
    mk, minfo = markers_from(Rp[keep], Rv[keep], Rz[keep], P, surf, variant)
    parts += mk
    info['markers'] = minfo
    return union(parts), info


def arch_strap(Ap, Av, geo, info):
    """Handle strap over the lid: top curve along the arch's long axis, swept rectangle (width W, thickness T)."""
    c, d = geo['c'], geo['d']
    X = Ap - c; hh = X @ d; Xp = X - hh[:, None] * d
    w_, V = np.linalg.eigh(np.cov(Xp.T)); u = V[:, 2]; u = unit(u - (u @ d) * d); w = np.cross(d, u)
    s = Xp @ u; a = Xp @ w
    top = (Av @ d) > 0.3
    side = np.abs(Av @ w) > 0.5
    ds = 0.003
    S, H, A, W = [], [], [], []
    for s0 in np.arange(np.percentile(s, 0.5), np.percentile(s, 99.5), ds):
        mm = (s >= s0) & (s < s0 + ds)
        mt = mm & top
        if mt.sum() >= 8:
            S.append(s0 + ds / 2); H.append(np.percentile(hh[mt], 75))
            lo, hi = np.percentile(a[mm], [3, 97]); A.append(0.5 * (lo + hi)); W.append(hi - lo)
    S, H, A, W = map(np.array, (S, H, A, W))
    width = float(np.clip(np.median(W), 0.008, 0.03))
    acen = float(np.median(A))
    # thickness from side-seen points of the high (flat) part: 2 x median depth below the local top
    Hs = np.interp(s, S, H)
    hi_part = hh > np.percentile(H, 50)
    sp = side & hi_part
    if sp.sum() > 30:
        T = float(np.clip(2 * np.median(Hs[sp] - hh[sp]), 0.003, 0.008)); t_src = 'side'
    else:
        T, t_src = BAR_T0, 'prior'
    Hsm = ndimage.median_filter(H, size=3, mode='nearest'); Hsm = ndimage.uniform_filter1d(Hsm, 3, mode='nearest')
    # ends: run the top curve down into the sheet (lid top surface at the end radius)
    def lid_h(sv):
        rr = np.abs(sv)   # approximate radius along the strap line through the centre region
        return np.interp(rr, geo['rc'], geo['top'])
    S2 = np.r_[S[0] - 0.004, S, S[-1] + 0.004]
    H2 = np.r_[lid_h(S[0] - 0.004) + T * 0.5, Hsm, lid_h(S[-1] + 0.004) + T * 0.5]
    curve = np.stack([S2, H2], 1)
    curve = resample(curve, 0.002)
    Tg = unit(np.gradient(curve, axis=0)); Nn = np.stack([-Tg[:, 1], Tg[:, 0]], 1)   # up-ish normal
    Nn[Nn[:, 1] < 0] *= -1
    mid = curve - 0.5 * T * Nn
    # sweep a rectangle: corners at mid +- T/2 * Nn (in the s-h plane) and +- W/2 along w
    verts = []
    for (sv, hv), nn in zip(mid, Nn):
        base = c + sv * u + acen * w + hv * d
        nv = nn[0] * u + nn[1] * d
        for da, dn in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            verts.append(base + da * width * w + dn * T * nv)
    verts = np.array(verts); n = len(mid); F = []
    for i in range(n - 1):
        for k in range(4):
            a0, a1 = 4 * i + k, 4 * i + (k + 1) % 4
            b0, b1 = a0 + 4, a1 + 4
            F += [[a0, a1, b1], [a0, b1, b0]]
    F += [[0, 2, 1], [0, 3, 2]]
    l0 = 4 * (n - 1); F += [[l0, l0 + 1, l0 + 2], [l0, l0 + 2, l0 + 3]]
    tm = trimesh.Trimesh(verts, np.array(F), process=True)
    tm.fix_normals()
    # manifold of the sweep (a self-intersecting sweep would be repaired by the union; check status)
    strap = to_mf(tm)
    info['arch'] = dict(n=int(len(Ap)), width_mm=round(width * 1e3, 1), T_mm=round(T * 1e3, 1), T_src=t_src,
                        span_mm=round(float(S[-1] - S[0]) * 1e3, 1), height_mm=round(float(Hsm.max()) * 1e3, 1))
    tree = cKDTree(np.r_[verts, tm.sample(4000)])
    return strap, dict(dist=lambda Y: tree.query(Y)[0])


# ------------------------------------------------------------------------------------------------ main
def main():
    p = argparse.ArgumentParser()
    p.add_argument('obj', choices=['pot', 'lid']); p.add_argument('obs'); p.add_argument('out')
    p.add_argument('--variant', default='fit', choices=['fit', 'nostem', 'tsdf', 'thick'])
    p.add_argument('--lib', default=None, help='library TSDF mesh (variant tsdf only)')
    p.add_argument('--axis_cache', default=None, help='pot: json with the fitted axis (written if missing, reused '
                   'by the other variants of the same episode; the axis does not depend on the variant)')
    a = p.parse_args()
    P, C = load_obs(a.obs)
    if a.obj == 'pot':
        mesh, info = build_pot(P, C, a.variant, a.lib, a.axis_cache)
    else:
        mesh, info = build_lid(P, C, a.variant, a.lib)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    mesh.export(a.out)
    info.update(out=a.out, obs=a.obs, faces=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                bodies=int(mesh.body_count))
    json.dump(info, open(a.out.rsplit('.', 1)[0] + '.json', 'w'), indent=1, default=float)
    print(json.dumps(info, default=float))


if __name__ == '__main__':
    main()
