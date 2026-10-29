"""Part library of the autokit part DSL: parametric parts fitted to OUR observed stereo points (obs_points.py).

GT-free by construction. Every fitter here sees only the observed points of one episode (pts, cam, frame and the
obs_points vote grids, through autokit.io_gt.load_obs), our own library mesh (tsdf_patch only, loaded through the
io_gt guard) and the program's unseen-thickness prior t (generic grid {1.5, 2.5, 4.0} mm). No scan, *_align file,
mocap or parquet pose is read, no number measured on a scan is used, and there are no object names or per-object
constants in this file (stage 1b: the per-object calibration constants S_REF_* and the scan-derived 7 mm marker-ball
prior were removed; the example programs carry their windows explicitly, which is the per-object B side).

Parameter schema. Every part type declares its parameters in PART_TYPES[type].schema (name -> Param: kind, default,
class, meaning). program.validate_program rejects unknown keys, wrong enum values, references to parts that are not
earlier in the list and missing REQUIRED windows; DSL.md's tables are generated from the schema (program.py
--schema-md). Window classes:
  - sensor : resolution / noise scales of OUR stereo points (bins, bands, grids). Generic default, ABSOLUTE metres,
             derived from the sensor constants below (VOX, F_SCALE, APP_D), the same on every object.
  - generic: a rule chosen without any object in mind (e.g. the ball radius window 3-15 mm = 'any small sphere',
             the thickness floor 1.5 mm = the smallest grid value). Absolute default.
  - shape  : depends on the object's shape (flange radii, peg slice heights, plausible extents). NO default: a
             program that uses the window must give it (validation error otherwise). Write it relative to s.
A window value in a program is a bare number (fraction of s), {"frac": f, "floor": m} or {"abs": m}; its value is
max(floor, frac * s) or m, s = robust RMS radius of the object's observed points (Ctx.s).

Part types (fit_<type>(ctx, idx, spec, done) -> Part). Each returns a manifold3d solid (or a mesh patch), its
parameters, the number of free parameters k, the list of parameters that ended on a bound (bounds_hit) and
diagnostics; resid(X) gives how far points X lie OUTSIDE the part (> band: not explained by it), reach(X) how far
they reach beyond its extent (used by the assignment rules in program.py).
  lathe               thin-wall body of revolution; method 'polar' (closed floor, mid-surface +- t/2;
                      prim_potlid.pot_axis/pot_body) or 'height' (open or closed floor; lathe_obs.py)
  sheet_of_revolution domed thin sheet seen from one side (prim_potlid.build_lid): edge circle, tilt, top profile,
                      underside = top - t (prior grid)
  plate               plate in its own fitted plane: outline 'bar' (straight bar with rounded tip, optional hole,
                      inner end inside the host's wall), 'occupancy' (optionally keep_holes) or 'rect'
  plate_set           sequential plane segmentation (one-point RANSAC on camera-oriented normals), one plate per
                      plane-connected inlier set, each clipped to its own inliers
  tube_rrect          drafted, leaning rounded-rectangle tube in the program's support frame; wall 'thin' (thickness
                      t) or 'lip' (inner face inset s0 + s1 (top - h)); point classes by the side they were seen from
  strap               rectangle swept along a centreline fitted in the cluster's best plane (prim_potlid.arch_strap);
                      ends run down to the host surface
  cone_array          rows of tapered round pegs (shared template per row) on blobs of a horizontal slice
  rounded_box         box in the cluster's PCA frame, robust extents, rounded edges
  ball                small spheres kept ONLY where a free sphere fit succeeds inside a generic radius window and
                      passes support tests (frames, cap, residual, convexity, isotropy); stems only where points
                      support them; no fixed-radius fallback; mode 'none' = no balls
  tsdf_patch          faces of our library mesh lying outside the listed parts (hybrid.py / tsdf_parts)
  splat               voxel splat + marching cubes of each assigned cluster (lathe_obs appendages)
  shell_patch         route-A thin shell (shell.surface_patch) over the residual points, trimmed against the union of
                      the earlier parts: observed surface the parts did not explain (A inside B)
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
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
import lathe_obs as L                                     # noqa: E402
import prim_potlid as PL                                  # noqa: E402  (geometry helpers only; not markers_from)
import prim_rack as PR                                    # noqa: E402  (rrect / peg geometry helpers only)
import prim_boards as PB                                  # noqa: E402
import manifold3d as mf                                   # noqa: E402
from autokit import io_gt                                 # noqa: E402

# ------------------------------------------------------------------------------------------------ sensor
VOX = 0.0015          # voxel downsample of the observed points (m), sensor
F_SCALE = 0.002       # robust (soft_l1) loss scale (m), stereo noise scale (our per-frame residual to the
                      # self-consensus is ~0.7-0.8 mm median, refine.py on ep41/ep42, GT-free; 2 mm is generous)
APP_D = 0.008         # residual noise band: a point farther than this outside every part is unexplained (m),
                      # = 4 x F_SCALE
VR = 0.25             # |in-plane view component| that decides outer- vs inner-seen (tube_rrect)
NSEC = 24             # azimuth sectors of the body-of-revolution statistics
MINSEC = 6            # sectors needed for a bin to belong to the body of revolution (handles fill 1-3)
MIN_PTS = 8           # legacy fixed points per (bin, sector) cell (lathe cell_min_pts override only)
CELL_Q = 0.25         # density-normalised cell threshold: a (bin, sector) cell counts as seen when it holds
                      # >= CELL_Q x the median count of the occupied cells (generic: a quarter of a typical cell)
CELL_FLOOR = 3        # ... and at least this many points
NSEG = 64             # revolve segments


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def robust_scale(P):
    """Robust RMS radius s of a point set about its coordinate-wise median (the 2 % farthest points dropped)."""
    c = np.median(P, 0)
    d = np.linalg.norm(P - c, axis=1)
    q = np.quantile(d, 0.98)
    return float(np.sqrt(np.mean(d[d <= q] ** 2))), c


# ------------------------------------------------------------------------------------------------ parameter schema
@dataclass
class Param:
    """One program parameter. kind: window (length, see module doc), int, float, bool, enum, ref (an earlier part's
    name), refs (a name or a list of names). cls (windows): sensor / generic / shape. default None on a window =
    REQUIRED (when `when` matches the spec's params); optional=True: may be omitted, no default (feature off)."""
    kind: str
    default: object = None
    meaning: str = ''
    cls: str = ''
    choices: tuple = ()
    when: dict = None
    optional: bool = False

    def required(self, params, schema):
        if self.kind != 'window' or self.default is not None or self.optional:
            return False
        for k, v in (self.when or {}).items():
            cur = params.get(k, schema[k].default if k in schema else None)
            if (cur not in v) if isinstance(v, (list, tuple)) else (cur != v):
                return False
        return True


def Ws(m, meaning, when=None):                 # sensor window, absolute generic default
    return Param('window', {'abs': m}, meaning, 'sensor', when=when)


def Wg(m, meaning, when=None):                 # generic rule window, absolute default
    return Param('window', {'abs': m}, meaning, 'generic', when=when)


def Wr(meaning, when=None):                    # shape window: required, no default
    return Param('window', None, meaning, 'shape', when=when)


def E(choices, default, meaning):
    return Param('enum', default, meaning, choices=tuple(choices))


class SchemaError(ValueError):
    pass


def window_value(v, s, name='?'):
    """A program's window value -> metres. v: bare number = fraction of s; {'frac': f, 'floor': m}; {'abs': m}."""
    if isinstance(v, dict):
        if 'abs' in v:
            return float(v['abs'])
        return float(max(float(v.get('floor', 0.0)), float(v['frac']) * s))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) * s
    raise SchemaError(f'window {name}: bad value {v!r} (number = fraction of s, {{"frac", "floor"}} or {{"abs"}})')


