"""Part library of the autokit part DSL: parametric parts fitted to OUR observed stereo points (obs_points.py).

GT-free by construction. Every fitter here sees only the observed points of one episode (pts, cam, frame and the
obs_points vote grids, through autokit.io_gt.load_obs), our own library mesh (tsdf_patch only) and the program's
unseen-thickness prior t (generic grid {1.5, 2.5, 4.0} mm). No scan, *_align file, mocap or parquet pose is read, no
number measured on a scan is used, and there are no object names or per-object constants in this file.

Scale. Every window that depends on the object's size is RELATIVE: w = max(floor, frac * s), s = robust RMS radius
of the object's observed points (Ctx.s). The default fractions are the hand kits' (scripts/prim_*.py, lathe_obs.py)
absolute windows divided by s of the episode each kit was developed on, so a program that uses the defaults
reproduces the hand kit there. Absolute numbers remain only for
  - the sensor: voxel downsample VOX, robust-loss scale F_SCALE, residual noise band APP_D (our stereo points lie a
    median 0.9-1.9 mm, p90 up to ~7 mm from the surface), view-class cosines;
  - the marker-ball hardware (BALL: radius prior 7 mm from our own stereo, size / gap / stem tests), which is the same
    on every object.

Part types (fit_<type>(ctx, idx, spec, done) -> Part). Each returns a manifold3d solid (or a mesh patch), its
parameters, the number of free parameters k, the list of parameters that ended on a bound (bounds_hit) and
diagnostics; resid(X) gives how far points X lie OUTSIDE the part (> band: not explained by it), reach(X) how far
they reach beyond its extent (used by the assignment rules in program.py).
  lathe               thin-wall body of revolution; method 'polar' (closed floor, mid-surface +- t/2;
                      prim_potlid.pot_axis/pot_body) or 'height' (open or closed floor; lathe_obs.py)
  sheet_of_revolution domed thin sheet seen from one side (prim_potlid.build_lid): edge circle, tilt, top profile,
                      underside = top - t (prior grid)
  plate               plate in its own fitted plane: outline 'bar' (straight bar with rounded tip, optional hole,
                      inner end inside the host's wall), 'occupancy' or 'rect' (prim_boards outline)
  plate_set           one 'occupancy' plate per large cluster of the assigned points
  tube_rrect          drafted, leaning rounded-rectangle tube in the program's support frame; wall 'thin' (thickness
                      t) or 'lip' (inner face inset s0 + s1 (top - h)); point classes by the side they were seen from
  strap               rectangle swept along a centreline fitted in the cluster's best plane (prim_potlid.arch_strap);
                      ends run down to the host surface
  cone_array          rows of tapered round pegs (shared template per row) on blobs of a horizontal slice
  rounded_box         box in the cluster's PCA frame, robust extents, rounded edges
  ball                marker balls (one shared detector: prim_potlid.markers_from) on optional stems
  tsdf_patch          faces of our library mesh lying outside the listed parts (hybrid.py / tsdf_parts)
  splat               voxel splat + marching cubes of each assigned cluster (lathe_obs appendages)
Usage: library only (see program.py and DSL.md).
"""
import json, math, os, sys
from dataclasses import dataclass, field

import numpy as np
import trimesh
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
import lathe_obs as L                                     # noqa: E402
import prim_potlid as PL                                  # noqa: E402
import prim_rack as PR                                    # noqa: E402
import prim_boards as PB                                  # noqa: E402
import manifold3d as mf                                   # noqa: E402

# ------------------------------------------------------------------------------------------------ sensor / hardware
VOX = 0.0015          # voxel downsample of the observed points (m), sensor
F_SCALE = 0.002       # robust (soft_l1) loss scale (m), stereo noise
APP_D = 0.008         # residual noise band: a point farther than this outside every part is unexplained (m)
VR = 0.25             # |in-plane view component| that decides outer- vs inner-seen (tube_rrect)
NSEC = 24             # azimuth sectors of the body-of-revolution statistics
MINSEC = 6            # sectors needed for a bin to belong to the body of revolution (handles fill 1-3)
MIN_PTS = 8           # points per (bin, sector) cell
NSEG = 64             # revolve segments
BALL = dict(r0=0.007, rmin=0.005, rmax=0.0095, diag=(0.006, 0.035), res=0.002, gap=(-0.003, 0.020),
            stem_r=0.0035, stem_min=15, min_pts=60, free_r=(0.004, 0.012), spread=0.05)
# Default windows are the hand kits' absolute windows divided by s of the development episode of each kit
# (rel(value, S_REF_x)); a program on another object gets them scaled by its own s. Programs may override any
# window by name (params: {name: fraction} or {name: {'frac': f, 'floor': m}} or {name: {'abs': m}}).
S_REF_POLAR = 0.09114     # hand kit A, lathe 'polar' + bar plate (prim_potlid.build_pot development episode)
S_REF_SHEET = 0.06373     # hand kit A', sheet + strap (prim_potlid.build_lid development episode)
S_REF_TUBE = 0.15564      # hand kit C, tubes + cones (prim_rack development episode)
S_REF_HEIGHT = 0.05681    # lathe_obs.py development episode (lathe 'height' + splat)


def rel(m, s_ref, floor=0.0):
    """Window default: absolute value m (metres) at the reference scale s_ref, as (fraction of s, floor)."""
    return (m / s_ref, floor)


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def robust_scale(P):
    """Robust RMS radius s of a point set about its coordinate-wise median (the 2 % farthest points dropped)."""
    c = np.median(P, 0)
    d = np.linalg.norm(P - c, axis=1)
    q = np.quantile(d, 0.98)
    return float(np.sqrt(np.mean(d[d <= q] ** 2))), c


class Ctx:
    """Per-object fitting context: voxel-downsampled points P, camera centres C, unit view directions V
    (point -> camera), frame ids F, robust scale s, unseen-thickness prior t, the obs_points arguments (table band)
    and its vote grids (obs), the optional library mesh path (tsdf_patch) and the program's support frame."""

    def __init__(self, obs, t=0.0025, lib=None, vox=VOX):
        P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
        F = np.asarray(obs['frame']) if 'frame' in obs else np.zeros(len(P), int)
        key = np.floor(P / vox).astype(np.int64)
        _, first = np.unique(key, axis=0, return_index=True)         # one point per voxel (voxel-key order)
        self.P, self.C, self.F = P[first], C[first], F[first]
        self.V = unit(self.C - self.P)
        self.s, self.c0 = robust_scale(self.P)
        self.t = float(t)
        self.lib = lib
        self.obs = obs
        args = {}
        if 'args' in obs:
            try:
                args = json.loads(str(obs['args']))
            except ValueError:
                args = {}
        self.table_band = float(args.get('table_band', 0.008))
        self.frame = None
        self._n = None

    def w(self, spec, name, default):
        """Window `name`: spec params may give {'frac': f} (relative), a bare number (relative fraction) or
        {'abs': m}; default is (frac, floor). Returns max(floor, frac * s) in metres."""
        frac, floor = default
        v = spec.get('params', {}).get(name)
        if isinstance(v, dict):
            if 'abs' in v:
                return float(v['abs'])
            frac = float(v.get('frac', frac)); floor = float(v.get('floor', floor))
        elif v is not None:
            frac = float(v)
        return float(max(floor, frac * self.s))

    def normals(self):
        if self._n is None:
            self._n = L.normals(self.P, self.C, k=24)
        return self._n


@dataclass
class Part:
    name: str
    type: str
    solid: object = None                    # manifold3d.Manifold (unioned) or None
    mesh: object = None                     # trimesh patch concatenated at the end (tsdf_patch, splat concat)
    cavity: object = None                   # manifold3d.Manifold subtracted after the union (tube_rrect)
    params: dict = field(default_factory=dict)
    k: int = 0
    bounds_hit: list = field(default_factory=list)
    diag: dict = field(default_factory=dict)
    geo: dict = field(default_factory=dict)
    resid: object = None                    # resid(X) -> (N,) distance outside the part (m)
    reach: object = None                    # reach(X) -> (N,) distance beyond the part's extent (m)
    idx: object = None                      # indices (into ctx.P) of the points assigned to the part


def P_(ctx, idx):
    return ctx.P[idx], ctx.C[idx], ctx.V[idx]


def to_mf(m):
    return PL.to_mf(m)


def from_mf(M):
    return PL.from_mf(M)


def mf_union(solids):
    solids = [s for s in solids if s is not None]
    if not solids:
        return None
    return mf.Manifold.batch_boolean(solids, mf.OpType.Add) if len(solids) > 1 else solids[0]


class Surf:
    """Sampled surface of a solid for distance queries: signed distance (> 0 outside, by the nearest sample's
    face normal), as prim_rack.build's residual test."""

    def __init__(self, tm, n=200000):
        S, fi = trimesh.sample.sample_surface(tm, n, seed=0)
        self.S, self.N, self.tree = S, tm.face_normals[fi], cKDTree(S)

    def signed(self, X):
        d, j = self.tree.query(X)
        out = np.einsum('ij,ij->i', X - self.S[j], self.N[j]) > 0
        return np.where(out, d, -d)


def generic_resid(solid):
    tm = from_mf(solid)
    sf = Surf(tm)
    return sf.signed


def bbox_reach(solid):
    tm = from_mf(solid)
    c = tm.bounding_box.centroid; R = 0.5 * np.linalg.norm(tm.extents)
    return lambda X: np.linalg.norm(X - c, axis=1) - R


def bound_flags(names, x, lo, hi, tol=1e-6):
    """Names of least-squares parameters that ended within tol (relative to the bound span) of a bound."""
    out = []
    for n, v, a, b in zip(names, x, lo, hi):
        span = (b - a) if np.isfinite(a) and np.isfinite(b) else max(abs(v), 1.0)
        if (np.isfinite(a) and v - a <= tol * span + 1e-9) or (np.isfinite(b) and b - v <= tol * span + 1e-9):
            out.append(n)
    return out


def clip_flag(name, v, lo, hi, hits):
    """np.clip with a bound-hit record."""
    if v <= lo:
        hits.append(name); return lo
    if v >= hi:
        hits.append(name); return hi
    return v


# ================================================================================================ lathe
def axis_search(ctx, P, C, spec, info, n_dirs=600):
    """prim_potlid.pot_axis with relative windows: line-complex placement per direction, score = rim flatness (MAD of
    the per-sector 98th-pct height in the rim window [0.6 R, R + rim_w]) + rotational self-consistency; hemisphere
    search, two local refinements around the three best; lathe_obs.fit_axis's direction is a candidate too."""
    rim_w = ctx.w(spec, 'rim_w', rel(0.020, S_REF_POLAR))
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
        win = (r > 0.6 * R) & (r < R + rim_w)
        tops = [np.percentile(h[win & (sec == q)], 98) for q in range(NSEC) if np.sum(win & (sec == q)) >= 10]
        if len(tops) < NSEC // 2:
            return 1e9, a, c
        tops = np.array(tops); mad = float(np.median(np.abs(tops - np.median(tops))))
        return (mad + L.rot_consistency(Q, c, a)) * 1e3, a, c

    cands = [J(a, Ps[small]) + (a,) for a in PL.fib_hemisphere(n_dirs)]
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