class Ctx:
    """Per-object fitting context: voxel-downsampled points P, camera centres C, unit view directions V
    (point -> camera), frame ids F, robust scale s, unseen-thickness prior t (required: one of the generic grid
    values), the obs_points arguments (table band) and its vote grids (obs), raw -> downsampled index map inv, the
    optional library mesh path (tsdf_patch) and the program's support frame."""

    def __init__(self, obs, t, lib=None, vox=VOX):
        P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
        F = np.asarray(obs['frame']) if 'frame' in obs else np.zeros(len(P), int)
        key = np.floor(P / vox).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)   # one point per voxel
        self.P, self.C, self.F = P[first], C[first], F[first]
        self.inv = np.asarray(inv).reshape(-1)                         # raw point -> index into self.P
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

    def w(self, spec, name, schema=None):
        """Window `name` of a part spec (params[name]) or of the frame spec (spec[name]) in metres; the default comes
        from the part type's schema; a missing REQUIRED window raises SchemaError."""
        if schema is None:
            schema = PART_TYPES[spec['type']].schema
        pr = schema.get(name)
        if pr is None or pr.kind != 'window':
            raise SchemaError(f'{spec.get("type")}: {name!r} is not a declared window')
        src = spec if schema is FRAME_SCHEMA else spec.get('params', {})
        v = src.get(name)
        if v is None:
            v = pr.default
        if v is None:
            raise SchemaError(f'{spec.get("name", spec.get("type"))}: window {name!r} is required (class {pr.cls}: '
                              f'{pr.meaning}); give it in params, relative to s')
        return window_value(v, self.s, name)

    def p(self, spec, name):
        """Non-window parameter with its schema default."""
        pr = PART_TYPES[spec['type']].schema[name]
        v = spec.get('params', {}).get(name)
        return pr.default if v is None else v

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
def cell_threshold(ctx, spec, keys):
    """Count threshold of a (bin, sector) cell. params.cell_min_pts (int) fixes it (the hand kits used 8); else it is
    density-normalised: max(CELL_FLOOR, cell_q x the median count of the occupied cells, pooled over the key
    arrays given (outer- and inner-seen cells)), so the same object sampled more densely sees the same cells."""
    fixed = ctx.p(spec, 'cell_min_pts')
    if fixed is not None:
        return int(fixed), None
    cnt = np.concatenate([np.unique(k, return_counts=True)[1] for k in keys if len(k)] or [np.zeros(0, int)])
    med = float(np.median(cnt)) if len(cnt) else 0.0
    return max(CELL_FLOOR, int(round(float(ctx.p(spec, 'cell_q')) * med))), med


def axis_search(ctx, P, C, spec, info, n_dirs=600):
    """prim_potlid.pot_axis with relative windows: line-complex placement per direction, score = rim flatness (MAD of
    the per-sector 98th-pct height in the rim window [0.6 R, R + rim_w]) + rotational self-consistency; hemisphere
    search, two local refinements around the three best; lathe_obs.fit_axis's direction is a candidate too."""
    rim_w = ctx.w(spec, 'rim_w')
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
    body_w = ctx.w(spec, 'body_w')
    tmin = ctx.w(spec, 't_min'); tmax = ctx.w(spec, 't_max')
    near_w = ctx.w(spec, 'rim_near')
    ds = ctx.w(spec, 'resample')
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
    xb_ = np.floor((phi - p0) / dphi).astype(int); sb_ = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    ok_ = (xb_ >= 0) & (xb_ < nb)
    cmin, cmed = cell_threshold(ctx, spec, [(xb_ * NSEC + sb_)[ok_ & outer], (xb_ * NSEC + sb_)[ok_ & inner]])
    info.update(cell_min_pts=cmin, cell_median=cmed)
    ro, _ = PL.binned_sector_median(phi, rho, th, outer, p0, dphi, nb, min_pts=cmin)
    ri, _ = PL.binned_sector_median(phi, rho, th, inner, p0, dphi, nb, min_pts=cmin)
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
    if both.sum() >= 3 and ctx.p(spec, 't_src') != 'prior':
        Xin = np.stack([ri[both] * U[both, 0], hO + ri[both] * U[both, 1]], 1)
        t = float(np.median(PL.poly_dist(Qo[np.isfinite(ro)], Xin))); t_src = 'two_sided'
    else:
        t = ctx.t; t_src = 'prior'
    info['t_src_evidence'] = bool(both.sum() >= 3)
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
    dh = ctx.w(spec, 'dh')
    tmin = ctx.w(spec, 't_min')
    body_m = ctx.w(spec, 'body_margin')
    cap_m = ctx.w(spec, 'cap_margin')
    layer = ctx.w(spec, 'floor_layer')
    floor = p.get('floor', 'base')
    gap = int(p.get('gap_bins', 3))
    sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)
    cost, c, d, k = L.fit_axis(P[sub], C[sub], knn=24)
    h, r, th, (e1, e2, d) = L.cyl(P, c, d)
    v = unit(C - P)
    radial = np.stack([np.cos(th), np.sin(th)], 1)
    vr = (v @ e1) * radial[:, 0] + (v @ e2) * radial[:, 1]
    outer, inner = vr > 0.3, vr < -0.3

    hb_ = np.floor((h - h.min()) / dh).astype(int)
    sb_ = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    cmin, cmed = cell_threshold(ctx, spec, [(hb_ * NSEC + sb_)[outer], (hb_ * NSEC + sb_)[inner]])
    info.update(cell_min_pts=cmin, cell_median=cmed)

    def sector_stat(sel):
        hb = np.floor((h - h.min()) / dh).astype(int); nbin = hb.max() + 1
        sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
        out = np.full((nbin, NSEC), np.nan)
        key = hb[sel] * NSEC + sb[sel]; rr = r[sel]
        order = np.argsort(key); key, rr = key[order], rr[order]
        u, start, cnt = np.unique(key, return_index=True, return_counts=True)
        for kk, s0, n in zip(u, start, cnt):
            if n >= cmin:
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
    if vi.sum() >= 3 and ctx.p(spec, 't_src') != 'prior':
        t = float(np.median((r_out - r_in)[vi])); t_src = 'two_sided'
    else:
        t = ctx.t; t_src = 'prior'
    info['t_src_evidence'] = bool(vi.sum() >= 3)
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
    edge_w = ctx.w(spec, 'edge_w')
    fl_r = (ctx.w(spec, 'flange_r0'), ctx.w(spec, 'flange_r1'))
    fl_h = ctx.w(spec, 'flange_h')
    rb_w = ctx.w(spec, 'rbin'); surf_w = ctx.w(spec, 'surf_band')
    r_in = ctx.w(spec, 'tilt_rmin'); tb_w = ctx.w(spec, 'tilt_rbin')
    dr = ctx.w(spec, 'prof_dr')
    rc = (ctx.w(spec, 'dome_r0'), ctx.w(spec, 'dome_r1'))
    ds = ctx.w(spec, 'resample')
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
    edge_out = ctx.w(spec, 'resid_edge')

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
    lb = ctx.w(spec, 'len_bin')
    Tlo = ctx.w(spec, 'T_min'); Thi = ctx.w(spec, 'T_max')
    back = ctx.w(spec, 'inner_search')
    g = ctx.w(spec, 'hole_grid'); hole_a = ctx.w(spec, 'hole_min_d') ** 2
    hole_tip = ctx.w(spec, 'hole_tip')
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
    if side.sum() > 50 and ctx.p(spec, 't_src') != 'prior':
        T = clip_flag('T', float(2 * np.median(btop - b[side])), Tlo, Thi, hits); t_src = 'side'
    else:
        T, t_src = ctx.t, 'prior'
    info['t_src_evidence'] = bool(side.sum() > 50)
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


def mask_polygons_holes(M, lo, grid, hole_min_cells):
    """Outer contour of the largest component of a mask plus its holes (RETR_CCOMP children of at least
    hole_min_cells cells), smoothed as prim_boards.mask_polygon, in (u, v) metres. Returns (outer, [holes])."""
    import cv2
    up = 4
    g = cv2.resize(M.T.astype(np.float32), None, fx=up, fy=up, interpolation=cv2.INTER_NEAREST)
    g = cv2.GaussianBlur(g, (0, 0), PB.SMOOTH_PX * up)
    img = (g > 0.5).astype(np.uint8)
    cs, hier = cv2.findContours(img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if not cs:
        raise RuntimeError('plate: empty outline')
    hier = hier[0]
    outers = [i for i in range(len(cs)) if hier[i][3] < 0]
    io = max(outers, key=lambda i: cv2.contourArea(cs[i]))

    def to_m(c):
        c = cv2.approxPolyDP(c, PB.EPS / grid * up, True)[:, 0, :].astype(float) / up
        return np.stack([lo[0] + c[:, 0] * grid + 0.5 * grid / up, lo[1] + c[:, 1] * grid + 0.5 * grid / up], 1)
    holes = [to_m(cs[i]) for i in range(len(cs)) if hier[i][3] == io and
             cv2.contourArea(cs[i]) / (up * up) >= hole_min_cells]
    return to_m(cs[io]), [hh for hh in holes if len(hh) >= 3]


def clean_mask_holes(M0, close_px, open_px=3, min_frac=0.1):
    """prim_boards.clean_mask without the hole filling: closing (gaps below ~close_px cells close), opening,
    significant components (>= min_frac of the largest)."""
    M = PB._close(M0, close_px)
    M = ndimage.binary_opening(M, structure=PB.disk(open_px))
    lab, nl = ndimage.label(M)
    if nl == 0:
        return M
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1))
    return np.isin(lab, [i + 1 for i in range(nl) if sizes[i] >= min_frac * sizes.max()])


def plane_outline(ctx, P, C, spec, info, hits, mode='occupancy'):
    """prim_boards: plane from camera-oriented PCA normals, thickness from two seen faces (else the prior t),
    occupancy outline (closing, hole fill, opening, significant components, smoothed contour) or its minimum-area
    rectangle, extruded between the two face planes. params.keep_holes: the outline keeps its holes (no hole
    filling; holes of at least hole_min_d diameter-equivalent survive), e.g. a ring handle."""
    grid = ctx.w(spec, 'grid')
    close_mm = ctx.w(spec, 'close')
    n, planar = L.normals(P, C, k=24)
    a, pinfo = PB.fit_plane(P, C, n, planar)
    op, om = pinfo['off_p'], pinfo['off_m']
    two = pinfo['n_face_p'] >= 200 and pinfo['n_face_m'] >= 200 and np.isfinite(op) and np.isfinite(om)
    t_lo, t_hi = ctx.w(spec, 't_min'), ctx.w(spec, 't_max')
    info['t_src_evidence'] = bool(two and t_lo <= op - om <= t_hi)
    if two and t_lo <= op - om <= t_hi and ctx.p(spec, 't_src') != 'prior':
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
        holes = []
        if ctx.p(spec, 'keep_holes') and mode != 'rect':
            M = clean_mask_holes(img >= 1, max(1, int(round(close_mm / grid))))
            if not M.any():
                raise RuntimeError('plate: empty outline')
            hd = ctx.w(spec, 'hole_min_d')
            poly, holes = mask_polygons_holes(M, lo, grid, math.pi / 4 * (hd / grid) ** 2)
        else:
            M, r_used = PB.clean_mask(img >= 1, max(1, int(round(close_mm / grid))))
            if not M.any():
                raise RuntimeError('plate: empty outline')
            poly = PB.rect_polygon(M, lo) if mode == 'rect' else PB.mask_polygon(M, lo)
    finally:
        PB.GRID = old
    cs = mf.CrossSection([poly.astype(np.float64)] + [hh.astype(np.float64) for hh in holes],
                         fillrule=mf.FillRule.EvenOdd)
    info['holes'] = len(holes)
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


def segment_planes(P, n, dist, cos_min, min_pts, max_planes, seeds, conn_vox, rng):
    """Sequential plane segmentation: one-point RANSAC (a seed point and its camera-oriented normal define a plane;
    inliers = points within dist of the plane whose normal is within acos(cos_min) of it, either sign, so both faces
    of a thin plate join), the best seed's plane refitted by PCA of its inliers (2 passes), its inliers split into
    voxel-connected components (conn_vox); every component of >= min_pts points is one plate, clipped to its own
    inliers; the inliers are removed and the search repeats. Returns a list of index arrays (into P), largest first,
    and per-plane info."""
    rem = np.arange(len(P)); out, infos = [], []
    while len(out) < max_planes and len(rem) >= min_pts:
        Pr, nr = P[rem], n[rem]
        best = None
        for i in rng.choice(len(rem), min(seeds, len(rem)), replace=False):
            a = nr[i]; d0 = Pr[i] @ a
            m = (np.abs(Pr @ a - d0) < dist) & (np.abs(nr @ a) > cos_min)
            if best is None or m.sum() > best[2].sum():
                best = (a, d0, m)
        a, d0, m = best
        for _ in range(2):
            Q = Pr[m]; c = Q.mean(0)
            a2 = np.linalg.eigh(np.cov((Q - c).T))[1][:, 0]
            a = a2 if a2 @ a >= 0 else -a2; d0 = float(np.median(Q @ a))
            m = (np.abs(Pr @ a - d0) < dist) & (np.abs(nr @ a) > cos_min)
        if m.sum() < min_pts:
            break
        inl = rem[m]
        comps = [inl[q] for q in PL.clusters(P[inl], vox=conn_vox, min_pts=min_pts)]
        for q in comps:
            if len(out) < max_planes:
                out.append(q); infos.append(dict(n=int(len(q)), normal=np.round(a, 4).tolist()))
        rem = rem[~m]
        if not comps:
            infos.append(dict(n=int(m.sum()), dropped='no connected component >= min_pts'))
    order = np.argsort([-len(q) for q in out])
    return [out[i] for i in order], infos