def lathe_polar(ctx, P, C, spec, info, hits):
    """prim_potlid.pot_body with relative windows. Polar (r, h) profile about an interior point; outer/inner by the
    view direction along the polar ray; median over >= MINSEC sectors; wall t measured where both sides were seen
    (else the prior ctx.t); mid-surface +- t/2 so the unseen floor underside = observed inner floor + t (closed)."""
    p = spec.get('params', {})
    body_w = ctx.w(spec, 'body_w', rel(0.020, S_REF_POLAR))
    tmin = ctx.w(spec, 't_min', rel(0.002, S_REF_POLAR, 0.0015)); tmax = ctx.w(spec, 't_max', rel(0.006, S_REF_POLAR, 0.003))
    near_w = ctx.w(spec, 'rim_near', rel(0.008, S_REF_POLAR))
    ds = ctx.w(spec, 'resample', rel(0.003, S_REF_POLAR, 0.001))
    dphi = math.radians(float(p.get('dphi_deg', 2.0)))
    c, d = axis_search(ctx, P, C, spec, info)
    cost = L.rot_consistency(P[np.random.default_rng(1).choice(len(P), min(20000, len(P)), replace=False)], c, d) * 1e3
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    v = unit(C - P)
    body0 = r < np.percentile(r, 60) + body_w
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
    hO = hlo + 0.6 * (hhi - hlo)
    Y = h - hO; rho = np.hypot(r, Y); phi = np.arctan2(Y, r)
    ux, uy = r / np.maximum(rho, 1e-9), Y / np.maximum(rho, 1e-9)
    s_ = vr * ux + vh * uy
    outer, inner = s_ > 0.3, s_ < -0.3
    p0 = -np.pi / 2; nb = int(math.ceil((np.pi / 2 - p0) / dphi))
    pc = p0 + (np.arange(nb) + 0.5) * dphi
    ro, _ = PL.binned_sector_median(phi, rho, th, outer, p0, dphi, nb)
    ri, _ = PL.binned_sector_median(phi, rho, th, inner, p0, dphi, nb)
    ro[ri >= ro] = np.nan
    have = np.isfinite(ro) | np.isfinite(ri)
    if have.sum() < 10:
        raise RuntimeError('lathe polar: too few profile bins')
    last = np.nonzero(have)[0].max()
    U = np.stack([np.cos(pc), np.sin(pc)], 1)

    def curve(rr):
        z = PL.fill_smooth(rr)
        return np.stack([z * U[:, 0], hO + z * U[:, 1]], 1)
    Qo, Qi = curve(ro), curve(ri)
    No, Ni = PL.curve_normals(Qo), PL.curve_normals(Qi)
    both = np.isfinite(ro) & np.isfinite(ri)
    if both.sum() >= 3:
        Xin = np.stack([ri[both] * U[both, 0], hO + ri[both] * U[both, 1]], 1)
        t = float(np.median(PL.poly_dist(Qo[np.isfinite(ro)], Xin))); t_src = 'two_sided'
    else:
        t = ctx.t; t_src = 'prior'
    t_meas = t
    t = clip_flag('t', t, tmin, tmax, hits) * float(p.get('thick', 1.0))
    co = np.maximum(np.einsum('ij,ij->i', No, U), 0.3); ci = np.maximum(np.einsum('ij,ij->i', Ni, U), 0.3)
    mo = ro - 0.5 * t_meas / co; mi = ri + 0.5 * t_meas / ci
    mid = np.where(np.isfinite(mo) & np.isfinite(mi), 0.5 * (mo + mi), np.where(np.isfinite(mo), mo, mi))
    mid[last + 1:] = np.nan
    pcs, mids = pc[:last + 1], PL.fill_smooth(mid[:last + 1])
    M = np.stack([mids * np.cos(pcs), hO + mids * np.sin(pcs)], 1)
    M = np.r_[[[0.0, hO - mids[0]]], M]
    dm = PL.poly_dist(M, np.stack([r, h], 1))
    near = dm < near_w
    tops = []
    sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    for q in range(NSEC):
        m = near & (sb == q) & (r > 0.5 * np.max(M[:, 0]))
        if m.sum() > 30:
            tops.append(np.percentile(h[m], 99))
    h_top = float(np.median(tops)) if tops else float(M[-1, 1])
    keep = M[:, 1] <= h_top
    j = np.nonzero(~keep)[0]
    if len(j) and j[0] > 0:
        a_, b_ = M[j[0] - 1], M[j[0]]
        f = (h_top - a_[1]) / (b_[1] - a_[1])
        M = np.r_[M[:j[0]], [a_ + f * (b_ - a_)]]
    else:
        M = np.r_[M, [[M[-1, 0], h_top]]]
    M = PL.resample(M, ds)
    M[0, 0] = 0.0
    N = PL.curve_normals(M); N[0] = [0, -1]
    Out = M + 0.5 * t * N; In = M - 0.5 * t * N
    Out[:, 0] = np.maximum(Out[:, 0], 1e-4); In[:, 0] = np.maximum(In[:, 0], 1e-4)
    Out[0, 0] = In[0, 0] = 0.0
    prof = [(0.0, float(Out[0, 1]))] + [tuple(map(float, q)) for q in Out[1:]] + \
           [tuple(map(float, q)) for q in In[:0:-1]] + [(0.0, float(In[0, 1]))]
    body = PL.revolve_to_object(prof, c, e1, e2, d)
    hull = np.r_[Out, [[0.0, Out[-1, 1]]]]
    info.update(axis_rotcons_mm=round(cost, 3), t_meas_mm=round(t_meas * 1e3, 2), t_mm=round(t * 1e3, 2), t_src=t_src,
                h_top_mm=round((h_top - hlo) * 1e3, 1), rmax_mm=round(float(Out[:, 0].max()) * 1e3, 1),
                bins_outer=int(np.isfinite(ro).sum()), bins_inner=int(np.isfinite(ri).sum()), bins_both=int(both.sum()))
    return body, dict(c=c, d=d, e1=e1, e2=e2, Out=Out, hull=hull, t=t, h_top=h_top, rmax=float(Out[:, 0].max()),
                      prof=np.asarray(prof)), 2 + 2 + 1 + int(len(M))


def lathe_height(ctx, P, C, spec, info, hits):
    """lathe_obs.py with relative windows: line-complex axis candidates scored by rotational self-consistency;
    per height bin the sector-median outer and inner radius (>= MINSEC sectors); open end = the end with inner-wall
    evidence; t = median (r_out - r_in) (two-sided), else the prior; floor 'base' (cavity down to base + t, an
    observed thin floor layer if present), 'observed' (only as deep as the inner wall was seen), 'solid' (no cavity) or 'open' (bottomless ring)."""
    p = spec.get('params', {})
    dh = ctx.w(spec, 'dh', rel(0.003, S_REF_HEIGHT, 0.001))
    tmin = ctx.w(spec, 't_min', rel(0.0015, S_REF_HEIGHT, 0.0015))
    body_m = ctx.w(spec, 'body_margin', rel(0.005, S_REF_HEIGHT))
    cap_m = ctx.w(spec, 'cap_margin', rel(0.003, S_REF_HEIGHT))
    layer = ctx.w(spec, 'floor_layer', rel(0.010, S_REF_HEIGHT))
    floor = p.get('floor', 'base')
    gap = int(p.get('gap_bins', 3))
    sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)
    cost, c, d, k = L.fit_axis(P[sub], C[sub], knn=24)
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    v = unit(C - P)
    radial = np.stack([np.cos(th), np.sin(th)], 1)
    vr = (v @ e1) * radial[:, 0] + (v @ e2) * radial[:, 1]
    outer, inner = vr > 0.3, vr < -0.3

    def sector_stat(sel):
        hb = np.floor((h - h.min()) / dh).astype(int); nbin = hb.max() + 1
        sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
        out = np.full((nbin, NSEC), np.nan)
        key = hb[sel] * NSEC + sb[sel]; rr = r[sel]
        order = np.argsort(key); key, rr = key[order], rr[order]
        u, start, cnt = np.unique(key, return_index=True, return_counts=True)
        for kk, s0, n in zip(u, start, cnt):
            if n >= MIN_PTS:
                out[kk // NSEC, kk % NSEC] = np.percentile(rr[s0:s0 + n], 50)
        return out
    Sout, Sin = sector_stat(outer), sector_stat(inner)
    h0 = h.min(); nbin = Sout.shape[0]
    nso = np.sum(np.isfinite(Sout), 1); nsi = np.sum(np.isfinite(Sin), 1)
    with np.errstate(all='ignore'):
        r_out = np.where(nso >= MINSEC, np.nanmedian(Sout, 1), np.nan)
        r_in = np.where(nsi >= MINSEC, np.nanmedian(Sin, 1), np.nan)
    hc = h0 + (np.arange(nbin) + 0.5) * dh
    vo = np.isfinite(r_out); vi = np.isfinite(r_in) & vo & (r_in < r_out)
    if vo.sum() < 5:
        raise RuntimeError('lathe height: too few outer-wall bins')
    body = r < np.nanmax(r_out) + body_m
    hlo, hhi = np.percentile(h[body], [0.5, 99.5])
    hi_in = hc[vi]
    open_top = (len(hi_in) > 0) and (np.mean(hi_in > 0.5 * (hlo + hhi)) >= 0.5)
    if not open_top:
        d = -d; h = -h; hlo, hhi = -hhi, -hlo
        r_out, r_in, vo, vi, hc = r_out[::-1], r_in[::-1], vo[::-1], vi[::-1], -hc[::-1]
        e2 = np.cross(d, e1)
    if vi.sum() >= 3:
        t = float(np.median((r_out - r_in)[vi])); t_src = 'two_sided'
    else:
        t = ctx.t; t_src = 'prior'
    if t < tmin:
        hits.append('t'); t = tmin
    sel = (hc >= hlo) & (hc <= hhi)
    hc, r_out, r_in, vo, vi = hc[sel], r_out[sel], r_in[sel], vo[sel], vi[sel]
    ro = L.smooth_fill(r_out, vo)
    ri = np.minimum(L.smooth_fill(np.where(vi, r_in, r_out - t), vi | vo), ro - tmin)
    solid = floor == 'solid'
    capin = (~outer) & (~inner) & (r < np.interp(h, hc, ri) - cap_m) & (h > hlo) & (h < hhi)
    hfloor = hlo + t
    low = capin & (h < hlo + 0.4 * (hhi - hlo))
    if low.sum() > 200 and not solid:
        q10, q50, q90 = np.percentile(h[low], [10, 50, 90])
        if q90 - q10 < layer:
            hfloor = max(float(q50), hlo + t)
    if floor == 'observed' and vi.any():
        idx = np.nonzero(vi)[0]; j = idx[-1]; g = 0
        for i in range(idx[-1], -1, -1):
            if vi[i]:
                j, g = i, 0
            else:
                g += 1
                if g > gap:
                    break
        hfloor = max(float(hc[j]) - dh, hlo + t)
    base, top = hlo, hhi
    prof = [(0.0, base), (float(ro[0]), base)]
    prof += [(float(ro[i]), float(hc[i])) for i in range(len(hc))]
    prof += [(float(ro[-1]), top)]
    if solid:
        prof += [(0.0, top)]
    else:
        keep = hc > hfloor
        prof += [(float(ri[-1]), top)]
        prof += [(float(ri[i]), float(hc[i])) for i in range(len(hc) - 1, -1, -1) if keep[i]]
        prof += [(float(ri[keep][0]) if keep.any() else float(ro[0] - t), hfloor), (0.0, hfloor)]
    R = np.stack([e1, np.cross(d, e1), d], 1)
    if floor == 'open':
        # bottomless ring: outer wall up, rim, inner wall down to the base (an annulus revolved about the axis)
        ring = [(float(ri[0]), base), (float(ro[0]), base)] + [(float(ro[i]), float(hc[i])) for i in range(len(hc))]
        ring += [(float(ro[-1]), top), (float(ri[-1]), top)] + [(float(ri[i]), float(hc[i])) for i in range(len(hc) - 1, -1, -1)]
        cs = mf.CrossSection([np.asarray(ring, np.float64)])
        if cs.area() < 0:
            cs = mf.CrossSection([np.asarray(ring[::-1], np.float64)])
        man = mf.Manifold.revolve(cs, int(p.get('nseg', 96))).transform(np.c_[R, c])
        mesh = from_mf(man)
        prof = ring
    else:
        mesh = L.revolve(prof, nseg=int(p.get('nseg', 96)))
        mesh.apply_transform(np.r_[np.c_[R, c], [[0, 0, 0, 1]]])
    Out = np.r_[[[float(ro[0]), base]], np.stack([ro, hc], 1), [[float(ro[-1]), top]]]     # outer curve (r, h)
    hull = np.r_[[[0.0, base]], Out, [[0.0, top]]]
    info.update(axis_rotcons_mm=round(cost, 3), axis_cands=int(k), t_mm=round(t * 1e3, 2), t_src=t_src,
                height_mm=round((top - base) * 1e3, 1), rmax_mm=round(float(ro.max() * 1e3), 1),
                open_top=bool(open_top), hfloor_mm=round((hfloor - base) * 1e3, 1), floor=floor)
    e1o = R[:, 0]; e2o = R[:, 1]
    return mesh, dict(c=c, d=d, e1=e1o, e2=e2o, Out=Out, hull=hull, t=t, h_top=top, base=base, rmax=float(ro.max()),
                      prof=np.asarray(prof), hc=hc, ro=ro), 2 + 2 + 1 + 2 * int(len(hc))


def revolve_resid(geo, mode='hull'):
    """(r, h) residual of a body of revolution: inside the solid hull (outer curve + axis) -> negative, else the
    distance to the outer curve."""
    from skimage.measure import points_in_poly
    c, d = geo['c'], geo['d']

    def f(X):
        Q = X - c; h = Q @ d; r = np.linalg.norm(Q - h[:, None] * d, axis=1)
        Y = np.stack([r, h], 1)
        inside = points_in_poly(Y, geo['hull'])
        dist = PL.poly_dist(geo['Out'], Y)
        return np.where(inside, -dist, dist)
    return f


def revolve_reach(geo):
    c, d, rmax = geo['c'], geo['d'], geo['rmax']

    def f(X):
        Q = X - c; h = Q @ d
        return np.linalg.norm(Q - h[:, None] * d, axis=1) - rmax
    return f


def fit_lathe(ctx, idx, spec, done):
    P, C, _ = P_(ctx, idx)
    info, hits = {}, []
    method = spec.get('params', {}).get('method', 'polar')
    if method == 'polar':
        body, geo, k = lathe_polar(ctx, P, C, spec, info, hits)
    else:
        body, geo, k = lathe_height(ctx, P, C, spec, info, hits)
    params = dict(method=method, centre=geo['c'].round(5).tolist(), axis=geo['d'].round(5).tolist(),
                  t_mm=round(geo['t'] * 1e3, 2), rmax_mm=round(geo['rmax'] * 1e3, 1))
    if method == 'polar':
        resid = revolve_resid(geo)
    else:
        hc, ro, base, top = geo['hc'], geo['ro'], geo['base'], geo['h_top']
        c, d = geo['c'], geo['d']

        def resid(X):                                  # lathe_obs: radial excess over the outer profile, or beyond the ends
            Q = X - c; hh = Q @ d; rr = np.linalg.norm(Q - hh[:, None] * d, axis=1)
            return np.maximum.reduce([rr - np.interp(hh, hc, ro), hh - top, base - hh])
    return Part(spec['name'], 'lathe', solid=to_mf(body), params=params, k=k, bounds_hit=hits, diag=info, geo=geo,
                resid=resid, reach=revolve_reach(geo))


# ================================================================================================ sheet of revolution
def fit_sheet_of_revolution(ctx, idx, spec, done):
    """prim_potlid.build_lid's sheet with relative windows. Disc normal = smallest PCA direction, oriented towards the
    cameras (the underside is never seen); centre by a circle fit to the per-sector outer edge (3 passes); normal
    refit on the flange annulus; tilt refinement (rotational consistency of the height field, 3 iterations); top
    profile h(r) = median over sectors of the per-(radius bin, sector) median, two passes (points off the first-pass
    surface are residual); near the axis (under an arch) a quadratic dome from the ring [rc0, rc1]; underside =
    top - t along the profile normal (t = the program's prior: the underside is never observed)."""
    P, C, v = P_(ctx, idx)
    p = spec.get('params', {})
    edge_w = ctx.w(spec, 'edge_w', rel(0.003, S_REF_SHEET))
    fl_r = (ctx.w(spec, 'flange_r0', rel(0.040, S_REF_SHEET)), ctx.w(spec, 'flange_r1', rel(0.080, S_REF_SHEET)))
    fl_h = ctx.w(spec, 'flange_h', rel(0.006, S_REF_SHEET))
    rb_w = ctx.w(spec, 'rbin', rel(0.002, S_REF_SHEET)); surf_w = ctx.w(spec, 'surf_band', rel(0.004, S_REF_SHEET))
    r_in = ctx.w(spec, 'tilt_rmin', rel(0.020, S_REF_SHEET)); tb_w = ctx.w(spec, 'tilt_rbin', rel(0.004, S_REF_SHEET))
    dr = ctx.w(spec, 'prof_dr', rel(0.002, S_REF_SHEET))
    rc = (ctx.w(spec, 'dome_r0', rel(0.015, S_REF_SHEET)), ctx.w(spec, 'dome_r1', rel(0.035, S_REF_SHEET)))
    ds = ctx.w(spec, 'resample', rel(0.003, S_REF_SHEET))
    t = ctx.t * float(p.get('thick', 1.0))
    info, hits = {}, []
    m0 = P.mean(0)
    w_, V = np.linalg.eigh(np.cov((P - m0).T)); d = V[:, 0]
    if (v @ d).mean() < 0:
        d = -d
    c = m0.copy()
    for _ in range(3):
        h, r, th, (e1, e2, d) = L.cyl(P, c, d)
        sb = ((th + np.pi) / (2 * np.pi) * 36).astype(int) % 36
        E = []
        for q in range(36):
            mm = sb == q
            if mm.sum() > 50:
                rq = np.percentile(r[mm], 98); sel = mm & (r > rq - edge_w)
                E.append(P[sel].mean(0))
        if len(E) < 6:
            raise RuntimeError(f'sheet_of_revolution: only {len(E)} of 36 sectors have > 50 points (edge circle)')
        E = np.array(E) - c
        x, y = E @ e1, E @ e2
        A = np.c_[2 * x, 2 * y, np.ones(len(x))]; sol = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)[0]
        c = c + sol[0] * e1 + sol[1] * e2
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    fl = (r > fl_r[0]) & (r < fl_r[1])
    if fl.sum() > 100:
        hb = np.median(h[fl])
        fl &= np.abs(h - hb) < fl_h
        Fp = P[fl]; mf_ = Fp.mean(0); w2, V2 = np.linalg.eigh(np.cov((Fp - mf_).T)); d2 = V2[:, 0]
        if d2 @ d < 0:
            d2 = -d2
        d = d2
    gx = gy = 0.0
    for _ in range(3):
        h, r, th, (e1, e2, d) = L.cyl(P, c, d)
        rb = np.floor(r / rb_w).astype(int)
        med = np.asarray(ndimage.median(h, rb, np.arange(rb.max() + 1)), float)
        surf0 = np.abs(h - med[rb]) < surf_w
        R_hi = np.percentile(r[surf0], 98) - rb_w
        sel = surf0 & (r > r_in) & (r < R_hi)
        rbin = np.floor(r[sel] / tb_w).astype(int); sbin = ((th[sel] + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
        key = rbin * NSEC + sbin
        uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        mh = np.asarray(ndimage.median(h[sel], inv, np.arange(len(uk))), float)
        good = cnt >= MIN_PTS
        ri_ = (uk // NSEC)[good]; tj = ((uk % NSEC)[good] + 0.5) / NSEC * 2 * np.pi - np.pi; y_ = mh[good]
        ur, ir = np.unique(ri_, return_inverse=True)
        rr_ = (ri_ + 0.5) * tb_w
        A = np.zeros((len(y_), len(ur) + 2)); A[np.arange(len(y_)), ir] = 1
        A[:, -2] = rr_ * np.cos(tj); A[:, -1] = rr_ * np.sin(tj)
        sol = np.linalg.lstsq(A, y_, rcond=None)[0]
        gx, gy = sol[-2], sol[-1]
        d = unit(d - gx * e1 - gy * e2)
    info['tilt_last_deg'] = round(math.degrees(math.atan(math.hypot(gx, gy))), 3)
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)

    def top_profile(sel):
        nb = int(math.ceil((r[sel].max() + 1e-6) / dr))
        med, ns = PL.binned_sector_median(r, h, th, sel, 0.0, dr, nb, minsec=MINSEC)
        rc_ = (np.arange(nb) + 0.5) * dr
        ok = np.isfinite(med)
        m = ok & (rc_ >= rc[0]) & (rc_ <= rc[1])
        if m.sum() >= 4:
            kk = np.polyfit(rc_[m] ** 2, med[m], 1)
            med = np.where(rc_ < rc[0], kk[1] + kk[0] * rc_ ** 2, med)
        return rc_, med, ns
    rc_, top1, _ = top_profile(np.ones(len(P), bool))
    t1 = np.interp(r, rc_, PL.fill_smooth(top1, 3, 3))
    surf = np.abs(h - t1) < surf_w
    rc_, top2, ns = top_profile(surf)
    ok = np.isfinite(top2)
    last = np.nonzero(ok)[0].max()
    rc_, top = rc_[:last + 1], PL.fill_smooth(top2[:last + 1], 3, 3)
    sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    r_edge = float(np.median([np.percentile(r[surf & (sb == q)], 99.5) for q in range(NSEC) if (surf & (sb == q)).sum() > 30]))
    r_edge = max(r_edge, float(rc_[-1]))
    Tp = np.stack([rc_, top], 1)
    Tp = np.r_[[[0.0, top[0]]], Tp, [[r_edge, top[-1]]]]
    Tp = PL.resample(Tp, ds); Tp[0, 0] = 0.0
    Tg = unit(np.gradient(Tp, axis=0)); Nu = np.stack([-Tg[:, 1], Tg[:, 0]], 1); Nu[0] = [0, 1]
    Bt = Tp - t * Nu
    Bt[:, 0] = np.maximum(Bt[:, 0], 0.0); Bt[0, 0] = 0.0
    prof = [(0.0, float(Bt[0, 1]))] + [tuple(map(float, q)) for q in Bt[1:]] + \
           [tuple(map(float, q)) for q in Tp[:0:-1]] + [(0.0, float(Tp[0, 1]))]
    body = PL.revolve_to_object(prof, c, e1, e2, d)
    info.update(t_mm=round(t * 1e3, 2), t_src='prior', r_edge_mm=round(r_edge * 1e3, 1),
                dome_mm=round(float(top[0] - top.min()) * 1e3, 1), prof_bins=int(ok.sum()))
    geo = dict(c=c, d=d, e1=e1, e2=e2, rc=Tp[:, 0], top=Tp[:, 1], r_edge=r_edge, t=t, rmax=r_edge)
    edge_out = ctx.w(spec, 'resid_edge', rel(0.015, S_REF_SHEET))

    def resid(X):
        Q = X - c; hh = Q @ d; rr = np.linalg.norm(Q - hh[:, None] * d, axis=1)
        z = hh - np.interp(rr, geo['rc'], geo['top'])
        return np.where(rr < r_edge + edge_out, z, -1.0)          # beyond the edge band: not this part's business
    params = dict(centre=c.round(5).tolist(), axis=d.round(5).tolist(), r_edge_mm=round(r_edge * 1e3, 1),
                  t_mm=round(t * 1e3, 2), n_prof=int(len(Tp)))
    return Part(spec['name'], 'sheet_of_revolution', solid=to_mf(body), params=params, k=2 + 2 + 1 + len(Tp),
                bounds_hit=hits, diag=info, geo=geo, resid=resid, reach=revolve_reach(geo))


# ================================================================================================ plate
def fit_plate_bar(ctx, P, V, spec, host, info, hits):
    """prim_potlid.bar_handle with relative windows: PCA long axis (pointing away from the host's axis), top plane by
    a trimmed fit to top-seen points, width = median 3..97 % lateral extent per length bin, thickness from side-seen
    points (2 x median depth below the top plane; else the prior t), straight bar from inside the host's wall to the
    99.5 % tip with a rounded tip, optional hole (closed gap of the top-surface occupancy near the tip)."""
    p = spec.get('params', {})
    lb = ctx.w(spec, 'len_bin', rel(0.005, S_REF_POLAR))
    Tlo = ctx.w(spec, 'T_min', rel(0.003, S_REF_POLAR, 0.0015)); Thi = ctx.w(spec, 'T_max', rel(0.008, S_REF_POLAR))
    back = ctx.w(spec, 'inner_search', rel(0.060, S_REF_POLAR))
    g = ctx.w(spec, 'hole_grid', rel(0.002, S_REF_POLAR)); hole_a = ctx.w(spec, 'hole_min_d', rel(40e-6 ** 0.5, S_REF_POLAR)) ** 2
    hole_tip = ctx.w(spec, 'hole_tip', rel(0.060, S_REF_POLAR))
    if host is not None and 'd' in host.geo:
        c, d = host.geo['c'], host.geo['d']
    else:
        c, d = ctx.c0, unit(np.mean(V, 0))
    m0 = P.mean(0)
    w_, Vv = np.linalg.eigh(np.cov((P - m0).T))
    u = Vv[:, 2]
    rad = (m0 - c) - ((m0 - c) @ d) * d
    if u @ rad < 0:
        u = -u
    n = Vv[:, 0]
    if n @ d < 0:
        n = -n
    top = (V @ n) > 0.3
    T_ = P[top] if top.sum() > 50 else P
    for _ in range(4):
        mt = T_.mean(0); w2, V2 = np.linalg.eigh(np.cov((T_ - mt).T)); n2 = V2[:, 0]
        if n2 @ n < 0:
            n2 = -n2
        res = (T_ - mt) @ n2
        T_ = T_[np.abs(res - np.median(res)) < 2.5 * 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-4]
    n = n2; u = unit(u - (u @ n) * n); w = np.cross(n, u)
    p_top = mt
    s = (P - p_top) @ u; a = (P - p_top) @ w
    W, A, S = [], [], []
    for s0 in np.arange(np.percentile(s, 1), np.percentile(s, 99), lb):
        mm = (s >= s0) & (s < s0 + lb)
        if mm.sum() >= 15:
            lo, hi = np.percentile(a[mm], [3, 97]); W.append(hi - lo); A.append(0.5 * (lo + hi)); S.append(s0 + 0.5 * lb)
    W, A, S = np.array(W), np.array(A), np.array(S)
    width = float(np.median(W))
    k = np.polyfit(S, A, 1) if len(S) >= 4 else np.array([0.0, float(np.median(A))])
    ang = math.atan(k[0]); u2 = unit(math.cos(ang) * u + math.sin(ang) * w); w2 = np.cross(n, u2)
    origin = p_top + k[1] * w
    s = (P - origin) @ u2; a = (P - origin) @ w2; b = (P - origin) @ n
    side = np.abs(V @ w2) > 0.5
    btop = float(np.median(b[top])) if top.sum() > 30 else 0.0
    if side.sum() > 50:
        T = clip_flag('T', float(2 * np.median(btop - b[side])), Tlo, Thi, hits); t_src = 'side'
    else:
        T, t_src = ctx.t, 'prior'
    s_tip = float(np.percentile(s, 99.5))
    ss = np.linspace(np.percentile(s, 0.5) - back, s_tip, 400)
    pts = origin + ss[:, None] * u2
    if host is not None and 'rmax' in host.geo and 'd' in host.geo:
        rr = np.linalg.norm((pts - c) - ((pts - c) @ d)[:, None] * d, axis=1)
        inside = rr < host.geo['rmax'] - 2 * host.geo.get('t', ctx.t)
        s_in = float(ss[inside].max()) if inside.any() else float(ss[0])
    else:
        s_in = float(np.percentile(s, 0.5))
    half = 0.5 * width
    L_ = s_tip - half - s_in
    cs = mf.CrossSection.square((L_, width)).translate((s_in, -half))
    cs = cs + mf.CrossSection.circle(half, 32).translate((s_tip - half, 0.0))
    hole = None
    tp = top & (s > s_in)
    if p.get('hole', True) and tp.sum() > 200:
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
            if area >= hole_a and sc > s_tip - hole_tip and abs(ac) < 0.5 * half:
                if best is None or area > best[0]:
                    best = (area, sc, ac)
        if best is not None:
            rh = math.sqrt(best[0] / math.pi)
            hole = dict(s_mm=round((s_tip - best[1]) * 1e3, 1), a_mm=round(best[2] * 1e3, 1), d_mm=round(2 * rh * 1e3, 1))
            cs = cs - mf.CrossSection.circle(rh, 32).translate((best[1], best[2]))
    bar = cs.extrude(T)
    R = np.stack([u2, w2, n], 1)
    o3 = origin + (btop - T) * n
    bar = bar.transform(PL.frame_T(R, o3))
    info.update(width_mm=round(width * 1e3, 1), T_mm=round(T * 1e3, 1), T_src=t_src,
                length_mm=round((s_tip - s_in) * 1e3, 1), tilt_deg=round(math.degrees(math.asin(min(1, abs(n @ d)))), 1),
                hole=hole)
    fr = dict(origin=o3, R=R, L=(s_in, s_tip), width=width, T=T)

    def resid(X):                                     # L-inf distance outside the bar box
        Q = (X - fr['origin']) @ fr['R']
        ex = np.stack([fr['L'][0] - Q[:, 0], Q[:, 0] - fr['L'][1], np.abs(Q[:, 1]) - 0.5 * fr['width'],
                       -Q[:, 2], Q[:, 2] - fr['T']], 1)
        return ex.max(1)
    return bar, fr, resid, 9 + (3 if hole else 0)


def plane_outline(ctx, P, C, spec, info, hits, mode='occupancy'):
    """prim_boards: plane from camera-oriented PCA normals, thickness from two seen faces (else the prior t),
    occupancy outline (closing, hole fill, opening, significant components, smoothed contour) or its minimum-area
    rectangle, extruded between the two face planes."""
    grid = ctx.w(spec, 'grid', (0.0, PB.GRID))
    close_mm = ctx.w(spec, 'close', (0.0, 0.003))
    n, planar = L.normals(P, C, k=24)
    a, pinfo = PB.fit_plane(P, C, n, planar)
    op, om = pinfo['off_p'], pinfo['off_m']
    two = pinfo['n_face_p'] >= 200 and pinfo['n_face_m'] >= 200 and np.isfinite(op) and np.isfinite(om)
    t_lo, t_hi = ctx.w(spec, 't_min', (0.0, 0.003)), ctx.w(spec, 't_max', (0.0, 0.025))
    if two and t_lo <= op - om <= t_hi:
        t = op - om; t_src = 'two_sided'
    else:
        t = ctx.t; t_src = 'prior'
        if pinfo['n_face_p'] >= pinfo['n_face_m'] and np.isfinite(op):
            om = op - t
        elif np.isfinite(om):
            op = om + t
        else:
            dd = P @ a; op = float(np.median(dd)) + 0.5 * t; om = op - t
    d = P @ a
    slab = (d >= om - 0.0015) & (d <= op + 0.0015)
    if slab.sum() < 30:
        slab = np.ones(len(P), bool)
    o, e1, e2 = PB.inplane_frame(P, a, slab)
    X = P - o; U = X @ e1; Vv = X @ e2
    old = PB.GRID
    PB.GRID = grid
    try:
        lo = np.array([U[slab].min(), Vv[slab].min()]) - 0.02
        shape = (int(math.ceil((U[slab].max() - lo[0] + 0.02) / grid)) + 1,
                 int(math.ceil((Vv[slab].max() - lo[1] + 0.02) / grid)) + 1)
        img = PB.occupancy(U[slab], Vv[slab], lo, shape)
        M, r_used = PB.clean_mask(img >= 1, max(1, int(round(close_mm / grid))))
        if not M.any():
            raise RuntimeError('plate: empty outline')
        poly = PB.rect_polygon(M, lo) if mode == 'rect' else PB.mask_polygon(M, lo)
    finally:
        PB.GRID = old
    cs = mf.CrossSection([poly.astype(np.float64)])
    slab_m = mf.Manifold.extrude(cs, float(op - om)).translate([0, 0, float(om)])
    R = np.stack([e1, e2, a], 1)
    T4 = np.eye(4); T4[:3, :3] = R; T4[:3, 3] = o - (o @ a) * a
    solid = slab_m.transform(T4[:3, :])
    info.update(t_mm=round(t * 1e3, 2), t_src=t_src, area_cm2=round(float(abs(cs.area())) * 1e4, 1),
                n_vertices=int(len(poly)), outline=mode)
    return solid, dict(a=a, o=o, e1=e1, e2=e2, t=t), 3 + 2 + 2 * int(len(poly))


def fit_plate(ctx, idx, spec, done):
    """Plate in its own fitted plane: params.outline 'bar' (fit_plate_bar; params.host = the body whose wall the bar
    starts inside) or 'occupancy' / 'rect' (plane_outline, prim_boards construction)."""
    P, C, V = P_(ctx, idx)
    p = spec.get('params', {})
    info, hits = {}, []
    host = done.get(p.get('host')) if p.get('host') else None
    outline = p.get('outline', 'bar')
    if outline == 'bar':
        solid, fr, resid, k = fit_plate_bar(ctx, P, V, spec, host, info, hits)
        geo = dict(frame=fr)
    else:
        solid, geo, k = plane_outline(ctx, P, C, spec, info, hits, mode=outline)
        resid = generic_resid(solid)
    return Part(spec['name'], 'plate', solid=solid, params=dict(outline=outline, **{k_: v for k_, v in info.items()
                                                                                    if k_ in ('width_mm', 'T_mm', 't_mm', 'length_mm')}),
                k=k, bounds_hit=hits, diag=info, geo=geo, resid=resid, reach=bbox_reach(solid))


def fit_plate_set(ctx, idx, spec, done):
    """One occupancy plate per cluster (largest first, up to max_plates) of the assigned points."""
    p = spec.get('params', {})
    vox = ctx.w(spec, 'cluster_vox', rel(0.003, S_REF_POLAR))
    cl = PL.clusters(ctx.P[idx], vox=vox, min_pts=int(p.get('min_pts', 300)))[:int(p.get('max_plates', 4))]
    solids, infos, k = [], [], 0
    for q in cl:
        info, hits = {}, []
        try:
            s_, _, kk = plane_outline(ctx, ctx.P[idx[q]], ctx.C[idx[q]], spec, info, hits,
                                      mode=p.get('outline', 'occupancy'))
            solids.append(s_); k += kk; info['n'] = int(len(q)); infos.append(info)
        except RuntimeError as e:
            infos.append(dict(n=int(len(q)), error=str(e)))
    solid = mf_union(solids)
    return Part(spec['name'], 'plate_set', solid=solid, params=dict(n_plates=len(solids)), k=k, diag=dict(plates=infos),
                resid=generic_resid(solid) if solid is not None else None,
                reach=bbox_reach(solid) if solid is not None else None)


# ================================================================================================ strap
def fit_strap(ctx, idx, spec, done):
    """prim_potlid.arch_strap generalised: the strap's plane is spanned by its PCA long axis and the host's up
    direction (host axis; without a host the cluster's best plane: its two largest PCA axes); per length bin the top height (75th pct of
    top-seen points) and the lateral extent; width = median extent; thickness from side-seen points of the high
    part (else the prior t); the smoothed top curve, offset by T/2, is swept as a rectangle; both ends run down to
    the host's mid-surface (host profile 'rc'/'top' if it has one, else the lowest strap point)."""
    P, C, Av = P_(ctx, idx)
    p = spec.get('params', {})
    host = done.get(p.get('host')) if p.get('host') else None
    ds = ctx.w(spec, 'len_bin', rel(0.003, S_REF_SHEET))
    Wlo, Whi = ctx.w(spec, 'W_min', rel(0.008, S_REF_SHEET)), ctx.w(spec, 'W_max', rel(0.030, S_REF_SHEET))
    Tlo, Thi = ctx.w(spec, 'T_min', rel(0.003, S_REF_SHEET, 0.0015)), ctx.w(spec, 'T_max', rel(0.008, S_REF_SHEET))
    ext = ctx.w(spec, 'end_ext', rel(0.004, S_REF_SHEET)); rs = ctx.w(spec, 'resample', rel(0.002, S_REF_SHEET))
    info, hits = {}, []
    if host is not None and 'd' in host.geo:
        c, d = host.geo['c'], host.geo['d']
    else:
        # no host: the cluster's best plane (two largest PCA axes); up = the second axis, towards the cameras
        c = P.mean(0); Vc = np.linalg.eigh(np.cov((P - c).T))[1]
        d = Vc[:, 1] if (Av @ Vc[:, 1]).mean() >= 0 else -Vc[:, 1]
        c = c - d * float(np.percentile((P - c) @ d, 1))           # height origin at the strap's lowest points
    X = P - c; hh = X @ d; Xp = X - hh[:, None] * d
    w_, V = np.linalg.eigh(np.cov(Xp.T)); u = V[:, 2]; u = unit(u - (u @ d) * d); w = np.cross(d, u)
    s = Xp @ u; a = Xp @ w
    top = (Av @ d) > 0.3
    side = np.abs(Av @ w) > 0.5
    S, H, A, W = [], [], [], []
    for s0 in np.arange(np.percentile(s, 0.5), np.percentile(s, 99.5), ds):
        mm = (s >= s0) & (s < s0 + ds)
        mt = mm & top
        if mt.sum() >= 8:
            S.append(s0 + ds / 2); H.append(np.percentile(hh[mt], 75))
            lo, hi = np.percentile(a[mm], [3, 97]); A.append(0.5 * (lo + hi)); W.append(hi - lo)
    S, H, A, W = map(np.array, (S, H, A, W))
    if len(S) < 3:
        raise RuntimeError('strap: too few top-seen bins')
    width = clip_flag('W', float(np.median(W)), Wlo, Whi, hits)
    acen = float(np.median(A))
    Hs = np.interp(s, S, H)
    hi_part = hh > np.percentile(H, 50)
    sp = side & hi_part
    if sp.sum() > 30:
        T = clip_flag('T', float(2 * np.median(Hs[sp] - hh[sp])), Tlo, Thi, hits); t_src = 'side'
    else:
        T, t_src = ctx.t, 'prior'
    Hsm = ndimage.median_filter(H, size=3, mode='nearest'); Hsm = ndimage.uniform_filter1d(Hsm, 3, mode='nearest')
    if host is not None and 'rc' in host.geo:
        def base_h(sv):
            return np.interp(np.hypot(sv, acen), host.geo['rc'], host.geo['top']) - 0.5 * host.geo['t']
    else:
        lowest = float(np.percentile(hh, 1))

        def base_h(sv):
            return lowest
    S2 = np.r_[S[0] - ext, S, S[-1] + ext]
    H2 = np.r_[base_h(S[0] - ext), Hsm, base_h(S[-1] + ext)]
    curve = PL.resample(np.stack([S2, H2], 1), rs)
    Tg = unit(np.gradient(curve, axis=0)); Nn = np.stack([-Tg[:, 1], Tg[:, 0]], 1)
    Nn[Nn[:, 1] < 0] *= -1
    mid = curve - 0.5 * T * Nn
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
    strap = to_mf(tm)
    info.update(width_mm=round(width * 1e3, 1), T_mm=round(T * 1e3, 1), T_src=t_src,
                span_mm=round(float(S[-1] - S[0]) * 1e3, 1), height_mm=round(float(Hsm.max()) * 1e3, 1))
    tree = cKDTree(np.r_[verts, tm.sample(4000)])
    return Part(spec['name'], 'strap', solid=strap, params=dict(width_mm=info['width_mm'], T_mm=info['T_mm'],
                                                                n_knots=int(len(S))),
                k=2 + len(S), bounds_hit=hits, diag=info, geo=dict(c=c, d=d, u=u, w=w),
                resid=lambda Y: tree.query(Y)[0], reach=bbox_reach(strap))


# ================================================================================================ ball
def fit_ball(ctx, idx, spec, done):
    """Marker balls: prim_potlid.markers_from (one shared detector, BALL hardware constants) on the compact
    clusters of the assigned residual points; host surface = union of the parts in params.of. Options:
    require_cap (prim_rack.marker_parts: keep only a free-fit radius in BALL.free_r or a curved cap), reject_inside
    (part name whose cavity footprint must not contain a ball centre), stems (default True)."""
    p = spec.get('params', {})
    of = [done[n] for n in p.get('of', []) if n in done]
    info = {}
    solids = [q.solid for q in of if q.solid is not None]
    if not solids or len(idx) < BALL['min_pts']:
        return Part(spec['name'], 'ball', params=dict(n=0), diag=dict(markers=[], note='no residual'))
    surf_tm = from_mf(mf_union(solids))
    Rp, Rv = ctx.P[idx], ctx.V[idx]
    Rz = of[0].resid(Rp) if of[0].resid is not None else np.full(len(Rp), APP_D + 0.01)
    old = PL.APP_D
    PL.APP_D = spec.get('_band', APP_D)                # markers_from's re-cluster height test
    try:
        parts, minfo = PL.markers_from(Rp, Rv, Rz, ctx.P, surf_tm, 'nostem' if p.get('stems') is False else 'fit')
    finally:
        PL.APP_D = old
    if p.get('require_cap') or p.get('reject_inside'):
        keep_parts, out = [], []
        host_sd = None
        if p.get('reject_inside') and p['reject_inside'] in done:
            host_sd = done[p['reject_inside']].geo.get('inside_cavity')
        for m in minfo:
            m = dict(m)
            if 'rejected' not in m and host_sd is not None and host_sd(np.asarray(m['centre'])[None])[0]:
                m['rejected'] = 'in_cavity'
            if 'rejected' not in m and p.get('require_cap'):
                fr_ok = ('free_r_mm' in m and BALL['free_r'][0] * 1e3 <= m['free_r_mm'] <= BALL['free_r'][1] * 1e3
                         and m['free_res_mm'] <= 1.2)
                if not (fr_ok or m.get('spread', 0) >= BALL['spread']):
                    m['rejected'] = 'flat'
            out.append(m)
        minfo = out
        parts = []
        pq = trimesh.proximity.ProximityQuery(surf_tm)
        for m in minfo:
            if 'rejected' in m:
                continue
            cc = np.asarray(m['centre']); r = m['r_mm'] * 1e-3
            parts.append(PL.mf_sphere(cc, r, seg=20 if p.get('require_cap') else 24))
            if m.get('stem'):
                sp = pq.on_surface(cc[None])[0][0]
                ax = (sp - cc) / max(np.linalg.norm(sp - cc), 1e-9)
                parts.append(PL.mf_cylinder(cc, sp + 0.002 * ax, PL.STEM_R))
    acc = [m for m in minfo if 'rejected' not in m]
    solid = mf_union(parts)
    info['markers'] = minfo
    geo = dict(balls=[(np.asarray(m['centre']), m['r_mm'] * 1e-3) for m in acc])
    hits = [f'r{j}' for j, m in enumerate(acc) if m.get('mode') == 'prior']
    return Part(spec['name'], 'ball', solid=solid, params=dict(n=len(acc), r_mm=[m['r_mm'] for m in acc],
                                                                stems=int(sum(1 for m in acc if m.get('stem')))),
                k=4 * len(acc), bounds_hit=hits, diag=info, geo=geo,
                resid=generic_resid(solid) if solid is not None else None)


# ================================================================================================ splat / tsdf_patch
def fit_splat(ctx, idx, spec, done):
    """lathe_obs appendages: each voxel-connected cluster (>= min_pts) of the assigned points is splatted on a grid
    (dilation, closing), Gaussian-blurred and meshed by marching cubes. combine 'union' (default: manifold union)
    or 'concat' (kept as a separate mesh, as lathe_obs.py did)."""
    from skimage.measure import marching_cubes
    p = spec.get('params', {})
    vox = ctx.w(spec, 'vox', rel(0.002, S_REF_HEIGHT))
    min_pts = int(p.get('min_pts', 400))
    A = ctx.P[idx]
    info = dict(n=int(len(A)))
    meshes = []
    if len(A) >= min_pts:
        lo = A.min(0) - 3 * vox
        ii = np.floor((A - lo) / vox).astype(int); shp = ii.max(0) + 4
        occ = np.zeros(shp, bool); occ[tuple(ii.T)] = True
        occ = ndimage.binary_closing(ndimage.binary_dilation(occ, iterations=1), iterations=2)
        lab, nl = ndimage.label(occ)
        cnts = np.bincount(lab[tuple(ii.T)], minlength=nl + 1)[1:]
        for q in range(nl):
            if cnts[q] < min_pts:
                continue
            g = np.pad(lab == q + 1, 1).astype(np.float32)
            g = ndimage.gaussian_filter(g, 0.7)
            vv, ff, _, _ = marching_cubes(g, 0.5, spacing=(vox,) * 3)
            meshes.append(trimesh.Trimesh(vv + lo - vox, ff, process=True))
    info['clusters'] = len(meshes)
    if not meshes:
        return Part(spec['name'], 'splat', params=dict(n=0), diag=info)
    if p.get('combine', 'union') == 'concat':
        m = trimesh.util.concatenate(meshes)
        return Part(spec['name'], 'splat', mesh=m, params=dict(n=len(meshes), combine='concat'), diag=info,
                    k=0, resid=Surf(m).signed if len(m.faces) else None)
    sol = []
    for m in meshes:
        try:
            m.fix_normals(); sol.append(to_mf(m))
        except RuntimeError as e:
            info.setdefault('errors', []).append(str(e))
    solid = mf_union(sol)
    return Part(spec['name'], 'splat', solid=solid, params=dict(n=len(sol), combine='union'), diag=info, k=0,
                resid=generic_resid(solid) if solid is not None else None)


def fit_tsdf_patch(ctx, idx, spec, done):
    """Faces of our own library mesh (ctx.lib, same object frame) whose centres lie outside every part in
    params.of by more than params.margin (default APP_D): the hand kits' 'tsdf' variant. Not watertight; the
    program concatenates it after the union."""
    p = spec.get('params', {})
    if not ctx.lib:
        raise RuntimeError('tsdf_patch needs the library mesh path (run_program(..., lib=...))')
    src = trimesh.load(ctx.lib, force='mesh')
    margin = float(p.get('margin', APP_D)) if not isinstance(p.get('margin'), dict) else ctx.w(spec, 'margin', (0, APP_D))
    of = [done[n] for n in p.get('of', []) if n in done]
    X = src.triangles_center
    dist = np.min([q.resid(X) for q in of if q.resid is not None], axis=0) if of else np.full(len(X), np.inf)
    keep = dist > margin
    app = src.submesh([np.nonzero(keep)[0]], append=True) if keep.any() else None
    return Part(spec['name'], 'tsdf_patch', mesh=app, params=dict(faces=int(keep.sum())), diag=dict(faces=int(keep.sum())))


# ================================================================================================ rounded box
def fit_rounded_box(ctx, idx, spec, done):
    """Box in the PCA frame of the assigned points; half extents = robust (q, 100-q) percentile spans; edge radius
    = params.r_frac x the smallest half extent (default 0.2); hull of 8 corner spheres."""
    P = ctx.P[idx]
    p = spec.get('params', {})
    q = float(p.get('pct', 1.0))
    m0 = P.mean(0); w_, V = np.linalg.eigh(np.cov((P - m0).T))
    X = (P - m0) @ V
    lo, hi = np.percentile(X, q, 0), np.percentile(X, 100 - q, 0)
    cen = 0.5 * (lo + hi); he = 0.5 * (hi - lo)
    r = float(p.get('r_frac', 0.2)) * float(he.min())
    corners = [cen + np.array([sx, sy, sz]) * np.maximum(he - r, 1e-4)
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    sph = [mf.Manifold.sphere(max(r, 1e-4), 16).translate(tuple(map(float, c))) for c in corners]
    box = mf.Manifold.batch_hull(sph)
    T = np.c_[V, m0]
    solid = box.transform(T)
    return Part(spec['name'], 'rounded_box', solid=solid, params=dict(half_extents_mm=(he * 1e3).round(1).tolist(),
                                                                     r_mm=round(r * 1e3, 1)),
                k=10, diag=dict(n=int(len(P))), resid=generic_resid(solid), reach=bbox_reach(solid))


# ================================================================================================ support frame (tube_rrect, cone_array)
def lower_plane(P, up, cs, band, iters=4):
    """prim_rack.lower_plane with relative windows: lower supporting plane of the points (per cell the 2nd-pct
    height, plane fitted to the lowest 30 % of cells + band, iterated); returns (up, offset)."""
    off = 0.0
    for _ in range(iters):
        a = np.eye(3)[np.argmin(np.abs(up))]; a = a - (a @ up) * up; a /= np.linalg.norm(a); b = np.cross(up, a)
        h = P @ up; y = P @ a; z = P @ b
        key = np.floor(y / cs).astype(np.int64) * 100000 + np.floor(z / cs).astype(np.int64)
        o = np.argsort(key, kind='stable'); _, st, cnt = np.unique(key[o], return_index=True, return_counts=True)
        low = []
        for s0, c in zip(st, cnt):
            if c < 20:
                continue
            ii = o[s0:s0 + c]
            low.append(ii[np.argsort(h[ii])[max(0, int(0.02 * c))]])
        low = np.array(low)
        A = np.c_[y[low], z[low], np.ones(len(low))]; hl = h[low]
        coef = np.linalg.lstsq(A, hl, rcond=None)[0]
        for _ in range(10):
            r = hl - A @ coef; m = r < np.percentile(r, 30) + band
            coef = np.linalg.lstsq(A[m], hl[m], rcond=None)[0]
        n = up - coef[0] * a - coef[1] * b; s = np.linalg.norm(n); up = n / s; off = coef[2] / s
    return up, off


def support_frame(ctx, spec):
    """Program-level frame for parts standing on a table: up = normal of the lower supporting plane of all points
    (the table cut of obs_points), x = in-plane PCA long axis, y = up x x with the cameras on the -y side, origin on
    the cut plane. 'tall_end' (default on): x is flipped so the end holding the tall points (h > tall_frac x the
    99.8 % height) is at -x; its x range is stored as frame['tall'] = (lo, hi)."""
    P, C = ctx.P, ctx.C
    cell = ctx.w(spec, 'cell', rel(0.010, S_REF_TUBE)); band = ctx.w(spec, 'band', rel(0.003, S_REF_TUBE))
    X = P - P.mean(0)
    up = np.linalg.eigh(np.cov(X.T))[1][:, 0]
    if np.mean((C - P) @ up) < 0:
        up = -up
    up, off = lower_plane(P, up, cell, band)
    Q = P - np.outer(P @ up, up)
    Lx = np.linalg.eigh(np.cov((Q - Q.mean(0)).T))[1][:, -1]
    Lx = Lx - (Lx @ up) * up; Lx /= np.linalg.norm(Lx)
    w = np.cross(up, Lx)
    if np.mean(C @ w) > np.mean(P @ w):
        Lx, w = -Lx, -w
        w = np.cross(up, Lx)
    o = P.mean(0); o = o - (o @ up) * up + off * up
    fr = dict(up=up, L=Lx, w=w, o=o)
    tall = None
    if spec.get('tall_end', True):
        x, y, h = frame_xyh(P, fr)
        frac = float(spec.get('tall_frac', 0.65))
        tall_m = h > frac * np.percentile(h, 99.8)
        lo, hi = np.percentile(x[tall_m], [1, 99]); xmin, xmax = np.percentile(x, [0.5, 99.5])
        if (lo + hi) / 2 > (xmin + xmax) / 2:
            fr = rotate_frame(fr, math.pi)
            x, y, h = frame_xyh(P, fr)
            lo, hi = np.percentile(x[tall_m], [1, 99])
        tall = (float(lo), float(hi))
    fr['tall'] = tall
    fr['table'] = -ctx.table_band
    return fr


def frame_xyh(P, fr):
    X = P - fr['o']
    return X @ fr['L'], X @ fr['w'], X @ fr['up']


def rotate_frame(fr, theta, dx=0.0, dy=0.0):
    c, s = math.cos(theta), math.sin(theta)
    Lx = c * fr['L'] + s * fr['w']; w = np.cross(fr['up'], Lx)
    o = fr['o'] + dx * fr['L'] + dy * fr['w']
    out = dict(fr); out.update(L=Lx, w=w, o=o)
    return out


def frame_T4(fr):
    R = np.stack([fr['L'], fr['w'], fr['up']], 1)
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = fr['o']
    return T


# ================================================================================================ tube_rrect
def rr_poly(cx, cy, hx, hy, r, theta=0.0, seg=6):
    """Counter-clockwise rounded-rectangle polygon, rotated by theta about its centre."""
    base = PR.rrect_poly(0.0, 0.0, hx, hy, r, seg=seg)
    c, s = math.cos(theta), math.sin(theta)
    return np.c_[cx + c * base[:, 0] - s * base[:, 1], cy + s * base[:, 0] + c * base[:, 1]]


def rr_sd(q, xs, ys, ex, ey, cx, cy):
    """Signed distance to the rounded rectangle (half extents ex, ey, corner q['r'], rotation q['theta'] about
    (cx, cy)) and its outward unit normal (gx, gy) in frame coordinates."""
    c_, s_ = math.cos(q['theta']), math.sin(q['theta'])
    X = c_ * (xs - cx) + s_ * (ys - cy); Y = -s_ * (xs - cx) + c_ * (ys - cy)
    sd, gx, gy = PR.rrect_sd(X, Y, ex, ey, q['r'])
    return sd, c_ * gx - s_ * gy, s_ * gx + c_ * gy


TUBE_NAMES = ('cx', 'cy', 'ux', 'uy', 'ex', 'ey', 'fx', 'fy', 'r', 'theta', 's0', 's1', 'dout')


def tube_section(q, wall, hh, Href):
    """(cx, cy, ex, ey) of the OUTER face at height hh. thin: centre and half extents linear in h (lean ux, uy;
    draft fx, fy). lip: the outline (cx, cy, ex, ey) is the lip outline; the outer face lies dout (Href - h)
    outside it (a leaning outer face), the inner face s0 + s1 (Href - h) inside it."""
    if wall == 'thin':
        return q['cx'] + q['ux'] * hh, q['cy'] + q['uy'] * hh, q['ex'] + q['fx'] * hh, q['ey'] + q['fy'] * hh
    return q['cx'], q['cy'], q['ex'], q['ey']


def fit_tube_rrect(ctx, idx, spec, done):
    """Rounded-rectangle tube in the program's support frame (x, y, h above the table cut), fitted by robust least
    squares (soft_l1, F_SCALE) to point classes chosen by the side they were seen from (the in-plane view component
    along the fitted outward normal; no face signs are assumed):
      wall 'thin' (a thin tube, thickness t from the prior grid): outer-seen sd = 0, inner-seen sd = -t,
        top-seen (rim) sd = -t/2; centre, lean, half extents, draft (linear in h) and corner radius free.
        params.above = a host part: only points above the host's top (+ a band) are classed as outer / rim, and
        below it only the cavity's own inner faces (the host hides the outside there).
      wall 'lip' (a tray with a thick rim): outline (cx, cy, ex, ey, r, theta) at the top, outer face leaning out
        by dout per unit depth, inner face inset s0 + s1 (top - h); outer-seen sd = dout (top - h), inner-seen
        sd = -(s0 + s1 (top - h)), lip-top-seen sd = -s0/2. Top = robust plane through lip-top samples along the
        outline edges (top 'plane').
    params.x_min_from = 'tall_lo' fixes the -x end at the frame's tall region (minus t): the tube ends against a
    taller part there; points of that end region are not used. params.align_frame: re-express the program frame in
    the fitted outline frame (rotation theta, centre line y = cy) and refit twice (later parts use it).
    Floor: the table plate (table + t); 'thin' tubes take a raised inner floor where >= 50 up-facing points lie
    inside the cavity below the host's top. carve 'self' (default for 'lip'): solid = outer - cavity; 'all'
    (default for 'thin'): the cavity is subtracted from the whole assembly after the union."""
    p = spec.get('params', {})
    if ctx.frame is None:
        raise RuntimeError('tube_rrect needs a support frame (program "frame": {"type": "support"})')
    wall = p.get('wall', 'thin')
    host = done.get(p.get('above')) if p.get('above') else None
    info, hits = {}, []
    t = ctx.t
    fr = ctx.frame
    rounds = 3 if (wall == 'lip' and p.get('align_frame', True)) else 1
    for rnd in range(rounds):
        q, top_c, H_med, cls_info, r_, hb = tube_fit_once(ctx, idx, spec, fr, wall, host, t, info)
        if rnd < rounds - 1:
            fr = rotate_frame(fr, q['theta'], 0.0, q['cy'])
    if wall == 'lip' and p.get('align_frame', True):
        ctx.frame = fr
        info['frame_aligned'] = True
    hits += hb
    info.update(cls_info)
    x, y, h = frame_xyh(ctx.P[idx], fr)
    table = fr['table']; h_ft = table + t
    if p.get('floor_depth') is not None:
        # floor plate top at depth below the robust top (instead of on the table): a development-only option for
        # depths known from other episodes; the table plate lies t below it
        h_ft = H_med - ctx.w(spec, 'floor_depth', (0.0, 0.0)); table = h_ft - t
        info['floor_depth_mm'] = round((H_med - h_ft) * 1e3, 2)
    elif host is not None and 'h_ft' in host.geo:
        table, h_ft = host.geo['h_tab'], host.geo['h_ft']
    nup = ctx.normals()[0][idx] @ fr['up']
    if wall == 'thin':
        sd = rr_sd(q, x, y, *tube_section(q, wall, h, None)[2:], *tube_section(q, wall, h, None)[:2])[0]
        below = host.geo['H_med'] if host is not None else top_c[0]
        fl = (sd < -t - ctx.w(spec, 'floor_in', rel(0.004, S_REF_TUBE))) & (nup > 0.85) & (h < below) & (h > h_ft)
        h_cf = float(np.median(h[fl])) if fl.sum() >= 50 else h_ft
        info.update(h_floor_mm=round(h_cf * 1e3, 2), n_floor=int(fl.sum()))
    else:
        h_cf = h_ft
    geo = dict(q=q, wall=wall, top_c=top_c, H_med=H_med, h_tab=table, h_ft=h_ft, h_cf=h_cf, frame=fr, t=t,
               x_min_fix=(fr['tall'][0] - t) if (p.get('x_min_from') == 'tall_lo' and fr.get('tall')) else None,
               x_clip=-np.inf)
    carve = p.get('carve', 'all' if wall == 'thin' else 'self')
    part = Part(spec['name'], 'tube_rrect', params={**{n: round(float(q[n]), 5) for n in TUBE_NAMES},
                                                    'wall': wall, 'top_mm': round(float(H_med) * 1e3, 2),
                                                    'h_floor_mm': round(h_cf * 1e3, 2), 'carve': carve},
                k=int(info.pop('_k')), bounds_hit=hits, diag=info, geo=geo)
    tube_build(part)

    def inside_cavity(X):                              # e.g. ball rejection: centre over the cavity (lip inset)
        xx, yy, hh = frame_xyh(np.atleast_2d(X), fr)
        cx, cy, ex, ey = tube_section(q, wall, hh, H_med)
        sd = rr_sd(q, xx, yy, ex, ey, cx, cy)[0]
        return (sd < -q['s0']) & (xx > part.geo['x_clip'])
    geo['inside_cavity'] = inside_cavity

    def cavity_mask(X, inset):                         # assignment rule 'cavity': inside the inner face by > inset
        xx, yy, hh = frame_xyh(X, fr)
        cx, cy, ex, ey = tube_section(q, wall, hh, H_med)
        sd = rr_sd(q, xx, yy, ex, ey, cx, cy)[0]
        w_ = q['s0'] + q['s1'] * (H_med - hh) if wall == 'lip' else q['s0']
        return (sd < -(w_ + inset)) & (xx > part.geo['x_clip'])
    geo['cavity_mask'] = cavity_mask
    return part


def tube_fit_once(ctx, idx, spec, fr, wall, host, t, info):
    """One robust fit of the tube in frame fr (see fit_tube_rrect). Returns (q dict, top plane coefficients, robust
    top height, class counts / residuals, final residual vector, bound hits)."""
    p = spec.get('params', {})
    P, C, V = P_(ctx, idx)
    x, y, h = frame_xyh(P, fr)
    vx, vy = V @ fr['L'], V @ fr['w']
    nup = ctx.normals()[0][idx] @ fr['up']
    W = lambda name, mm: ctx.w(spec, name, rel(mm, S_REF_TUBE))
    table = fr['table']; h_ft = table + t
    if host is not None and 'h_ft' in host.geo:                # stand on the host's floor plate
        table, h_ft = host.geo['h_tab'], host.geo['h_ft']
    rng = np.random.default_rng(0)
    x_min_fix = (fr['tall'][0] - t) if (p.get('x_min_from') == 'tall_lo' and fr.get('tall')) else None
    use = np.ones(len(P), bool)
    if x_min_fix is not None:
        use = x > fr['tall'][1] + W('skip_end', 0.040)
    if wall == 'lip':
        # ---- top plane through lip-top samples along the outline edges (not the fixed end)
        tl = x > fr['tall'][1] + W('skip_lip', 0.015) if x_min_fix is not None else np.ones(len(P), bool)
        ylo, yhi = np.percentile(y[tl], [1, 99]); xhi = np.percentile(x[tl], 99)
        eb, sg_w = W('edge_band', 0.012), W('top_seg', 0.010)
        T_ = []
        for m, coord in (((y < ylo + eb) & tl, x), ((y > yhi - eb) & tl, x), ((x > xhi - eb) & tl, y)):
            if m.sum() < 50:
                continue
            sg = np.floor(coord[m] / sg_w).astype(int)
            xm, ym, hm = x[m], y[m], h[m]
            for s_ in np.unique(sg):
                kk = sg == s_
                if kk.sum() >= 30:
                    T_.append((np.median(xm[kk]), np.median(ym[kk]), np.percentile(hm[kk], 98)))
        T_ = np.array(T_)
        H_med = float(np.median(T_[:, 2]))
        A = np.c_[np.ones(len(T_)), T_[:, 0], T_[:, 1]]
        m = np.ones(len(T_), bool)
        for _ in range(5):
            top_c = np.linalg.lstsq(A[m], T_[m, 2], rcond=None)[0]
            rr = T_[:, 2] - A @ top_c
            m = np.abs(rr - np.median(rr[m])) < W('top_robust', 0.003)
        info['top_plane'] = dict(a_mm=round(top_c[0] * 1e3, 2), slope_x=round(top_c[1], 4), slope_y=round(top_c[2], 4),
                                 n=int(m.sum()))
        xs0 = x[use]; ys0 = y[use]
        ylo, yhi = np.percentile(ys0, [1, 99]); xhi = np.percentile(xs0, 99.5)
        xa = x_min_fix if x_min_fix is not None else np.percentile(xs0, 0.5)
        q = dict(cx=0.5 * (xa + xhi), cy=0.5 * (ylo + yhi), ux=0.0, uy=0.0, ex=0.5 * (xhi - xa), ey=0.5 * (yhi - ylo),
                 fx=0.0, fy=0.0, r=W('r0', 0.015), theta=0.0, s0=W('s0_init', 0.008), s1=0.3, dout=0.0)
        free = ['cx', 'cy', 'theta', 'dout', 'ey', 'r', 's0', 's1']
        if x_min_fix is None:
            free.insert(4, 'ex')
        else:
            free.insert(4, 'ex')                          # ex free, cx tied so the -x end stays at x_min_fix
        lo = dict(cx=-np.inf, cy=-np.inf, theta=-0.2, dout=-0.3, ex=W('e_min', 0.030), ey=W('e_min', 0.030),
                  r=W('r_min', 0.002), s0=W('s0_min', 0.004), s1=0.0)
        hi = dict(cx=np.inf, cy=np.inf, theta=0.2, dout=1.0, ex=W('e_max', 0.150) * 10, ey=W('e_max', 0.150),
                  r=W('r_max', 0.060), s0=W('s0_max', 0.030), s1=1.5)
    else:
        H_host = host.geo['H_med'] if host is not None else -np.inf
        bw = W('flat_band', 0.020)
        tops = [np.percentile(h[(y >= a) & (y < a + bw)], 99) for a in np.arange(np.percentile(y, 2), np.percentile(y, 98), bw)
                if ((y >= a) & (y < a + bw) & (h > H_host)).sum() > 30]
        H_med = float(np.median(tops))
        top_c = np.array([H_med, 0.0, 0.0])
        tall = h > (H_host + W('init_above', 0.010) if host is not None else np.percentile(h, 50))
        xl, xh = np.percentile(x[tall], [1, 99]); yl, yh = np.percentile(y[tall], [1, 99])
        q = dict(cx=0.5 * (xl + xh), cy=0.5 * (yl + yh), ux=0.0, uy=0.0, ex=0.5 * (xh - xl), ey=0.5 * (yh - yl),
                 fx=0.0, fy=0.0, r=W('r0', 0.020), theta=0.0, s0=t, s1=0.0, dout=0.0)
        lean = float(p.get('lean_max', 0.25)) if p.get('lean', True) else 1e-6
        free = ['cx', 'cy', 'ux', 'uy', 'ex', 'ey', 'fx', 'fy', 'r']
        lo = dict(cx=-np.inf, cy=-np.inf, ux=-lean, uy=-lean, ex=W('ex_min', 0.010), ey=W('ey_min', 0.010),
                  fx=-lean, fy=-lean, r=W('r_min', 0.004))
        hi = dict(cx=np.inf, cy=np.inf, ux=lean, uy=lean, ex=W('ex_max', 0.080), ey=W('ey_max', 0.120),
                  fx=lean, fy=lean, r=W('r_max', 0.050))
    lo_v = np.array([lo[n] for n in free]); hi_v = np.array([hi[n] for n in free])

    def unpack(z):
        qq = dict(q); qq.update({n: float(v) for n, v in zip(free, z)})
        if x_min_fix is not None and wall == 'lip':
            qq['cx'] = x_min_fix + qq['ex']
        return qq
    Ht = top_c[0] + top_c[1] * x + top_c[2] * y
    gate = W('class_gate', 0.008)
    n_it = int(p.get('iters', 4 if wall == 'lip' else 5))
    for it in range(n_it):
        cx, cy, ex, ey = tube_section(q, wall, h, Ht)
        sd, gx, gy = rr_sd(q, x, y, ex, ey, cx, cy)
        vr = vx * gx + vy * gy
        if wall == 'lip':
            s_h = q['s0'] + q['s1'] * (Ht - h)
            near = use & (sd > -W('near_in', 0.035)) & (sd < W('near_out', 0.015))
            outer = near & (h > W('low', 0.003)) & (h < Ht - W('below_top', 0.006)) & (vr > VR) & \
                (np.abs(sd - q['dout'] * (Ht - h)) < gate)
            inner = near & (h > W('low_in', 0.006)) & (h < Ht - W('below_top', 0.006)) & (vr < -VR) & \
                (np.abs(sd + s_h) < gate)
            rim = near & (h > Ht - W('lip_below', 0.003)) & (h < Ht + W('lip_above', 0.004)) & \
                (sd > -W('lip_in', 0.020)) & (sd < W('lip_out', 0.006))
        else:
            near = (np.abs(sd) < W('near', 0.012)) & (h < H_med + W('top_above', 0.004))
            upper = h > H_host + W('host_band', 0.004)
            vert = np.abs(nup) < 0.7
            outer = near & upper & (vr > VR) & (sd > -W('out_in', 0.006)) & (h < H_med - W('rim_band', 0.003))
            inner = near & upper & (vr < -VR) & (sd < W('in_out', 0.003)) & (h < H_med - W('rim_band', 0.003)) & vert
            if it >= 2 and host is not None:
                inner |= (near & ~upper & (h > h_ft + W('host_band', 0.004)) & (vr < -VR) & vert &
                          (sd < -t + W('in_out', 0.003)) & (sd > -t - gate))
            rim = near & (h >= H_med - W('rim_band', 0.003))
        cls = np.r_[np.zeros(outer.sum()), np.ones(inner.sum()), 2 * np.ones(rim.sum())].astype(int)
        ii = np.r_[np.nonzero(outer)[0], np.nonzero(inner)[0], np.nonzero(rim)[0]]
        if len(ii) > 60000:
            sub = rng.choice(len(ii), 60000, replace=False); ii, cls = ii[sub], cls[sub]
        if len(ii) < 50:
            raise RuntimeError(f'tube_rrect: too few classified points ({len(ii)})')
        xs, ys, hs, Hs = x[ii], y[ii], h[ii], Ht[ii]

        def res(z):
            qq = unpack(z)
            cx_, cy_, ex_, ey_ = tube_section(qq, wall, hs, Hs)
            sdq = rr_sd(qq, xs, ys, ex_, ey_, cx_, cy_)[0]
            if wall == 'lip':
                target = np.where(cls == 0, qq['dout'] * (Hs - hs),
                                  np.where(cls == 1, -(qq['s0'] + qq['s1'] * (Hs - hs)), -0.5 * qq['s0']))
            else:
                target = np.where(cls == 0, 0.0, np.where(cls == 1, -t, -0.5 * t))
            return sdq - target
        z0 = np.clip(np.array([q[n] for n in free]), lo_v + 1e-6, hi_v - 1e-6)
        sol = least_squares(res, z0, bounds=(lo_v, hi_v), loss='soft_l1', f_scale=F_SCALE)
        q = unpack(sol.x)
    r_ = res(sol.x)
    hb = bound_flags(free, sol.x, lo_v, hi_v)
    cls_info = dict(n_outer=int(outer.sum()), n_inner=int(inner.sum()), n_top=int(rim.sum()),
                    med_abs_res_mm=round(float(np.median(np.abs(r_))) * 1e3, 3),
                    res_by_class_mm=[round(float(np.median(np.abs(r_[cls == k]))) * 1e3, 3) if (cls == k).any() else None
                                     for k in range(3)], _k=len(free) + (3 if wall == 'lip' else 1))
    return q, top_c, H_med, cls_info, r_, hb


def tube_build(part):
    """(Re)build the tube's outer solid and cavity in frame coordinates, apply the cavity clip (x >= x_clip) and
    set part.solid / part.cavity in the object frame (prim_rack.build_body construction)."""
    g = part.geo
    q, wall, tc, H = g['q'], g['wall'], g['top_c'], g['H_med']
    h_tab = g['h_tab']
    top0 = tc[0] if wall == 'lip' else H

    def ring(pl, hh):
        return np.c_[pl, np.full(len(pl), hh)]

    def on_top(pl, dz=0.0):
        return np.c_[pl, tc[0] + tc[1] * pl[:, 0] + tc[2] * pl[:, 1] + dz]
    if wall == 'thin':
        def sec(hh, inset):
            cx, cy, ex, ey = tube_section(q, wall, hh, None)
            return rr_poly(cx, cy, ex - inset, ey - inset, max(q['r'] - inset, 0.002), q['theta'])
        outer = mf.Manifold.hull_points(np.r_[ring(sec(h_tab, 0), h_tab), ring(sec(H, 0), H)])
        T = q['s0']; h_cf = g['h_cf']
        fl = sec(h_cf, T)
        cxf, cyf = q['cx'] + q['ux'] * h_cf, q['cy'] + q['uy'] * h_cf
        fl_h = np.maximum(h_cf - q['ux'] * (fl[:, 0] - cxf) - q['uy'] * (fl[:, 1] - cyf), g['h_ft'])
        cav = mf.Manifold.hull_points(np.r_[np.c_[fl, fl_h], ring(sec(H + 0.01, T), H + 0.01)])
    else:
        d = max(q['dout'], -0.2) * (H - h_tab)
        xa = g['x_min_fix']
        xb = q['cx'] + q['ex']
        if xa is None:
            xa = q['cx'] - q['ex']
            lo_pl = rr_poly(q['cx'], q['cy'], q['ex'] + d, q['ey'] + d, q['r'] + max(d, 0), q['theta'])
        else:
            lo_pl = rr_poly(0.5 * (xa + xb + d), q['cy'], 0.5 * (xb + d - xa), q['ey'] + d, q['r'] + max(d, 0), q['theta'])
        hi_pl = rr_poly(q['cx'], q['cy'], q['ex'], q['ey'], q['r'], q['theta'])
        outer = mf.Manifold.hull_points(np.r_[ring(lo_pl, h_tab), on_top(hi_pl)])

        def inset(hh):
            s = q['s0'] + q['s1'] * (H - hh)
            return rr_poly(q['cx'], q['cy'], q['ex'] - s, q['ey'] - s, max(q['r'] - s, 0.002), q['theta'])
        h_ft = g['h_ft']
        cav = mf.Manifold.hull_points(np.r_[ring(inset(h_ft), h_ft), on_top(inset(H + 0.01), 0.01)])
    if np.isfinite(g['x_clip']):
        cav = cav.trim_by_plane((1.0, 0.0, 0.0), float(g['x_clip']))
    T4 = frame_T4(g['frame'])[:3, :]
    g['outer'] = outer.transform(T4); g['cav'] = cav.transform(T4)
    part.cavity = g['cav']
    part.solid = g['outer'] - g['cav'] if part.params['carve'] == 'self' else g['outer']
    sol_for_resid = g['outer'] - g['cav']
    part.resid = generic_resid(sol_for_resid)
    part.reach = bbox_reach(sol_for_resid)


def tube_face_x(part, side=+1):
    """x (frame) of a 'thin' tube's outer face on the given side at the height of its host's top."""
    q, g = part.geo['q'], part.geo
    H = g.get('H_ref', g['H_med'])
    cx, cy, ex, ey = tube_section(q, g['wall'], H, None)
    return float(cx + side * ex)


# ================================================================================================ cone_array
def fit_cone_array(ctx, idx, spec, done):
    """Rows of tapered round pegs (prim_rack.detect_pegs / fit_peg_row with relative windows): blobs of a horizontal
    slice [slice0, slice1] above the table cut (2-D occupancy, closing), grouped into rows (centre y within row_dy,
    >= 3 pegs); per row one round upright template a(h) (piecewise linear, knots every dh) + per-peg base centres,
    robust least squares; rounded tip at the row's top; rows that do not rise above params.min_top (fraction of s
    above the host's top) are dropped. Standing on the host's floor (params.host, a tube_rrect)."""
    p = spec.get('params', {})
    fr = ctx.frame
    host = done.get(p.get('host')) if p.get('host') else None
    P = ctx.P
    x, y, h = frame_xyh(P, fr)
    inside = np.zeros(len(P), bool); inside[idx] = True
    W = lambda name, mm, floor=0.0: ctx.w(spec, name, rel(mm, S_REF_TUBE, floor))
    sl = (W('slice0', 0.012), W('slice1', 0.035))
    g = W('grid', 0.002)
    row_dy = W('row_dy', 0.012)
    peg_r = W('peg_r', 0.014); h0 = W('h0', 0.002)
    dh = W('dh', 0.006); a0 = W('a0', 0.006)
    a_lo, a_hi = W('a_min', 0.001, 0.0008), W('a_max', 0.020)
    c_m = W('centre_move', 0.008); min_top = W('min_above_host', 0.008); above = W('above_host', 0.002)
    info = {}
    old = dict(PEG_SLICE=PR.PEG_SLICE, PEG_R=PR.PEG_R, PEG_H0=PR.PEG_H0, F_SCALE=PR.F_SCALE)
    PR.PEG_SLICE, PR.PEG_R, PR.PEG_H0, PR.F_SCALE = sl, peg_r, h0, F_SCALE
    try:
        s_ = inside & (h > sl[0]) & (h < sl[1])
        rows = []
        if s_.sum() >= 100:
            x0, y0 = x[s_].min(), y[s_].min()
            i = ((x[s_] - x0) / g).astype(int); j = ((y[s_] - y0) / g).astype(int)
            Hh = np.zeros((i.max() + 1, j.max() + 1)); np.add.at(Hh, (i, j), 1)
            lab, nl = ndimage.label(ndimage.binary_closing(Hh >= 3))
            cents = []
            for qq in range(1, nl + 1):
                ii, jj = np.nonzero(lab == qq)
                if 10 <= len(ii) <= 150:
                    cents.append((x0 + (ii.mean() + 0.5) * g, y0 + (jj.mean() + 0.5) * g))
            if cents:
                cents = np.array(cents)
                order = np.argsort(cents[:, 1]); cur = [order[0]]
                for a_, b_ in zip(order[:-1], order[1:]):
                    if cents[b_, 1] - cents[a_, 1] < row_dy:
                        cur.append(b_)
                    else:
                        rows.append(cur); cur = [b_]
                rows.append(cur)
                rows = [cents[sorted(r, key=lambda k: cents[k, 0])] for r in rows if len(r) >= 3]
        lim_part = done.get(p.get('top_from')) if p.get('top_from') else None
        top_lim = lim_part.geo['H_med'] if lim_part is not None else np.percentile(h[idx], 99.8)
        host_top = host.geo['H_med'] if host is not None else -np.inf
        ok = (inside | (h > host_top + above)) if host is not None else inside
        fits = []
        for cents in rows:
            r = fit_peg_row_rel(x, y, h, cents, ok, top_lim, dh, a0, a_lo, a_hi, c_m)
            if r is not None and r['H_p'] > host_top + min_top:
                fits.append(r)
            elif r is not None:
                info.setdefault('rows_rejected', []).append(dict(n=len(r['xc']), H_p=r['H_p']))
    finally:
        PR.PEG_SLICE, PR.PEG_R, PR.PEG_H0, PR.F_SCALE = old['PEG_SLICE'], old['PEG_R'], old['PEG_H0'], old['F_SCALE']
    h_base = (host.geo['h_ft'] if host is not None else fr['table']) - 0.001
    sol = []
    for r in fits:
        for xc, yc in zip(r['xc'], r['yc']):
            sol.append(PR.peg_solid(r, xc, yc, h_base))
    T4 = frame_T4(fr)
    solid = mf_union(sol)
    if solid is not None:
        solid = solid.transform(T4[:3, :])
    info['rows'] = [dict(n=len(r['xc']), H_p_mm=round(r['H_p'] * 1e3, 1), med_abs_res_mm=round(r['med_abs_res_mm'], 3),
                         a_mm=[round(v * 1e3, 2) for v in r['a']]) for r in fits]
    k = int(sum(len(r['a']) + 2 * len(r['xc']) for r in fits))
    hits = [f'row{j}_a' for j, r in enumerate(fits) if any(abs(v - a_lo) < 1e-7 or abs(v - a_hi) < 1e-7 for v in r['a'])]
    return Part(spec['name'], 'cone_array', solid=solid, params=dict(rows=[len(r['xc']) for r in fits]), k=k,
                bounds_hit=hits, diag=info, geo=dict(rows=fits),
                resid=generic_resid(solid) if solid is not None else None)


def fit_peg_row_rel(x, y, h, cents, ok, top_lim, dh, a0, a_lo, a_hi, c_m):
    """prim_rack.fit_peg_row (round, upright template) with relative windows passed in."""
    tree = cKDTree(np.c_[x, y])
    K = len(cents)
    q = None
    for rnd in range(2):
        pid, idx = [], []
        for k, c in enumerate(cents):
            if q is None:
                nb = np.array(tree.query_ball_point(c, PR.PEG_R + 0.3 * PR.PEG_R), int)
                nb = nb[np.hypot(x[nb] - c[0], y[nb] - c[1]) < PR.PEG_R]
            else:
                cx_, cy_ = q['xc'][k], q['yc'][k]
                nb = np.array(tree.query_ball_point((cx_, cy_), PR.PEG_R * 3.1), int)
                nb = nb[np.hypot(x[nb] - cx_, y[nb] - cy_) < PR.PEG_R]
            nb = nb[ok[nb] & (h[nb] > PR.PEG_H0) & (h[nb] < top_lim)]
            pid.append(np.full(len(nb), k)); idx.append(nb)
        pid = np.concatenate(pid); idx = np.concatenate(idx)
        if len(idx) < 200:
            return None
        hs = h[idx]
        tops = [np.percentile(hs[pid == k], 99) for k in range(K) if (pid == k).sum() > 30]
        if not tops:
            return None
        H_p = float(np.median(tops))
        keep = hs < H_p
        pid, idx, hs = pid[keep], idx[keep], hs[keep]
        if len(idx) > 40000:
            sub = np.random.default_rng(0).choice(len(idx), 40000, replace=False)
            pid, idx, hs = pid[sub], idx[sub], hs[sub]
        xs, ys = x[idx], y[idx]
        knots = np.arange(PR.PEG_H0, H_p + 1e-9, dh)
        if knots[-1] < H_p - 1e-4:
            knots = np.r_[knots, H_p]
        nk = len(knots)
        if q is None:
            p0 = np.r_[np.full(nk, a0), cents[:, 0], cents[:, 1]]
        else:
            p0 = np.r_[np.interp(knots, q['knots'], q['a']), q['xc'], q['yc']]

        def res(qq):
            a = np.maximum(np.interp(hs, knots, qq[:nk]), 0.0008)
            dx = xs - qq[nk + pid]; dy = ys - qq[nk + K + pid]
            return (np.hypot(dx, dy) / a - 1) * a
        lo = np.r_[np.full(nk, a_lo), cents[:, 0] - c_m, cents[:, 1] - c_m]
        hi = np.r_[np.full(nk, a_hi), cents[:, 0] + c_m, cents[:, 1] + c_m]
        qq = least_squares(res, np.clip(p0, lo + 1e-7, hi - 1e-7), bounds=(lo, hi), loss='soft_l1', f_scale=PR.F_SCALE).x
        r_ = res(qq)
        q = dict(knots=knots.tolist(), a=qq[:nk].tolist(), kappa=1.0, u0=0.0, u1=0.0, v0=0.0, v1=0.0, H_p=H_p,
                 xc=qq[nk:nk + K].tolist(), yc=qq[nk + K:].tolist(), n=int(len(idx)),
                 med_abs_res_mm=float(np.median(np.abs(r_)) * 1e3))
    return q


PART_TYPES = dict(lathe=fit_lathe, sheet_of_revolution=fit_sheet_of_revolution, plate=fit_plate,
                  plate_set=fit_plate_set, tube_rrect=fit_tube_rrect, strap=fit_strap, cone_array=fit_cone_array,
                  rounded_box=fit_rounded_box, ball=fit_ball, tsdf_patch=fit_tsdf_patch, splat=fit_splat)