def fit_plate_set(ctx, idx, spec, done):
    """Several flat plates: the assigned points are segmented by plane (segment_planes; params.segment 'plane') -
    or, legacy, split by voxel connectivity ('cluster') - and each plate is an occupancy (or rect) outline of ITS OWN
    inlier points (plane_outline, optional keep_holes), extruded between its faces."""
    seg = ctx.p(spec, 'segment')
    min_pts = int(ctx.p(spec, 'min_pts')); maxp = int(ctx.p(spec, 'max_plates'))
    P = ctx.P[idx]
    if seg == 'plane':
        n = ctx.normals()[0][idx]
        cl, sinfo = segment_planes(P, n, ctx.w(spec, 'plane_dist'), math.cos(math.radians(float(ctx.p(spec, 'plane_deg')))),
                                   min_pts, maxp, int(ctx.p(spec, 'seeds')), ctx.w(spec, 'conn_vox'),
                                   np.random.default_rng(0))
    else:
        cl = PL.clusters(P, vox=ctx.w(spec, 'conn_vox'), min_pts=min_pts)[:maxp]; sinfo = []
    solids, infos, k = [], [], 0
    for q in cl:
        info, hits = {}, []
        try:
            s_, _, kk = plane_outline(ctx, ctx.P[idx[q]], ctx.C[idx[q]], spec, info, hits,
                                      mode=ctx.p(spec, 'outline'))
            solids.append(s_); k += kk; info['n'] = int(len(q)); infos.append(info)
        except RuntimeError as e:
            infos.append(dict(n=int(len(q)), error=str(e)))
    solid = mf_union(solids)
    return Part(spec['name'], 'plate_set', solid=solid, params=dict(n_plates=len(solids), segment=seg), k=k,
                diag=dict(plates=infos, segmentation=sinfo),
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
    ds = ctx.w(spec, 'len_bin')
    Wlo, Whi = ctx.w(spec, 'W_min'), ctx.w(spec, 'W_max')
    Tlo, Thi = ctx.w(spec, 'T_min'), ctx.w(spec, 'T_max')
    ext = ctx.w(spec, 'end_ext'); rs = ctx.w(spec, 'resample')
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
    if sp.sum() > 30 and ctx.p(spec, 't_src') != 'prior':
        T = clip_flag('T', float(2 * np.median(Hs[sp] - hh[sp])), Tlo, Thi, hits); t_src = 'side'
    else:
        T, t_src = ctx.t, 'prior'
    info['t_src_evidence'] = bool(sp.sum() > 30)
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
def sphere_fit_free(Q):
    """Free sphere fit (no radius prior): algebraic fit, Gauss-Newton on |q - c| - r, then one refit on the inliers
    (|d - r| < max(3 x median, VOX)). Returns (c, r, median |d - r| of the inliers, inlier mask) or None."""
    A = np.c_[2 * Q, np.ones(len(Q))]; b = (Q ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c = sol[:3]; r2 = sol[3] + c @ c
    if not np.isfinite(r2) or r2 <= 0:
        return None
    r = math.sqrt(r2)
    keep = np.ones(len(Q), bool)
    for rnd in range(2):
        for _ in range(10):
            D = Q[keep] - c; dn = np.maximum(np.linalg.norm(D, axis=1), 1e-9)
            J = np.c_[-D / dn[:, None], -np.ones(len(D))]
            step = np.linalg.lstsq(J, -(dn - r), rcond=None)[0]
            c = c + step[:3]; r = r + step[3]
            if not (np.all(np.isfinite(c)) and np.isfinite(r)) or r <= 0:
                return None
        res = np.abs(np.linalg.norm(Q - c, axis=1) - r)
        if rnd == 0:
            keep = res < max(3 * float(np.median(res)), VOX)
            if keep.sum() < 10:
                return None
    return c, float(r), float(np.median(res[keep])), keep


def ball_support(Q, V, F, c, r):
    """GT-free support statistics of a fitted sphere on its observed cap: frames, cap spread (1 - |mean radial
    direction|; a cap of half-angle a gives (1 - cos a) / 2), convexity towards the cameras (share of points whose
    fitted outward normal faces the camera that saw them: a convex cap is visible only from outside, a concave fit
    (the inside of a bowl) faces away),
    isotropy (smaller / larger eigenvalue of the radial directions' tangent spread: rims, pegs and fillets curve in
    one direction only)."""
    u = unit(Q - c); m = u.mean(0); mn = np.linalg.norm(m)
    spread = float(1 - mn)
    convex = float(np.mean(np.einsum('ij,ij->i', u, V) > 0))
    a = m / max(mn, 1e-9)
    T = u - np.outer(u @ a, a)
    ev = np.linalg.eigvalsh(np.cov(T.T))[1:]                  # two tangent eigenvalues (the third ~ 0)
    iso = float(ev[0] / max(ev[1], 1e-12))
    return dict(frames=int(len(np.unique(F))), spread=round(spread, 3), convex=round(convex, 3), iso=round(iso, 3))


def fit_ball(ctx, idx, spec, done):
    """Small spheres on compact residual clusters (no radius prior, no fixed-radius fallback). params.mode 'none'
    gives no balls. Each voxel-connected cluster (>= min_pts, 3..97 % bbox diagonal within [r_min, 3 r_max]; a
    larger cluster is re-clustered once on its points standing more than band + r_min outside the host) gets a FREE
    sphere fit (sphere_fit_free); the ball is kept only if
      r_min <= r <= r_max (generic window 'any small sphere'), median residual <= res_max,
      seen in >= min_frames frames, cap spread >= cap_min, convex (>= convex_min of the points face their camera),
      isotropic (>= iso_min), centre not inside the host (gap >= -r) and ball surface within gap_max of it,
      centre not over a reject_inside part's cavity.
    Stem: a cylinder from the ball to the nearest host surface only where >= stem_min observed points lie in the
    gap within 0.6 r of the stem axis and at least twice as many as in either control cylinder one ball diameter to
    the side; its radius = median distance of those points to the axis, clipped to [VOX, 0.6 r]."""
    p = spec.get('params', {})
    of_names = p.get('of', [])
    of_names = [of_names] if isinstance(of_names, str) else list(of_names)
    of = [done[n] for n in of_names if n in done]
    mode = ctx.p(spec, 'mode')
    if mode == 'none':
        return Part(spec['name'], 'ball', params=dict(n=0, mode='none'), diag=dict(markers=[], note='mode none'))
    min_pts = int(ctx.p(spec, 'min_pts'))
    solids = [q.solid for q in of if q.solid is not None]
    if not solids or len(idx) < min_pts:
        return Part(spec['name'], 'ball', params=dict(n=0, mode=mode), diag=dict(markers=[], note='no residual'))
    rmin, rmax = ctx.w(spec, 'r_min'), ctx.w(spec, 'r_max')
    res_max, gap_max = ctx.w(spec, 'res_max'), ctx.w(spec, 'gap_max')
    cvox = ctx.w(spec, 'cluster_vox')
    band = spec.get('_band', APP_D)
    surf_tm = from_mf(mf_union(solids))
    host_sd = Surf(surf_tm).signed
    pq = trimesh.proximity.ProximityQuery(surf_tm)
    Rp, Rv, Rf = ctx.P[idx], ctx.V[idx], ctx.F[idx]
    rz = [q.resid(Rp) for q in of if q.resid is not None]
    Rz = np.min(rz, axis=0) if rz else np.full(len(Rp), band + 1.0)
    tree = cKDTree(ctx.P)
    cav = done[p['reject_inside']].geo.get('inside_cavity') if p.get('reject_inside') in done else None
    stems_on = bool(ctx.p(spec, 'stems'))
    stem_min = int(ctx.p(spec, 'stem_min'))
    infos, parts, acc = [], [], []
    queue = [(q, 0) for q in PL.clusters(Rp, vox=cvox, min_pts=min_pts)]
    while queue:
        q, level = queue.pop(0)
        Q, V, Fq = Rp[q], Rv[q], Rf[q]
        diag = float(np.linalg.norm(np.percentile(Q, 97, 0) - np.percentile(Q, 3, 0)))
        info = dict(n=int(len(q)), diag_mm=round(diag * 1e3, 1), level=level)
        if not rmin <= diag <= 3 * rmax:
            info['rejected'] = 'size'
            if diag > 3 * rmax and level == 0:
                hi = q[Rz[q] > band + rmin]
                queue += [(hi[j], 1) for j in PL.clusters(Rp[hi], vox=cvox, min_pts=min_pts)] if len(hi) >= min_pts else []
            infos.append(info); continue
        fit = sphere_fit_free(Q)
        if fit is None:
            info['rejected'] = 'no_fit'; infos.append(info); continue
        c, r, res, keep = fit
        sup = ball_support(Q[keep], V[keep], Fq[keep], c, r)
        gap = float(host_sd(c[None])[0]) - r
        info.update(centre=[round(float(x), 4) for x in c], r_mm=round(r * 1e3, 2), res_mm=round(res * 1e3, 2),
                    gap_mm=round(gap * 1e3, 1), **sup)
        why = None
        if not rmin <= r <= rmax:
            why = 'radius'
        elif res > res_max:
            why = 'residual'
        elif sup['frames'] < int(ctx.p(spec, 'min_frames')):
            why = 'frames'
        elif sup['spread'] < float(ctx.p(spec, 'cap_min')):
            why = 'flat_cap'
        elif sup['convex'] < float(ctx.p(spec, 'convex_min')):
            why = 'not_convex'
        elif sup['iso'] < float(ctx.p(spec, 'iso_min')):
            why = 'anisotropic'
        elif not (-r <= gap <= gap_max):
            why = 'gap'
        elif cav is not None and cav(np.asarray(c)[None])[0]:
            why = 'in_cavity'
        if why:
            info['rejected'] = why; infos.append(info); continue
        parts.append(PL.mf_sphere(c, r, seg=24))
        if stems_on and gap > 2 * VOX:
            sp = pq.on_surface(c[None])[0][0]
            ax = unit(sp - c); L_ = float(np.linalg.norm(sp - c)); rs = 0.6 * r

            def stem_pts(a0):
                X = ctx.P[tree.query_ball_point(a0 + 0.5 * L_ * ax, 0.5 * L_ + rs)] - a0
                if len(X) == 0:
                    return np.zeros(0)
                tp = X @ ax; pp = np.linalg.norm(X - tp[:, None] * ax, axis=1)
                return pp[(pp < rs) & (tp > r + 0.5 * VOX) & (tp < L_ - 2 * VOX)]
            pin = stem_pts(c)
            side = unit(np.cross(ax, L.frame_from(ax)[0]))
            n_ctl = max(len(stem_pts(c + (2 * r + rs) * side)), len(stem_pts(c - (2 * r + rs) * side)))
            info.update(stem_pts=int(len(pin)), stem_ctl=int(n_ctl))
            if len(pin) >= stem_min and len(pin) >= 2 * n_ctl:
                sr = float(np.clip(np.median(pin), VOX, rs))
                parts.append(PL.mf_cylinder(c, sp + sr * ax, sr))
                info.update(stem=True, stem_r_mm=round(sr * 1e3, 2))
        infos.append(info); acc.append(info)
    solid = mf_union(parts)
    geo = dict(balls=[(np.asarray(m['centre']), m['r_mm'] * 1e-3) for m in acc])
    return Part(spec['name'], 'ball', solid=solid,
                params=dict(n=len(acc), mode=mode, r_mm=[m['r_mm'] for m in acc],
                            stems=int(sum(1 for m in acc if m.get('stem')))),
                k=4 * len(acc) + int(sum(1 for m in acc if m.get('stem'))), bounds_hit=[], diag=dict(markers=infos),
                geo=geo, resid=generic_resid(solid) if solid is not None else None)


# ================================================================================================ splat / tsdf_patch
def fit_splat(ctx, idx, spec, done):
    """lathe_obs appendages: each voxel-connected cluster (>= min_pts) of the assigned points is splatted on a grid
    (dilation, closing), Gaussian-blurred and meshed by marching cubes. combine 'union' (default: manifold union)
    or 'concat' (kept as a separate mesh, as lathe_obs.py did)."""
    from skimage.measure import marching_cubes
    p = spec.get('params', {})
    vox = ctx.w(spec, 'vox')
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


def load_mesh_guarded(path):
    """Mesh input through the io_gt guard: io_gt.load_mesh (deny-list + allow-listed roots) when it exists; until
    then (stage-1b stand-in) io_gt.check_path (deny-list) before trimesh.load."""
    fn = getattr(io_gt, 'load_mesh', None)
    if fn is not None:
        return fn(path)
    io_gt.check_path(path)
    return trimesh.load(path, force='mesh')


def fit_tsdf_patch(ctx, idx, spec, done):
    """Faces of our own library mesh (ctx.lib, same object frame) whose centres lie outside every part in
    params.of by more than params.margin (default APP_D): the hand kits' 'tsdf' variant. Not watertight; the
    program concatenates it after the union."""
    p = spec.get('params', {})
    if not ctx.lib:
        raise RuntimeError('tsdf_patch needs the library mesh path (run_program(..., lib=...))')
    src = load_mesh_guarded(ctx.lib)
    margin = ctx.w(spec, 'margin')
    of = p.get('of', [])
    of = [done[n] for n in ([of] if isinstance(of, str) else of) if n in done]
    X = src.triangles_center
    dist = np.min([q.resid(X) for q in of if q.resid is not None], axis=0) if of else np.full(len(X), np.inf)
    keep = dist > margin
    app = src.submesh([np.nonzero(keep)[0]], append=True) if keep.any() else None
    return Part(spec['name'], 'tsdf_patch', mesh=app, params=dict(faces=int(keep.sum())), diag=dict(faces=int(keep.sum())))


# ================================================================================================ shell_patch
def surface_patch_standin(obs, idx=None, t=0.0025, max_faces=None, host=None, voxel=0.002):
    """LOCAL STAND-IN for shell.surface_patch (stage-1b API contract) while the shell fixer's version does not exist:
    shell.thin_shell over obs['pts'][idx]; with a host mesh, every body of the shell whose surface lies mostly
    (>= 50 % of 2000 samples) within 2 voxels outside the host, or inside it, is dropped (it would duplicate the
    host's surface). Same signature and return type as the contract."""
    from autokit import shell as SH
    idx = np.arange(len(obs['pts'])) if idx is None else np.asarray(idx)
    sub = dict(pts=np.asarray(obs['pts'])[idx], cam=np.asarray(obs['cam'])[idx],
               frame=np.asarray(obs['frame'])[idx] if 'frame' in obs else np.zeros(len(idx), int))
    m = SH.thin_shell(sub, t=t, voxel=voxel, max_faces=max_faces or SH.MAX_FACES)
    if host is not None and len(m.faces):
        sd = Surf(host, n=100000).signed
        keep = [b for b in m.split(only_watertight=False)
                if np.mean(sd(trimesh.sample.sample_surface(b, 2000, seed=0)[0]) > 2 * voxel) >= 0.5]
        m = trimesh.util.concatenate(keep) if keep else trimesh.Trimesh()
    return m


def fit_shell_patch(ctx, idx, spec, done):
    """Observed surface the earlier parts did not explain (route A inside a part program): the assigned points
    (default rule: the residual of every earlier part), reduced to their voxel-connected clusters of >= min_pts,
    mapped back to the raw observed points, go to shell.surface_patch (a closed thin shell of thickness t over them,
    trimmed so it does not duplicate the host = union of the parts in params.of, default all earlier parts).
    Until shell.surface_patch exists, surface_patch_standin is used (reported as diag.impl)."""
    p = spec.get('params', {})
    of = p.get('of') or list(done)
    of = [of] if isinstance(of, str) else list(of)
    hp = [done[n] for n in of if n in done]
    sol = mf_union([q.solid for q in hp if q.solid is not None])
    hm = [from_mf(sol)] if sol is not None else []
    hm += [q.mesh for q in hp if q.mesh is not None and len(q.mesh.faces)]
    host = trimesh.util.concatenate(hm) if hm else None
    cl = PL.clusters(ctx.P[idx], vox=ctx.w(spec, 'cluster_vox'), min_pts=int(ctx.p(spec, 'min_pts'))) if len(idx) else []
    info = dict(n_assigned=int(len(idx)), clusters=len(cl))
    if not cl:
        return Part(spec['name'], 'shell_patch', params=dict(n_pts=0), diag=dict(info, note='no residual cluster'))
    keep = np.zeros(len(ctx.P), bool); keep[idx[np.concatenate(cl)]] = True
    raw = np.nonzero(keep[ctx.inv])[0]
    try:
        from autokit import shell as SH
        fn = getattr(SH, 'surface_patch', None)
    except ImportError:
        fn = None
    info['impl'] = 'shell.surface_patch' if fn is not None else 'parts.surface_patch_standin'
    mf_ = ctx.p(spec, 'max_faces')
    mesh = (fn or surface_patch_standin)(ctx.obs, idx=raw, t=ctx.t, max_faces=int(mf_) if mf_ else None, host=host)
    info.update(n_raw=int(len(raw)), n_vox=int(keep.sum()))
    if mesh is None or len(mesh.faces) == 0:
        return Part(spec['name'], 'shell_patch', params=dict(n_pts=int(keep.sum()), faces=0), diag=dict(info, note='empty patch'))
    info.update(faces=int(len(mesh.faces)), area_cm2=round(float(mesh.area) * 1e4, 2), watertight=bool(mesh.is_watertight))
    solid = None
    if mesh.is_watertight:
        try:
            solid = to_mf(mesh)
        except RuntimeError as e:
            info['mf_error'] = str(e)
    return Part(spec['name'], 'shell_patch', solid=solid, mesh=None if solid is not None else mesh,
                params=dict(n_pts=int(keep.sum()), faces=int(len(mesh.faces)), area_cm2=info['area_cm2']),
                k=0, diag=info, resid=Surf(mesh).signed, reach=None)


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
    cell = ctx.w(spec, 'cell', FRAME_SCHEMA); band = ctx.w(spec, 'band', FRAME_SCHEMA)
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
        h_ft = H_med - ctx.w(spec, 'floor_depth'); table = h_ft - t
        info['floor_depth_mm'] = round((H_med - h_ft) * 1e3, 2)
    elif host is not None and 'h_ft' in host.geo:
        table, h_ft = host.geo['h_tab'], host.geo['h_ft']
    nup = ctx.normals()[0][idx] @ fr['up']
    if wall == 'thin':
        sd = rr_sd(q, x, y, *tube_section(q, wall, h, None)[2:], *tube_section(q, wall, h, None)[:2])[0]
        below = host.geo['H_med'] if host is not None else top_c[0]
        fl = (sd < -t - ctx.w(spec, 'floor_in')) & (nup > 0.85) & (h < below) & (h > h_ft)
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
    W = lambda name: ctx.w(spec, name)
    table = fr['table']; h_ft = table + t
    if host is not None and 'h_ft' in host.geo:                # stand on the host's floor plate
        table, h_ft = host.geo['h_tab'], host.geo['h_ft']
    rng = np.random.default_rng(0)
    x_min_fix = (fr['tall'][0] - t) if (p.get('x_min_from') == 'tall_lo' and fr.get('tall')) else None
    use = np.ones(len(P), bool)
    if x_min_fix is not None:
        use = x > fr['tall'][1] + W('skip_end')
    if wall == 'lip':
        # ---- top plane through lip-top samples along the outline edges (not the fixed end)
        tl = x > fr['tall'][1] + W('skip_lip') if x_min_fix is not None else np.ones(len(P), bool)
        ylo, yhi = np.percentile(y[tl], [1, 99]); xhi = np.percentile(x[tl], 99)
        eb, sg_w = W('edge_band'), W('top_seg')
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
            m = np.abs(rr - np.median(rr[m])) < W('top_robust')
        info['top_plane'] = dict(a_mm=round(top_c[0] * 1e3, 2), slope_x=round(top_c[1], 4), slope_y=round(top_c[2], 4),
                                 n=int(m.sum()))
        xs0 = x[use]; ys0 = y[use]
        ylo, yhi = np.percentile(ys0, [1, 99]); xhi = np.percentile(xs0, 99.5)
        xa = x_min_fix if x_min_fix is not None else np.percentile(xs0, 0.5)
        q = dict(cx=0.5 * (xa + xhi), cy=0.5 * (ylo + yhi), ux=0.0, uy=0.0, ex=0.5 * (xhi - xa), ey=0.5 * (yhi - ylo),
                 fx=0.0, fy=0.0, r=W('r0'), theta=0.0, s0=W('s0_init'), s1=0.3, dout=0.0)
        free = ['cx', 'cy', 'theta', 'dout', 'ey', 'r', 's0', 's1']
        if x_min_fix is None:
            free.insert(4, 'ex')
        else:
            free.insert(4, 'ex')                          # ex free, cx tied so the -x end stays at x_min_fix
        lo = dict(cx=-np.inf, cy=-np.inf, theta=-0.2, dout=-0.3, ex=W('e_min'), ey=W('e_min'),
                  r=W('r_min'), s0=W('s0_min'), s1=0.0)
        hi = dict(cx=np.inf, cy=np.inf, theta=0.2, dout=1.0, ex=W('e_max') * 10, ey=W('e_max'),
                  r=W('r_max'), s0=W('s0_max'), s1=1.5)
    else:
        H_host = host.geo['H_med'] if host is not None else -np.inf
        bw = W('flat_band')
        tops = [np.percentile(h[(y >= a) & (y < a + bw)], 99) for a in np.arange(np.percentile(y, 2), np.percentile(y, 98), bw)
                if ((y >= a) & (y < a + bw) & (h > H_host)).sum() > 30]
        H_med = float(np.median(tops))
        top_c = np.array([H_med, 0.0, 0.0])
        tall = h > (H_host + W('init_above') if host is not None else np.percentile(h, 50))
        xl, xh = np.percentile(x[tall], [1, 99]); yl, yh = np.percentile(y[tall], [1, 99])
        q = dict(cx=0.5 * (xl + xh), cy=0.5 * (yl + yh), ux=0.0, uy=0.0, ex=0.5 * (xh - xl), ey=0.5 * (yh - yl),
                 fx=0.0, fy=0.0, r=W('r0'), theta=0.0, s0=t, s1=0.0, dout=0.0)
        lean = float(p.get('lean_max', 0.25)) if p.get('lean', True) else 1e-6
        free = ['cx', 'cy', 'ux', 'uy', 'ex', 'ey', 'fx', 'fy', 'r']
        lo = dict(cx=-np.inf, cy=-np.inf, ux=-lean, uy=-lean, ex=W('ex_min'), ey=W('ey_min'),
                  fx=-lean, fy=-lean, r=W('r_min'))
        hi = dict(cx=np.inf, cy=np.inf, ux=lean, uy=lean, ex=W('ex_max'), ey=W('ey_max'),
                  fx=lean, fy=lean, r=W('r_max'))
    lo_v = np.array([lo[n] for n in free]); hi_v = np.array([hi[n] for n in free])

    def unpack(z):
        qq = dict(q); qq.update({n: float(v) for n, v in zip(free, z)})
        if x_min_fix is not None and wall == 'lip':
            qq['cx'] = x_min_fix + qq['ex']
        return qq
    Ht = top_c[0] + top_c[1] * x + top_c[2] * y
    gate = W('class_gate')
    n_it = int(p.get('iters', 4 if wall == 'lip' else 5))
    for it in range(n_it):
        cx, cy, ex, ey = tube_section(q, wall, h, Ht)
        sd, gx, gy = rr_sd(q, x, y, ex, ey, cx, cy)
        vr = vx * gx + vy * gy
        if wall == 'lip':
            s_h = q['s0'] + q['s1'] * (Ht - h)
            near = use & (sd > -W('near_in')) & (sd < W('near_out'))
            outer = near & (h > W('low')) & (h < Ht - W('below_top')) & (vr > VR) & \
                (np.abs(sd - q['dout'] * (Ht - h)) < gate)
            inner = near & (h > W('low_in')) & (h < Ht - W('below_top')) & (vr < -VR) & \
                (np.abs(sd + s_h) < gate)
            rim = near & (h > Ht - W('lip_below')) & (h < Ht + W('lip_above')) & \
                (sd > -W('lip_in')) & (sd < W('lip_out'))
        else:
            near = (np.abs(sd) < W('near')) & (h < H_med + W('top_above'))
            upper = h > H_host + W('host_band')
            vert = np.abs(nup) < 0.7
            outer = near & upper & (vr > VR) & (sd > -W('out_in')) & (h < H_med - W('rim_band'))
            inner = near & upper & (vr < -VR) & (sd < W('in_out')) & (h < H_med - W('rim_band')) & vert
            if it >= 2 and host is not None:
                inner |= (near & ~upper & (h > h_ft + W('host_band')) & (vr < -VR) & vert &
                          (sd < -t + W('in_out')) & (sd > -t - gate))
            rim = near & (h >= H_med - W('rim_band'))
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
    W = lambda name: ctx.w(spec, name)
    sl = (W('slice0'), W('slice1'))
    g = W('grid')
    row_dy = W('row_dy')
    peg_r = W('peg_r'); h0 = W('h0')
    dh = W('dh'); a0 = W('a0')
    a_lo, a_hi = W('a_min'), W('a_max')
    c_m = W('centre_move'); min_top = W('min_above_host'); above = W('above_host')
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


# ================================================================================================ schema
T_SRC = E(('auto', 'prior'), 'auto', "thickness source: 'auto' = measured where both faces (or the side) were seen, "
          "else the prior t; 'prior' = always the prior t (program.variants() emits this as the t-grid variant)")
REFS_OF = Param('refs', None, 'earlier part(s) whose surface is the host (a name or a list)')
PLATE_OUTLINE = dict(
    grid=Ws(0.0015, 'occupancy cell of the outline (= VOX)', when={'outline': ('occupancy', 'rect')}),
    close=Ws(0.003, 'closing scale of the occupancy mask (2 x VOX)', when={'outline': ('occupancy', 'rect')}),
    t_min=Wg(0.003, 'smallest two-face thickness accepted as measured (carried from prim_boards)', when={'outline': ('occupancy', 'rect')}),
    t_max=Wg(0.025, 'largest two-face thickness accepted as measured (carried from prim_boards)', when={'outline': ('occupancy', 'rect')}),
    keep_holes=Param('bool', False, 'occupancy outline keeps its holes (no hole filling): rings, handles with a hole'),
    hole_min_d=Ws(0.006, 'smallest hole kept (equivalent diameter; 2 x the closing scale); bar: smallest tip hole'),
    t_src=T_SRC)


@dataclass
class PartType:
    fit: object
    schema: dict
    models: str = ''
    see: str = ''
    k: str = ''

    def __call__(self, ctx, idx, spec, done):
        return self.fit(ctx, idx, spec, done)


PART_TYPES = dict(
    lathe=PartType(fit_lathe, dict(
        method=E(('polar', 'height'), 'polar', "'polar': closed floor, profile in polar coordinates about an interior "
                 "point, robust hemisphere axis search; 'height': per-height-bin profile, open end from inner-wall evidence"),
        floor=E(('base', 'observed', 'solid', 'open'), 'base', "height method: 'base' closed (cavity to base + t), "
                "'observed' cavity only as deep as the inner wall was seen (GLOBAL RULE ONLY, never a per-object pick "
                "motivated by scan coverage), 'solid' no cavity, 'open' bottomless ring"),
        thick=Param('float', 1.0, 'polar: multiplier on the wall thickness (sensitivity runs only)'),
        dphi_deg=Param('float', 2.0, 'polar: angular profile bin (deg)'),
        gap_bins=Param('int', 3, "height, floor 'observed': bins of missing inner wall tolerated"),
        nseg=Param('int', 96, 'height: revolve segments'),
        t_src=T_SRC,
        cell_q=Param('float', CELL_Q, 'density-normalised cell threshold: fraction of the median occupied-cell count'),
        cell_min_pts=Param('int', None, 'fixed (bin, sector) cell threshold instead (hand kits: 8); omit = density-normalised', optional=True),
        rim_w=Wr('axis search: rim window beyond the body radius', when={'method': 'polar'}),
        body_w=Wr('profile: body points within the 60th-pct radius + body_w', when={'method': 'polar'}),
        t_min=Wg(0.0015, 'smallest wall thickness (= smallest grid value)'),
        t_max=Wr('largest measured wall thickness accepted (clip)', when={'method': 'polar'}),
        rim_near=Ws(APP_D, 'points within this of the mid-surface define the rim height', when={'method': 'polar'}),
        resample=Ws(0.003, 'profile resampling step', when={'method': 'polar'}),
        dh=Ws(0.003, 'height bin', when={'method': 'height'}),
        body_margin=Ws(0.005, 'body points: radius below the outer profile max + margin', when={'method': 'height'}),
        cap_margin=Ws(0.003, 'floor points lie inside the inner radius by this', when={'method': 'height'}),
        floor_layer=Ws(0.010, 'spread (q10-q90) below which floor points form one observed layer', when={'method': 'height'})),
        'thin-walled body of revolution (open containers, bowls, bottles)', 'round in every view, rim or opening',
        '5 + profile knots'),
    sheet_of_revolution=PartType(fit_sheet_of_revolution, dict(
        thick=Param('float', 1.0, 'multiplier on the prior t of the unseen underside'),
        edge_w=Ws(0.003, 'per-sector edge band (98th-pct radius minus edge_w)'),
        flange_r0=Wr('inner radius of the flat annulus used to refit the normal'),
        flange_r1=Wr('outer radius of that annulus'),
        flange_h=Ws(0.006, 'height band of the annulus points'),
        rbin=Ws(0.002, 'radius bin of the first-pass surface'),
        surf_band=Ws(0.004, 'points within this of the surface are surface points'),
        tilt_rmin=Wr('tilt refinement uses radii above this'),
        tilt_rbin=Ws(0.004, 'radius bin of the tilt refinement'),
        prof_dr=Ws(0.002, 'radius bin of the top profile'),
        dome_r0=Wr('inner radius of the ring the near-axis quadratic dome is fitted on'),
        dome_r1=Wr('outer radius of that ring'),
        resample=Ws(0.003, 'profile resampling step'),
        resid_edge=Wr('band beyond the edge radius in which points are this part\'s business')),
        'domed cover or dish seen from one side', 'flat round thing, underside never seen', '5 + knots'),
    plate=PartType(fit_plate, dict(
        outline=E(('bar', 'occupancy', 'rect'), 'bar', "'bar' straight bar with rounded tip and optional hole; "
                  "'occupancy' traced outline; 'rect' minimum-area rectangle"),
        host=Param('ref', None, "bar: the body whose wall the bar starts inside"),
        hole=Param('bool', True, 'bar: look for a hole near the tip'),
        len_bin=Ws(0.005, 'bar: length bin of the width profile', when={'outline': 'bar'}),
        T_min=Wg(0.0015, 'bar: smallest measured thickness (= smallest grid value)', when={'outline': 'bar'}),
        T_max=Wr('bar: largest measured thickness accepted (clip)', when={'outline': 'bar'}),
        inner_search=Wr('bar: how far behind the inner end the host wall is searched', when={'outline': 'bar'}),
        hole_grid=Ws(0.002, 'bar: occupancy cell of the hole search', when={'outline': 'bar'}),
        hole_tip=Wr('bar: a hole must lie within this of the tip', when={'outline': 'bar'}),
        **PLATE_OUTLINE),
        'flat piece in its own plane', 'handles, fins, flat slabs', '9 (bar), 5 + 2 x vertices'),
    plate_set=PartType(fit_plate_set, dict(
        segment=E(('plane', 'cluster'), 'plane', "'plane': sequential plane segmentation; 'cluster': voxel connectivity (legacy)"),
        outline=E(('occupancy', 'rect'), 'occupancy', 'outline of each plate'),
        min_pts=Param('int', 300, 'points of a plate'),
        max_plates=Param('int', 4, 'largest number of plates'),
        seeds=Param('int', 200, 'RANSAC seeds per plane'),
        plane_deg=Param('float', 30.0, 'normal tolerance of a plane inlier (deg, either sign)'),
        plane_dist=Ws(0.003, 'distance tolerance of a plane inlier (2 x VOX)'),
        conn_vox=Ws(0.003, 'voxel connectivity of a plate\'s inliers'),
        **{k: (Param(v.kind, v.default, v.meaning, v.cls) if k in ('grid', 'close', 't_min', 't_max') else v)
           for k, v in PLATE_OUTLINE.items()}),
        'several flat plates (sides of a box, a scoop)', 'flat sheets meeting at edges', 'sum of plates'),
    strap=PartType(fit_strap, dict(
        host=Param('ref', None, 'the sheet / body the strap ends run down into'),
        t_src=T_SRC,
        len_bin=Ws(0.003, 'length bin of the top curve'),
        W_min=Wr('smallest strap width (clip)'), W_max=Wr('largest strap width (clip)'),
        T_min=Wg(0.0015, 'smallest measured thickness (= smallest grid value)'), T_max=Wr('largest measured thickness (clip)'),
        end_ext=Ws(0.004, 'extension of the ends beyond the last top-seen bin'),
        resample=Ws(0.002, 'centreline resampling step')),
        'rectangle swept along a fitted centreline', 'arched handle over a cover, bucket handle', '2 + knots'),
    tube_rrect=PartType(fit_tube_rrect, dict(
        wall=E(('thin', 'lip'), 'thin', "'thin': wall thickness t, lean / draft / corner free; 'lip': thick rim s0, "
               "inner face sloping by s1, outer face leaning by dout, top = robust plane"),
        above=Param('ref', None, 'thin: host tube whose top hides this tube\'s lower outer face'),
        x_min_from=E((None, 'tall_lo'), None, "'tall_lo': the -x end is fixed at the frame's tall region"),
        align_frame=Param('bool', True, 'lip: re-express the program frame in the fitted outline frame'),
        carve=E((None, 'self', 'all'), None, "'self' (default for lip) or 'all' (default for thin)"),
        lean=Param('bool', True, 'thin: lean and draft free'), lean_max=Param('float', 0.25, 'thin: lean / draft bound'),
        iters=Param('int', None, 'robust-fit rounds (default 4 lip, 5 thin)', optional=True),
        floor_depth=Param('window', None, 'development only: floor plate at this depth below the top', 'shape', optional=True),
        r0=Wr('initial corner radius'), r_min=Wr('corner radius lower bound'), r_max=Wr('corner radius upper bound'),
        class_gate=Ws(APP_D, 'point-class gate around the current surface'),
        skip_end=Wr('points within this beyond the tall region are not used (x_min_from)', when={'x_min_from': 'tall_lo'}),
        skip_lip=Wr('lip-top samples start this far beyond the tall region', when={'wall': 'lip', 'x_min_from': 'tall_lo'}),
        edge_band=Wr('lip: band along the outline edges for top samples', when={'wall': 'lip'}),
        top_seg=Ws(0.010, 'lip: segment length of the top samples', when={'wall': 'lip'}),
        top_robust=Ws(0.003, 'lip: inlier band of the top plane', when={'wall': 'lip'}),
        s0_init=Wr('lip: initial rim width', when={'wall': 'lip'}),
        e_min=Wr('lip: smallest half extent', when={'wall': 'lip'}), e_max=Wr('lip: largest half extent (y; x: 10x)', when={'wall': 'lip'}),
        s0_min=Wr('lip: smallest rim width', when={'wall': 'lip'}), s0_max=Wr('lip: largest rim width', when={'wall': 'lip'}),
        near_in=Wr('lip: points this far inside the outline are near', when={'wall': 'lip'}),
        near_out=Wr('lip: points this far outside the outline are near', when={'wall': 'lip'}),
        low=Ws(0.003, 'lip: outer-class points above this height', when={'wall': 'lip'}),
        below_top=Ws(0.006, 'lip: wall classes end this far below the top', when={'wall': 'lip'}),
        low_in=Ws(0.006, 'lip: inner-class points above this height', when={'wall': 'lip'}),
        lip_below=Ws(0.003, 'lip: top class from this far below the top', when={'wall': 'lip'}),
        lip_above=Ws(0.004, 'lip: ... to this far above it', when={'wall': 'lip'}),
        lip_in=Wr('lip: top class reaches this far inside the outline', when={'wall': 'lip'}),
        lip_out=Ws(0.006, 'lip: ... and this far outside it', when={'wall': 'lip'}),
        flat_band=Wr('thin: y band of the robust top height', when={'wall': 'thin'}),
        init_above=Wr('thin: initial outline from points this far above the host top', when={'wall': 'thin'}),
        ex_min=Wr('thin: smallest half extent x', when={'wall': 'thin'}), ex_max=Wr('thin: largest half extent x', when={'wall': 'thin'}),
        ey_min=Wr('thin: smallest half extent y', when={'wall': 'thin'}), ey_max=Wr('thin: largest half extent y', when={'wall': 'thin'}),
        near=Wr('thin: points within this of the surface are near', when={'wall': 'thin'}),
        top_above=Ws(0.004, 'thin: near points up to this above the top', when={'wall': 'thin'}),
        host_band=Ws(0.004, 'thin: band above the host top', when={'wall': 'thin'}),
        out_in=Ws(0.006, 'thin: outer class reaches this far inside', when={'wall': 'thin'}),
        in_out=Ws(0.003, 'thin: inner class reaches this far outside', when={'wall': 'thin'}),
        rim_band=Ws(0.003, 'thin: rim class within this below the top', when={'wall': 'thin'}),
        floor_in=Ws(0.004, 'thin: raised-floor points lie inside the inner face by this', when={'wall': 'thin'})),
        'rounded-rectangle tube in the support frame', 'trays, holders, open boxes standing on the table', '9-13'),
    cone_array=PartType(fit_cone_array, dict(
        host=Param('ref', None, 'the tray (tube_rrect) whose floor the pegs stand on'),
        top_from=Param('ref', None, 'part whose top height limits the pegs'),
        slice0=Wr('lower height of the detection slice'), slice1=Wr('upper height of the detection slice'),
        grid=Ws(0.002, 'occupancy cell of the slice'), row_dy=Wr('pegs within this in y form a row'),
        peg_r=Wr('point radius around a peg centre'), h0=Ws(0.002, 'lowest knot height'),
        dh=Ws(0.006, 'knot spacing of the row template'), a0=Wr('initial peg radius'),
        a_min=Wr('smallest peg radius'), a_max=Wr('largest peg radius'),
        centre_move=Wr('largest peg-centre move'), min_above_host=Wr('rows must rise this far above the host top'),
        above_host=Ws(0.002, 'points this far above the host top count for the pegs')),
        'rows of tapered round pegs, one template per row', 'peg rows standing in a tray', 'knots + 2 x pegs'),
    rounded_box=PartType(fit_rounded_box, dict(
        pct=Param('float', 1.0, 'robust extent percentile'), r_frac=Param('float', 0.2, 'edge radius / smallest half extent')),
        'box with rounded edges in the PCA frame', 'blocks, bricks', '10'),
    ball=PartType(fit_ball, dict(
        mode=E(('free', 'none'), 'free', "'free': balls only where a free sphere fit passes every test; 'none': no balls"),
        of=REFS_OF, reject_inside=Param('ref', None, 'tube whose cavity footprint must not hold a ball centre'),
        stems=Param('bool', True, 'stems where points support them'),
        min_pts=Param('int', 25, 'points of a cluster (a 3 mm hemisphere cap holds ~25 voxels of 1.5 mm)'),
        min_frames=Param('int', 3, 'frames a ball must be seen in (one mis-tracked frame cannot make a ball)'),
        cap_min=Param('float', 0.08, 'cap spread 1 - |mean radial| (half-angle >= ~33 deg)'),
        convex_min=Param('float', 0.8, 'share of cap points whose fitted outward normal faces their camera'),
        iso_min=Param('float', 0.25, 'tangent spread isotropy (rims, pegs, fillets curve one way only)'),
        stem_min=Param('int', 15, 'observed points in the stem cylinder'),
        r_min=Wg(0.003, "smallest radius ('any small sphere'; generic, not from any scan)"),
        r_max=Wg(0.015, "largest radius ('any small sphere'; generic, not from any scan)"),
        res_max=Ws(0.0015, 'largest median |d - r| of the fit (= VOX)'),
        gap_max=Wg(0.030, 'largest ball-surface to host-surface gap (= 2 r_max)'),
        cluster_vox=Ws(0.003, 'voxel connectivity of the residual clusters')),
        'small spheres (markers) on optional stems', 'small round knobs / grey spheres on short stems', '4 per ball (+1 per stem)'),
    tsdf_patch=PartType(fit_tsdf_patch, dict(
        of=REFS_OF, margin=Ws(APP_D, 'library faces farther than this outside every listed part are kept')),
        'faces of OUR library TSDF mesh outside the listed parts', 'fallback for parts we cannot model', '0'),
    splat=PartType(fit_splat, dict(
        vox=Ws(0.002, 'splat voxel'), min_pts=Param('int', 400, 'points of a splatted cluster'),
        combine=E(('union', 'concat'), 'union', "'union' (watertight) or 'concat' (separate mesh)")),
        'voxel splat + marching cubes of each large cluster', 'anything irregular the vocabulary lacks', '0'),
    shell_patch=PartType(fit_shell_patch, dict(
        of=Param('refs', None, 'host parts the patch must not duplicate (default: every earlier part)'),
        min_pts=Param('int', 100, 'points of a residual cluster that gets a patch'),
        cluster_vox=Ws(0.003, 'voxel connectivity of the residual clusters'),
        max_faces=Param('int', None, 'face cap of the patch (shell default)', optional=True)),
        'route-A thin shell over observed surface the parts did not explain', 'leftover observed pieces after the parts',
        '0'),
)

FRAME_SCHEMA = dict(
    type=E(('support',), 'support', 'the only frame type: table support frame'),
    tall_end=Param('bool', True, 'flip x so the end holding the tall points lies at -x'),
    tall_frac=Param('float', 0.65, 'tall points: h > tall_frac x the 99.8 % height'),
    cell=Ws(0.010, 'cell of the lower supporting plane fit'),
    band=Ws(0.003, 'inlier band of the lower supporting plane'))
