#!/usr/bin/env python
"""Family C primitive assembly: plastic_dish_rack fitted to OUR observed stereo points (obs_points.py), no GT.

Pre-registered round 2026-10-27 (docs/work-log.md). This code never reads the scans, *_align.npz, mocap or parquet
poses; its only inputs are obs_points.py npz files (pts, cam, frame, args) in the object (track) frame.

What the points show (all five public episodes, 12/13/26/27/31; the rack is static and seen from one side):
  - no point lies within table_band (obs_points --table_band, 8 mm) of the table: the lowest points of every wall
    and peg end on one plane (the "cut"); the tray floor is never observed (it lies below the cut);
  - a long shallow tray (rounded-rectangle outline): outer face of the front wall (camera side), a rounded lip
    ~8 mm wide, and a SLOPED inner face (back wall, right end) that meets the floor ~20 mm inside the outline;
  - two rows of six tapered pegs (~15 mm wide at the base, ~55 mm tall);
  - a tall open cup holder at one end (rounded-rectangle tube, it leans and flares towards the back), with a
    raised inner floor;
  - grey marker balls on short stems.
Model (rack frame: up = normal of the lower supporting plane of the points (the cut), x = long axis, y = width,
h = height above the cut; table at h = -table_band):
  1. Tray block = rounded-rectangle prism from the table to the lip height H_r, minus the basin: a frustum whose
     outline is the block outline inset by s(h) = s0 + s1 (H_r - h) (s0 = lip width), from the floor top
     h_ft = table + T_WALL up; the basin ends at the cup holder's outer face. Outline, s0, s1 by one robust
     least-squares fit to three point classes chosen by the side they were seen from (camera centre per point):
     outer-face points (sd = 0), inner-face points (sd = -s(h)), lip points (sd = -s0/2).
  2. Cup holder = rounded-rectangle tube, lean and draft linear in h (CUP_LEAN; else straight upright), wall T_WALL; outer
     points sd = 0, inner points sd = -T_WALL, rim points sd = -T_WALL/2; top = robust top height; inner floor =
     up-facing points inside the cavity (else the tray floor).
  3. Pegs: blobs of a mid-height slice inside the basin, grouped into rows; per row one tapered cone template,
     round and upright (PEG_KAPPA = 1, PEG_LEAN = False; half-widths a(h) along x and y) and per-peg
     base centres, robust least squares on the pooled peg points; rounded tip at the row's top height.
  4. Marker balls: compact residual clusters outside the body (prim_potlid.markers_from: sphere fit with the 7 mm
     prior from our own stereo, gap/size/residual tests, stem only when points support it); kept only with a
     curved cap (marker_parts) and not centred over the basin (markers sit on the exterior).
  All parts are unioned with manifold3d (watertight, no hidden internal faces).
T_WALL is a prior for the moulded wall / floor thickness (PRIM_T_WALL, default 2.5 mm); the never-seen floor is a plate
of that thickness lying on the table. The 2.5 mm of the first run came from a brief that quoted the scan-measured rack
wall (leak, work log 2026-10-27); the clean-up round tests 1.5 / 2.5 / 4.0 mm and both cup-lean settings.

Variants (<= 4 for the family; all parameters shared by every episode):
  full  : per-episode fit, all parts + markers
  nomk  : per-episode fit, no marker balls (ablation)
  joint : the consistent episodes' points (own 'full' fidelity <= JOINT_TOL x the best) rigidly aligned to a
          reference episode (trimmed point-to-point ICP on the observed points), one fit on the merged points, the mesh then moved to the mean of the episode frames
          (so no single track frame is preferred); markers from the merged points
  joint_nomk : joint without markers
Usage:
  prim_rack.py build OBS.npz OUT_PREFIX [--variants full,nomk]          (one episode)
  prim_rack.py joint OBS1.npz,OBS2.npz,... OUT_PREFIX                   (joint, joint_nomk)
  prim_rack.py run --obs_dir DIR --out OUT [--episodes 12,13,26,27,31]   (all candidates + GT-free selection)
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import trimesh
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lathe_obs import normals                              # noqa: E402
import prim_potlid as PL                                    # noqa: E402
import manifold3d as mf                                     # noqa: E402

OBJ = 'plastic_dish_rack'
VOX = 0.0015            # voxel downsample of the observed points (m)
T_WALL = float(os.environ.get('PRIM_T_WALL', 0.0025))   # moulded wall / floor thickness prior (see docstring)
CELL = 0.01             # lower-envelope cell (m)
VR = 0.25               # |in-plane view component| that decides outer- vs inner-seen
F_SCALE = 0.002         # robust loss scale (m)
PEG_SLICE = (0.012, 0.035)   # peg detection slice (m above the cut)
PEG_R = 0.014           # peg point radius around a peg centre (m)
PEG_H0 = 0.002          # lowest peg knot (m above the cut)
PEG_KAPPA = 1.0         # peg section depth / width (prior: round pegs; the back of a peg is never seen)
PEG_LEAN = False        # pegs perpendicular to the floor: a free lean came out 0.04-0.4 (2-22 deg) between
                        # episodes and rows (stereo smear behind thin pegs), so it is not evidence
APP_D = 0.008           # residual for markers: farther than this outside the body (prim_potlid.APP_D)
MK_FREE_R = (4.0, 12.0)  # marker: free sphere-fit radius range (mm) that counts as a ball
MK_SPREAD = 0.05        # marker: or a cap this curved (1 - |mean direction| from the centre)
SEG = 6                 # segments per rounded corner
S0_MIN = 0.004          # lip width lower bound (the lip tops seen from above span ~7-9 mm)
CUP_LEAN = os.environ.get('PRIM_CUP_LEAN', '1') == '1'   # default True: cup-holder lean and draft free (linear in h).
                        # The first run used False (upright) after a [D] scan diagnostic (leak, work log 2026-10-27);
                        # in the clean-up round obs_fidelity (GT-free) preferred the free lean at every T_WALL
                        # (1.5/2.5/4.0 mm: 6.044/5.935/5.921 vs 6.242/6.116/6.138 mm), so the default follows it
JOINT_TOL = 1.25        # joint fit: episodes whose own fit has fidelity <= JOINT_TOL x the best
# C0b options (PREREG cdo-sprint/C0b 3.2, 3.3; main() sets them): --t_wall replaces T_WALL everywhere, --s0_min_t sets
# S0_MIN = T_WALL, --markers_dir replaces the marker path (markers_from, marker_parts, in_basin) by the gmg
# markers.py balls of each episode (<dir>/ep<N>.json) attached by markers.attach. Unset = the behaviour above.
GMG_MK = None           # dict(dir=..., sha=...) when --markers_dir is given
C0B_USED = {}


# ------------------------------------------------------------------------------------------------ io / frame
def load(path, vox=VOX):
    Z = np.load(path)
    P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    F = Z['frame'] if 'frame' in Z.files else np.zeros(len(P), int)
    band = float(json.loads(str(Z['args'])).get('table_band', 0.008)) if 'args' in Z.files else 0.008
    key = np.floor(P / vox).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    first = np.sort(first)
    return P[first], C[first], F[first], band


def lower_plane(P, up, cs=CELL, iters=4):
    """Lower supporting plane of the points: per (cs x cs) cell the 2nd-percentile height, then a plane fitted to
    the lowest 30 % of cells + 3 mm (iterated); up re-estimated from the plane. Returns (up, offset)."""
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
            idx = o[s0:s0 + c]
            low.append(idx[np.argsort(h[idx])[max(0, int(0.02 * c))]])
        low = np.array(low)
        A = np.c_[y[low], z[low], np.ones(len(low))]; hl = h[low]
        coef = np.linalg.lstsq(A, hl, rcond=None)[0]
        for _ in range(10):
            r = hl - A @ coef; m = r < np.percentile(r, 30) + 0.003
            coef = np.linalg.lstsq(A[m], hl[m], rcond=None)[0]
        n = up - coef[0] * a - coef[1] * b; s = np.linalg.norm(n); up = n / s; off = coef[2] / s
    return up, off


def initial_frame(P, C, up_fixed=None):
    X = P - P.mean(0)
    V = np.linalg.eigh(np.cov(X.T))[1]
    up = V[:, 0]
    if np.mean((C - P) @ up) < 0:
        up = -up
    up, off = lower_plane(P, up)
    if up_fixed is not None:                       # joint fit: the episodes' mean cut normal; offset re-measured
        up = up_fixed / np.linalg.norm(up_fixed)
        h = P @ up
        a = np.eye(3)[np.argmin(np.abs(up))]; a = a - (a @ up) * up; a /= np.linalg.norm(a); b = np.cross(up, a)
        key = np.floor(P @ a / CELL).astype(np.int64) * 100000 + np.floor(P @ b / CELL).astype(np.int64)
        o_ = np.argsort(key, kind='stable'); _, st, cnt = np.unique(key[o_], return_index=True, return_counts=True)
        low = np.array([np.percentile(h[o_[s0:s0 + n]], 2) for s0, n in zip(st, cnt) if n >= 20])
        off = float(np.percentile(low, 15))
    Q = P - np.outer(P @ up, up)
    L = np.linalg.eigh(np.cov((Q - Q.mean(0)).T))[1][:, -1]
    L = L - (L @ up) * up; L /= np.linalg.norm(L)
    w = np.cross(up, L)
    if np.mean(C @ w) > np.mean(P @ w):          # cameras on the -y (front) side
        L, w = -L, -w
        w = np.cross(up, L)
    o = P.mean(0); o = o - (o @ up) * up + off * up
    return dict(up=up, L=L, w=w, o=o)


def to_rack(P, fr):
    X = P - fr['o']
    return X @ fr['L'], X @ fr['w'], X @ fr['up']


def rotate_frame(fr, theta, dx=0.0, dy=0.0):
    """New frame whose x axis is rotated by theta (about up) and origin shifted by (dx, dy) in the old frame."""
    c, s = math.cos(theta), math.sin(theta)
    L = c * fr['L'] + s * fr['w']; w = np.cross(fr['up'], L)
    o = fr['o'] + dx * fr['L'] + dy * fr['w']
    return dict(up=fr['up'], L=L, w=w, o=o)


# ------------------------------------------------------------------------------------------------ 2-D shapes
def rrect_sd(px, py, hx, hy, r):
    """Signed distance to a rounded rectangle centred at 0 (half extents hx, hy, corner radius r) and its gradient."""
    r = np.minimum(r, np.minimum(hx, hy) - 1e-4)
    qx = np.abs(px) - (hx - r); qy = np.abs(py) - (hy - r)
    ox = np.maximum(qx, 0); oy = np.maximum(qy, 0); out = np.hypot(ox, oy)
    sd = out + np.minimum(np.maximum(qx, qy), 0) - r
    inside = out <= 0
    gx = np.where(inside, (qx >= qy).astype(float), ox / np.maximum(out, 1e-12)) * np.sign(px + 1e-15)
    gy = np.where(inside, (qy > qx).astype(float), oy / np.maximum(out, 1e-12)) * np.sign(py + 1e-15)
    return sd, gx, gy


def rrect_poly(cx, cy, hx, hy, r, seg=SEG):
    """Counter-clockwise rounded-rectangle polygon (N, 2)."""
    r = float(np.clip(r, 1e-4, min(hx, hy) - 1e-4))
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (hx - r), cy + sy * (hy - r)
        for k in range(seg + 1):
            t = math.radians(a0 + 90 * k / seg)
            pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    return np.array(pts)


def view_inplane(P, C, fr, gx, gy):
    """In-plane component of the unit view direction (point -> camera) along the outward 2-D normal (gx, gy)."""
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    return (v @ fr['L']) * gx + (v @ fr['w']) * gy


# ------------------------------------------------------------------------------------------------ fits
def find_cup(x, y, h):
    """The cup holder = the end holding the tall points (h > 0.65 x the 99.8 % height). Returns its x range and
    whether it lies at +x (then the frame is flipped by the caller)."""
    top = np.percentile(h, 99.8)
    tall = h > 0.65 * top
    lo, hi = np.percentile(x[tall], [1, 99])
    xmin, xmax = np.percentile(x, [0.5, 99.5])
    return lo, hi, (lo + hi) / 2 > (xmin + xmax) / 2


def lip_tops(x, y, h, x0):
    """Lip-top samples: tray points within 12 mm of the bounding box edges (front, back, right end; the cup end is
    left out), per 1 cm segment the 98 % height at the segment's median (x, y). Returns (N, 3) array."""
    t = x > x0
    ylo, yhi = np.percentile(y[t], [1, 99]); xhi = np.percentile(x[t], 99)
    out = []
    for m, coord in (((y < ylo + 0.012) & t, x), ((y > yhi - 0.012) & t, x), ((x > xhi - 0.012) & t, y)):
        if m.sum() < 50:
            continue
        seg = np.floor(coord[m] / 0.01).astype(int)
        xm, ym, hm = x[m], y[m], h[m]
        for s_ in np.unique(seg):
            k = seg == s_
            if k.sum() >= 30:
                out.append((np.median(xm[k]), np.median(ym[k]), np.percentile(hm[k], 98)))
    return np.array(out)


def rim_height(x, y, h, x0):
    """Lip height H_r: median of the lip-top samples."""
    return float(np.median(lip_tops(x, y, h, x0)[:, 2]))


def lip_plane(x, y, h, x0):
    """Plane h = a + b x + c y through the lip-top samples, robust (3 mm). Returns ((a, b, c), inliers, sd mm).
    The lip height differs between the front, back and right end by a few mm, differently per episode (table-cut
    tilt and view-dependent lip tops), so the lip is modelled as this plane rather than one height."""
    T = lip_tops(x, y, h, x0)
    A = np.c_[np.ones(len(T)), T[:, 0], T[:, 1]]
    m = np.ones(len(T), bool)
    for _ in range(5):
        coef = np.linalg.lstsq(A[m], T[m, 2], rcond=None)[0]
        r = T[:, 2] - A @ coef
        m = np.abs(r - np.median(r[m])) < 0.003
    return coef, int(m.sum()), float(np.std(r[m]) * 1e3)


def fit_outline(P, C, x, y, h, fr, x0, xa, lipc, info):
    """Tray outline (right end xb, centre line cy, angle, half width hy, corner radius) and inner-face profile
    s(h) = s0 + s1 (H_r - h); outer face sd = so1 (H_r - h) (so1 > 0: the outer face leans in going up). The left
    end xa is the cup holder's (fixed here): the cup holder replaces the tray's left wall, so only points with
    x > x0 + 30 mm enter. Point classes by viewing side: outer face sd = so1 (H_r - h), inner face sd = -s(h),
    lip sd = -s0 / 2. Returns [xb, cy, theta, so1, hy, rc, s0, s1]."""
    t = x > x0 + 0.03
    ylo, yhi = np.percentile(y[t], [1, 99]); xhi = np.percentile(x[t], 99.5)
    p = np.array([xhi, 0.5 * (ylo + yhi), 0.0, 0.0, 0.5 * (yhi - ylo), 0.015, 0.008, 0.3])
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True); vx, vy = v @ fr['L'], v @ fr['w']

    def geom(p, xs, ys):
        xb, cy, th, _, hy, r = p[:6]
        cx, hx = 0.5 * (xa + xb), 0.5 * (xb - xa)
        c, s = math.cos(th), math.sin(th)
        X = c * (xs - cx) + s * (ys - cy); Y = -s * (xs - cx) + c * (ys - cy)
        sd, gx, gy = rrect_sd(X, Y, hx, hy, r)
        return sd, c * gx - s * gy, s * gx + c * gy
    H_r = lipc[0] + lipc[1] * x + lipc[2] * y                 # local lip height of every point
    for it in range(4):
        sd, gx, gy = geom(p, x, y)
        vr = vx * gx + vy * gy
        s_h = p[6] + p[7] * (H_r - h)
        near = t & (sd > -0.035) & (sd < 0.015)
        outer = near & (h > 0.003) & (h < H_r - 0.006) & (vr > VR) & (np.abs(sd - p[3] * (H_r - h)) < 0.008)
        inner = near & (h > 0.006) & (h < H_r - 0.006) & (vr < -VR) & (np.abs(sd + s_h) < 0.008)
        lip = near & (h > H_r - 0.003) & (h < H_r + 0.004) & (sd > -0.02) & (sd < 0.006)
        # the outline's left end is the cup holder: do not let points near x0 pull the left edge
        cls = np.r_[np.zeros(outer.sum()), np.ones(inner.sum()), 2 * np.ones(lip.sum())].astype(int)
        idx = np.r_[np.nonzero(outer)[0], np.nonzero(inner)[0], np.nonzero(lip)[0]]
        if len(idx) > 60000:
            sub = np.random.default_rng(it).choice(len(idx), 60000, replace=False); idx, cls = idx[sub], cls[sub]
        xs, ys, hs, Hs = x[idx], y[idx], h[idx], H_r[idx]

        def res(q):
            sdq = geom(q, xs, ys)[0]
            target = np.where(cls == 0, q[3] * (Hs - hs), np.where(cls == 1, -(q[6] + q[7] * (Hs - hs)), -0.5 * q[6]))
            return sdq - target
        lo = [-np.inf, -np.inf, -0.2, -0.3, 0.03, 0.002, S0_MIN, 0.0]
        hi = [np.inf, np.inf, 0.2, 1.0, 0.15, 0.06, 0.03, 1.5]
        p = least_squares(res, np.clip(p, np.array(lo) + 1e-6, np.array(hi) - 1e-6), bounds=(lo, hi),
                          loss='soft_l1', f_scale=F_SCALE).x
    r_ = res(p)
    info['outline'] = dict(cx=0.5 * (xa + p[0]), cy=p[1], theta_deg=math.degrees(p[2]), hx=0.5 * (p[0] - xa), hy=p[4],
                           rc=p[5], s0=p[6], s1=p[7], so1=p[3], n_outer=int(outer.sum()), n_inner=int(inner.sum()), n_lip=int(lip.sum()),
                           med_abs_res_mm=float(np.median(np.abs(r_)) * 1e3),
                           res_by_class_mm=[float(np.median(np.abs(r_[cls == k])) * 1e3) if (cls == k).any() else None
                                            for k in range(3)])
    return p


def cup_lsq(P, n, x, y, h, fr, reg, H_r, h_ft, top, p, geom, vx, vy):
    """Free tube (lean and draft linear in h): robust LSQ on outer / inner / rim point classes."""
    for it in range(5):
        sd, gx, gy = geom(p, x, y, h)
        vr = vx * gx + vy * gy
        near = reg & (np.abs(sd) < 0.012) & (h < top + 0.004)
        upper = h > H_r + 0.004
        vert = np.abs(n @ fr['up']) < 0.7
        outer = near & upper & (vr > VR) & (sd > -0.006) & (h < top - 0.003)
        inner = near & upper & (vr < -VR) & (sd < 0.003) & (h < top - 0.003) & vert
        if it >= 2:
            # below the tray lip only the cavity's own inner faces (inside the current tube, near its inner face)
            inner |= (near & ~upper & (h > h_ft + 0.004) & (vr < -VR) & vert & (sd < -T_WALL + 0.003)
                      & (sd > -T_WALL - 0.008))
        rim = near & (h >= top - 0.003)
        cls = np.r_[np.zeros(outer.sum()), np.ones(inner.sum()), 2 * np.ones(rim.sum())].astype(int)
        idx = np.r_[np.nonzero(outer)[0], np.nonzero(inner)[0], np.nonzero(rim)[0]]
        if len(idx) > 60000:
            sub = np.random.default_rng(it).choice(len(idx), 60000, replace=False); idx, cls = idx[sub], cls[sub]
        xs, ys, hs = x[idx], y[idx], h[idx]
        tgt = np.where(cls == 0, 0.0, np.where(cls == 1, -T_WALL, -0.5 * T_WALL))

        def res(q):
            return geom(q, xs, ys, hs)[0] - tgt
        lean = 0.25 if CUP_LEAN else 1e-6           # upright: no lean and no draft (a straight tube)
        lo = [-np.inf, -np.inf, -lean, -lean, 0.01, 0.01, -lean, -lean, 0.004]
        hi = [np.inf, np.inf, lean, lean, 0.08, 0.12, lean, lean, 0.05]
        p = least_squares(res, np.clip(p, np.array(lo) + 1e-6, np.array(hi) - 1e-6), bounds=(lo, hi),
                          loss='soft_l1', f_scale=F_SCALE).x
    return p, res(p), cls


def cup_upright(P, n, x, y, h, fr, reg, H_r, top, p0, geom, vx, vy):
    """Upright straight tube from one robust statistic per side (above the lip, below the rim): left wall
    inner face (+x-facing, seen through the opening), right wall outer face (+x-facing, towards the tray), front
    wall outer face (-y-facing), back wall inner face (-y-facing); a seen inner face is moved out by T_WALL. Corner
    radius by a 1-D search of the robust residual. Every face the camera can see faces -y or +x here."""
    band = reg & (h > H_r + 0.005) & (h < top - 0.005)
    cx0, cy0 = p0[0], p0[1]
    nx, ny = n @ fr['L'], n @ fr['w']
    side = lambda m: float(np.median(m)) if len(m) > 30 else None
    xl = side(x[band & (x < cx0 - 0.01) & (nx > 0.8)])          # left inner face
    xr = side(x[band & (x > cx0 + 0.01) & (nx > 0.8)])          # right outer face
    yf = side(y[band & (y < cy0 - 0.02) & (ny < -0.8)])         # front outer face
    yb = side(y[band & (y > cy0 + 0.02) & (ny < -0.8)])         # back inner face
    xl = xl - T_WALL if xl is not None else p0[0] - p0[4]
    xr = xr if xr is not None else p0[0] + p0[4]
    yf = yf if yf is not None else p0[1] - p0[5]
    yb = yb + T_WALL if yb is not None else p0[1] + p0[5]
    p = np.array([0.5 * (xl + xr), 0.5 * (yf + yb), 0, 0, 0.5 * (xr - xl), 0.5 * (yb - yf), 0, 0, 0.02])
    sel = band & (np.abs(n @ fr['up']) < 0.7)
    best = None
    for r in np.arange(0.004, min(p[4], p[5]) - 0.001, 0.002):
        p[8] = r
        sd, gx, gy = geom(p, x[sel], y[sel], h[sel])
        vr = vx[sel] * gx + vy[sel] * gy
        e = np.where(vr > 0, sd, sd + T_WALL)
        e = e[np.abs(e) < 0.012]
        c = float(np.mean(np.minimum(np.abs(e), 0.004)))
        if best is None or c < best[0]:
            best = (c, r)
    p[8] = best[1]
    sd, gx, gy = geom(p, x[sel], y[sel], h[sel])
    vr = vx[sel] * gx + vy[sel] * gy
    r_ = np.where(vr > 0, sd, sd + T_WALL); r_ = r_[np.abs(r_) < 0.012]
    return p, r_, np.zeros(len(r_), int)


def fit_cup(P, C, n, x, y, h, fr, xr, H_r, h_ft, info):
    """Cup holder tube: centre (cx, cy) + h (ux, uy), half extents (ex, ey) + h (fx, fy), corner radius r (upright
    straight tube unless CUP_LEAN); top = median over 2 cm bands of the 99 % height; inner floor."""
    reg = x < xr + 0.012
    hc = h[reg]
    top = float(np.median([np.percentile(hc[(y[reg] >= a) & (y[reg] < a + 0.02)], 99)
                           for a in np.arange(np.percentile(y[reg], 2), np.percentile(y[reg], 98), 0.02)
                           if ((y[reg] >= a) & (y[reg] < a + 0.02) & (hc > H_r)).sum() > 30]))
    tall = reg & (h > H_r + 0.01)
    xl, xh = np.percentile(x[tall], [1, 99]); yl, yh = np.percentile(y[tall], [1, 99])
    p = np.array([0.5 * (xl + xh), 0.5 * (yl + yh), 0, 0, 0.5 * (xh - xl), 0.5 * (yh - yl), 0, 0, 0.02])
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True); vx, vy = v @ fr['L'], v @ fr['w']

    def geom(q, xs, ys, hs):
        cx = q[0] + q[2] * hs; cy = q[1] + q[3] * hs; ex = q[4] + q[6] * hs; ey = q[5] + q[7] * hs
        return rrect_sd(xs - cx, ys - cy, ex, ey, q[8])
    if not CUP_LEAN:
        p, r_, cls = cup_upright(P, n, x, y, h, fr, reg, H_r, top, p, geom, vx, vy)
    else:
        p, r_, cls = cup_lsq(P, n, x, y, h, fr, reg, H_r, h_ft, top, p, geom, vx, vy)
    # inner floor: up-facing points inside the cavity, below the lip
    sd = geom(p, x, y, h)[0]
    fl = reg & (sd < -T_WALL - 0.004) & (n @ fr['up'] > 0.85) & (h < H_r) & (h > h_ft)
    h_cf = float(np.median(h[fl])) if fl.sum() >= 50 else h_ft
    info['cup'] = dict(cx=p[0], cy=p[1], ux=p[2], uy=p[3], ex=p[4], ey=p[5], fx=p[6], fy=p[7], r=p[8], top=top,
                       h_cf=h_cf, n_floor=int(fl.sum()), n_fit=int(len(r_)), med_abs_res_mm=float(np.median(np.abs(r_)) * 1e3),
                       res_by_class_mm=[float(np.median(np.abs(r_[cls == k])) * 1e3) if (cls == k).any() else None
                                        for k in range(3)])
    return p, top, h_cf


def detect_pegs(x, y, h, inside, info, g=0.002):
    """Peg centres: blobs (>= 3 points per 2 mm cell, area 40-600 mm^2) of the PEG_SLICE slice inside the basin;
    rows = groups of centres whose y differ by < 12 mm (>= 3 pegs)."""
    s = inside & (h > PEG_SLICE[0]) & (h < PEG_SLICE[1])
    if s.sum() < 100:
        return []
    x0, y0 = x[s].min(), y[s].min()
    i = ((x[s] - x0) / g).astype(int); j = ((y[s] - y0) / g).astype(int)
    H = np.zeros((i.max() + 1, j.max() + 1)); np.add.at(H, (i, j), 1)
    lab, nl = ndimage.label(ndimage.binary_closing(H >= 3))
    cents = []
    for q in range(1, nl + 1):
        ii, jj = np.nonzero(lab == q)
        if 10 <= len(ii) <= 150:
            cents.append((x0 + (ii.mean() + 0.5) * g, y0 + (jj.mean() + 0.5) * g))
    if not cents:
        return []
    cents = np.array(cents)
    order = np.argsort(cents[:, 1]); rows, cur = [], [order[0]]
    for a, b in zip(order[:-1], order[1:]):
        if cents[b, 1] - cents[a, 1] < 0.012:
            cur.append(b)
        else:
            rows.append(cur); cur = [b]
    rows.append(cur)
    rows = [sorted(r, key=lambda k: cents[k, 0]) for r in rows if len(r) >= 3]
    info['pegs_detected'] = [[[round(float(v), 4) for v in cents[k]] for k in r] for r in rows]
    return [cents[r] for r in rows]


def fit_peg_row(x, y, h, cents, ok, top_lim, dh=0.006):
    """One leaning round-section template per row + per-peg base centres. Shape: radius a(h) piecewise linear
    over knots every dh from PEG_H0 to the row's top H_p (a flared base, a taper), centre offset (u0 + u1 h,
    v0 + v1 h) (lean; fixed at 0 unless PEG_LEAN). Only the camera side of a peg is ever seen, so the section shape is a prior (round,
    PEG_KAPPA = 1: a free depth/width ratio trades off against the lean and was unstable across episodes).
    Two passes: points within PEG_R of the vertical line through each centre, then of the fitted leaning axis."""
    tree = cKDTree(np.c_[x, y])
    K = len(cents)
    q = None
    for rnd in range(2):
        pid, idx = [], []
        for k, c in enumerate(cents):
            if q is None:
                nb = np.array(tree.query_ball_point(c, PEG_R + 0.004), int)
                nb = nb[np.hypot(x[nb] - c[0], y[nb] - c[1]) < PEG_R]
            else:
                cx_, cy_ = q['xc'][k], q['yc'][k]
                nb = np.array(tree.query_ball_point((cx_, cy_), PEG_R + 0.03), int)
                ax = cx_ + q['u0'] + q['u1'] * h[nb]; ay = cy_ + q['v0'] + q['v1'] * h[nb]
                nb = nb[np.hypot(x[nb] - ax, y[nb] - ay) < PEG_R]
            nb = nb[ok[nb] & (h[nb] > PEG_H0) & (h[nb] < top_lim)]
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
        knots = np.arange(PEG_H0, H_p + 1e-9, dh)
        if knots[-1] < H_p - 1e-4:
            knots = np.r_[knots, H_p]
        nk = len(knots)
        if q is None:
            p0 = np.r_[np.full(nk, 0.006), 0, 0, 0, 0, cents[:, 0], cents[:, 1]]
        else:
            p0 = np.r_[np.interp(knots, q['knots'], q['a']), q['u0'], q['u1'], q['v0'], q['v1'], q['xc'], q['yc']]

        def res(qq):
            a = np.maximum(np.interp(hs, knots, qq[:nk]), 0.0008); b = PEG_KAPPA * a
            dx = xs - qq[nk + 4 + pid] - (qq[nk] + qq[nk + 1] * hs)
            dy = ys - qq[nk + 4 + K + pid] - (qq[nk + 2] + qq[nk + 3] * hs)
            return (np.hypot(dx / a, dy / b) - 1) * np.sqrt(a * b)
        lean = 0.4 if PEG_LEAN else 1e-6
        lo = np.r_[np.full(nk, 0.001), -1e-6, -lean, -1e-6, -lean, cents[:, 0] - 0.008, cents[:, 1] - 0.008]
        hi = np.r_[np.full(nk, 0.02), 1e-6, lean, 1e-6, lean, cents[:, 0] + 0.008, cents[:, 1] + 0.008]
        qq = least_squares(res, np.clip(p0, lo + 1e-7, hi - 1e-7), bounds=(lo, hi), loss='soft_l1',
                           f_scale=F_SCALE).x
        r_ = res(qq)
        q = dict(knots=knots.tolist(), a=qq[:nk].tolist(), kappa=PEG_KAPPA, u0=float(qq[nk]), u1=float(qq[nk + 1]),
                 v0=float(qq[nk + 2]), v1=float(qq[nk + 3]), H_p=H_p, xc=qq[nk + 4:nk + 4 + K].tolist(),
                 yc=qq[nk + 4 + K:].tolist(), n=int(len(idx)), med_abs_res_mm=float(np.median(np.abs(r_)) * 1e3))
    return q


# ------------------------------------------------------------------------------------------------ geometry
def prism(poly, z0, z1):
    cs = mf.CrossSection([poly.astype(np.float64)])
    return mf.Manifold.extrude(cs, float(z1 - z0)).translate((0.0, 0.0, float(z0)))


def hull(points):
    return mf.Manifold.hull_points(np.asarray(points, np.float64))


def rings(polys_h):
    return np.concatenate([np.c_[pl, np.full(len(pl), hh)] for pl, hh in polys_h])


def build_body(geo):
    """Watertight rack body (tray block - basin + cup tube - cavity + pegs) in rack coordinates (x, y, h)."""
    o, cup = geo['outline'], geo['cup']
    h_tab, h_ft, H_r = geo['h_tab'], geo['h_ft'], geo['H_r']
    # tray block: rounded-rectangle frustum from the cup holder's outer left end to the right end; the outer face
    # leans by so1 (outline at the lip height H_r, expanded by so1 (H_r - h) below it; the left end stays at xa)
    xa = o['xa']
    xb = o['cx'] + o['hx']
    d = max(o['so1'], -0.2) * (H_r - h_tab)
    blk_lo = rrect_poly(0.5 * (xa + xb + d), o['cy'], 0.5 * (xb + d - xa), o['hy'] + d, o['rc'] + max(d, 0))
    blk_hi = rrect_poly(0.5 * (xa + xb), o['cy'], 0.5 * (xb - xa), o['hy'], o['rc'])
    lipc = geo['lipc']

    def on_lip(pl, dz=0.0):
        return np.c_[pl, lipc[0] + lipc[1] * pl[:, 0] + lipc[2] * pl[:, 1] + dz]
    body = hull(np.r_[np.c_[blk_lo, np.full(len(blk_lo), h_tab)], on_lip(blk_hi)])
    # basin: frustum of the outline inset by s(h), cut at the cup holder's outer face
    def inset(hh):
        s = o['s0'] + o['s1'] * (H_r - hh)
        return rrect_poly(o['cx'], o['cy'], o['hx'] - s, o['hy'] - s, max(o['rc'] - s, 0.002))
    htop = H_r + 0.01
    basin = hull(np.r_[np.c_[inset(h_ft), np.full(len(inset(h_ft)), h_ft)], on_lip(inset(htop), 0.01)])
    xr = geo['x_cup_face']
    basin = basin.trim_by_plane((1.0, 0.0, 0.0), float(xr))
    body = body - basin
    # cup holder tube (outer hull) and cavity
    def cup_poly(hh, d):
        return rrect_poly(cup['cx'] + cup['ux'] * hh, cup['cy'] + cup['uy'] * hh, cup['ex'] + cup['fx'] * hh - d,
                          cup['ey'] + cup['fy'] * hh - d, max(cup['r'] - d, 0.002))
    top = cup['top']
    tube = hull(rings([(cup_poly(h_tab, 0), h_tab), (cup_poly(top, 0), top)]))
    # cavity floor perpendicular to the tube axis (ux, uy, 1) through the observed floor height at the centre
    fl = cup_poly(cup['h_cf'], T_WALL)
    cxf, cyf = cup['cx'] + cup['ux'] * cup['h_cf'], cup['cy'] + cup['uy'] * cup['h_cf']
    fl_h = cup['h_cf'] - cup['ux'] * (fl[:, 0] - cxf) - cup['uy'] * (fl[:, 1] - cyf)
    fl_h = np.maximum(fl_h, h_ft)
    cav = hull(np.r_[np.c_[fl, fl_h], rings([(cup_poly(top + 0.01, T_WALL), top + 0.01)])])
    parts = [body, tube]
    # pegs
    for row in geo['pegs']:
        for xc, yc in zip(row['xc'], row['yc']):
            parts.append(peg_solid(row, xc, yc, h_ft - 0.001))
    U = mf.Manifold.batch_boolean(parts, mf.OpType.Add)
    U = U - cav
    return U


def peg_solid(row, xc, yc, h0, nseg=16):
    """Convex hull of the template's elliptic rings at its knots (the lowest ring repeated down to h0, inside the
    floor), with a rounded tip: ring at H_p - a(H_p), apex at H_p."""
    kn, av = np.asarray(row['knots']), np.asarray(row['a'])
    H = row['H_p']

    def ring(hh):
        a = max(float(np.interp(hh, kn, av)), 0.0008); b = max(row['kappa'] * a, 0.0008)
        t = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
        cx = xc + row['u0'] + row['u1'] * hh; cy = yc + row['v0'] + row['v1'] * hh
        return np.c_[cx + a * np.cos(t), cy + b * np.sin(t), np.full(nseg, hh)], a
    aH = ring(H)[1]
    hs = [h0] + [k for k in kn if k < H - aH]
    pts = [ring(hh)[0] for hh in hs]
    r0 = ring(kn[0])[0]; r0[:, 2] = h0; pts[0] = r0                     # base ring = lowest knot's section
    pts.append(ring(H - aH)[0])
    pts.append(np.array([[xc + row['u0'] + row['u1'] * H, yc + row['v0'] + row['v1'] * H, H]]))
    return hull(np.concatenate(pts))


def marker_parts(infos, body_tm):
    """prim_potlid.markers_from's accepted balls, kept only with evidence of a sphere cap (a flat residual patch -
    a wall our model leaves out by a few mm - passes the 7 mm prior fit too): free-fit radius MK_FREE_R with a
    small residual, or a curved cap (spread >= MK_SPREAD). Stems as prim_potlid (ball to the nearest body point)."""
    pq = trimesh.proximity.ProximityQuery(body_tm)
    parts, out = [], []
    for m in infos:
        m = dict(m)
        if 'rejected' not in m:
            fr_ok = ('free_r_mm' in m and MK_FREE_R[0] <= m['free_r_mm'] <= MK_FREE_R[1] and m['free_res_mm'] <= 1.2)
            if not (fr_ok or m.get('spread', 0) >= MK_SPREAD):
                m['rejected'] = 'flat'
        if 'rejected' not in m:
            c = np.asarray(m['centre']); r = m['r_mm'] * 1e-3
            parts.append(PL.mf_sphere(c, r, seg=20))
            if m.get('stem'):
                sp = pq.on_surface(c[None])[0][0]
                ax = (sp - c) / max(np.linalg.norm(sp - c), 1e-9)
                parts.append(PL.mf_cylinder(c, sp + 0.002 * ax, PL.STEM_R))
        out.append(m)
    return parts, out


def rack_to_object(m, fr):
    R = np.stack([fr['L'], fr['w'], fr['up']], 1)
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = fr['o']
    m.apply_transform(T)
    return m


# ------------------------------------------------------------------------------------------------ main fit
def fit(P, C, F, band, info=None, depth=None, up_fixed=None):
    """All geometry in the rack frame. Returns (geo, frame, per-point rack coordinates)."""
    info = {} if info is None else info
    fr = initial_frame(P, C, up_fixed)
    x, y, h = to_rack(P, fr)
    xl, xh, flip = find_cup(x, y, h)
    if flip:                                         # cup holder at -x (convention)
        fr = rotate_frame(fr, math.pi); x, y, h = to_rack(P, fr)
        xl, xh, flip = find_cup(x, y, h)
    info['cup_x_range'] = [float(xl), float(xh)]
    # diagnostic only: tilt of the lip plane against the table cut (not used: across ICP-aligned episodes the cut
    # normals agree within ~1-2.5 deg, the lip-plane normals scatter by up to 6 deg)
    n, _ = normals(P, C, k=24)
    H_r = rim_height(x, y, h, xh + 0.015)
    # outline: x0 = the cup holder's right side (the tray proper starts there), xa = its left end (fixed)
    xa = xl - T_WALL
    info['xa'] = float(xa)
    lipc = lip_plane(x, y, h, xh + 0.015)[0]
    po = fit_outline(P, C, x, y, h, fr, xh + 0.01, xa, lipc, info)
    # re-express in the outline's frame (x along the tray, y = 0 on its centre line), refit
    for _ in range(2):
        fr = rotate_frame(fr, po[2], 0.0, po[1])
        x, y, h = to_rack(P, fr)
        lipc, n_lip, sd_lip = lip_plane(x, y, h, xh + 0.015)
        po = fit_outline(P, C, x, y, h, fr, xh + 0.01, xa, lipc, info)
    info['lip_plane'] = dict(a_mm=float(lipc[0] * 1e3), slope_x=float(lipc[1]), slope_y=float(lipc[2]),
                             n_segments=n_lip, resid_sd_mm=sd_lip)
    outline = dict(cx=0.5 * (xa + po[0]), cy=po[1], hx=0.5 * (po[0] - xa), hy=po[4], rc=po[5], s0=po[6], s1=po[7],
                   so1=po[3], theta=po[2], xa=xa)
    # floor: a T_WALL plate on the table (table = cut - band); with a shared floor depth below the lip (driver:
    # the deepest of all episodes' cuts, since the floor is unseen in every episode) it is placed at H_r - depth
    h_ft = -band + T_WALL if depth is None else H_r - depth
    h_tab = h_ft - T_WALL
    pc, top, h_cf = fit_cup(P, C, n, x, y, h, fr, xh, H_r, h_ft, info)
    cup = dict(cx=pc[0], cy=pc[1], ux=pc[2], uy=pc[3], ex=pc[4], ey=pc[5], fx=pc[6], fy=pc[7], r=pc[8], top=top,
               h_cf=h_cf)
    # the cup holder's outer face towards the tray (at the lip height): the basin ends there
    x_cup_face = cup['cx'] + cup['ux'] * H_r + cup['ex'] + cup['fx'] * H_r
    # pegs: inside the basin (at least 4 mm inside the inner face), right of the cup holder
    sd = rrect_sd(x - outline['cx'], y - outline['cy'], outline['hx'], outline['hy'], outline['rc'])[0]
    s_h = outline['s0'] + outline['s1'] * (H_r - h)
    inside = (sd < -(s_h + 0.010)) & (x > x_cup_face + 0.006)
    rows = detect_pegs(x, y, h, inside, info)
    pegs = []
    for cents in rows:
        r = fit_peg_row(x, y, h, cents, inside | (h > H_r + 0.002), top)
        # a peg row stands well above the lip (a row of blobs along a wall does not)
        if r is not None and r['H_p'] > H_r + 0.008:
            pegs.append(r)
        elif r is not None:
            info.setdefault('peg_rows_rejected', []).append(dict(n=len(r['xc']), H_p=r['H_p']))
    geo = dict(outline=outline, cup=cup, pegs=pegs, h_tab=h_tab, h_ft=h_ft, H_r=H_r, lipc=[float(v) for v in lipc],
               x_cup_face=x_cup_face,
               band=band)
    info.update(H_r=H_r, h_tab=h_tab, h_ft=h_ft, x_cup_face=x_cup_face, outline_final=outline, cup_final=cup,
                pegs=[{k: (v if not isinstance(v, float) else round(v, 5)) for k, v in r.items()} for r in pegs])
    return geo, fr, n


def build(P, C, F, band, variants, prefix, fr_out=None, depth=None, up_fixed=None, balls=None):
    """Fit + mesh every requested variant; fr_out: optional transform of the final mesh (joint: mean frame).
    balls (C0b, GMG_MK set): gmg balls in the FINAL mesh frame; attached with posts (markers.attach, stem rule on P
    moved to the final frame) to every variant that does not end in nomk."""
    info = {}
    geo, fr, n = fit(P, C, F, band, info, depth, up_fixed)
    body = build_body(geo)
    body_tm = PL.from_mf(body)
    out = {}
    mk_parts, mk_info = [], []
    if GMG_MK is not None:
        return build_gmg(P, info, geo, fr, body, variants, prefix, fr_out, balls or [])
    if any(not v.endswith('nomk') for v in variants):
        # residual points: outside the body by > APP_D (in rack coordinates)
        x, y, h = to_rack(P, fr)
        Q = np.c_[x, y, h]
        S, fi = trimesh.sample.sample_surface(body_tm, 200000, seed=0)
        d, j = cKDTree(S).query(Q)
        outside = np.einsum('ij,ij->i', Q - S[j], body_tm.face_normals[fi[j]]) > 0
        res = outside & (d > APP_D)
        V = C - P; V /= np.linalg.norm(V, axis=1, keepdims=True)
        Vr = np.c_[V @ fr['L'], V @ fr['w'], V @ fr['up']]
        _, mk_all = PL.markers_from(Q[res], Vr[res], d[res], Q, body_tm, 'fit')
        # markers sit on the rack's exterior: a ball centred over the basin (inside the inner face, right of the
        # cup holder) is a residual of something in the tray (peg flare, clutter), not a marker
        o = geo['outline']
        for m in mk_all:
            if 'rejected' in m:
                continue
            c = np.asarray(m['centre'])
            sd_c = rrect_sd(np.array([c[0] - o['cx']]), np.array([c[1] - o['cy']]), o['hx'], o['hy'], o['rc'])[0][0]
            if sd_c < -o['s0'] and c[0] > geo['x_cup_face']:
                m['rejected'] = 'in_basin'
        mk_parts, mk_info = marker_parts(mk_all, body_tm)
    info['markers'] = mk_info
    info['n_markers'] = int(sum(1 for m in mk_info if 'rejected' not in m))
    for var in variants:
        M = body
        if not var.endswith('nomk') and mk_parts:
            M = mf.Manifold.batch_boolean([body] + mk_parts, mf.OpType.Add)
        m = PL.from_mf(M)
        m = rack_to_object(m, fr)
        if fr_out is not None:
            m.apply_transform(fr_out)
        f = f'{prefix}_{var}.glb'
        m.export(f)
        out[var] = dict(path=f, faces=int(len(m.faces)), watertight=bool(m.is_watertight))
    rep = dict(info=info, variants=out, frame={k: v.tolist() for k, v in fr.items()})
    json.dump(rep, open(prefix + '.json', 'w'), indent=1, default=float)
    return rep, geo, fr


def build_gmg(P, info, geo, fr, body, variants, prefix, fr_out, balls):
    """C0b mesh export: body (rack frame -> object frame -> fr_out), then the gmg balls (final frame) attached."""
    from gmg import markers as MK
    Pf = P if fr_out is None else P @ fr_out[:3, :3].T + fr_out[:3, 3]
    info['markers'] = dict(source='gmg markers.py', settings_sha256=GMG_MK['sha'], n=len(balls), balls=balls)
    info['n_markers'] = int(len(balls))
    out = {}
    for var in variants:
        m = PL.from_mf(body)
        m = rack_to_object(m, fr)
        if fr_out is not None:
            m.apply_transform(fr_out)
        if not var.endswith('nomk') and balls:
            m = MK.attach(m, balls, obs=dict(pts=Pf))
            info.setdefault('attach', {})[var] = m.metadata.get('balls')
        f = f'{prefix}_{var}.glb'
        m.export(f)
        out[var] = dict(path=f, faces=int(len(m.faces)), watertight=bool(m.is_watertight))
    rep = dict(info=info, variants=out, frame={k: v.tolist() for k, v in fr.items()}, c0b=C0B_USED)
    json.dump(rep, open(prefix + '.json', 'w'), indent=1, default=float)
    return rep, geo, fr


def gmg_episode_balls(obs_path):
    """C0b: the gmg balls of this rack episode (object frame of its track) from GMG_MK['dir']/ep<N>.json."""
    ep = os.path.basename(obs_path).split('_')[0]
    J = json.load(open(os.path.join(GMG_MK['dir'], f'{ep}.json')))
    if J.get('settings_sha256') != GMG_MK['sha']:
        raise SystemExit(f'{ep}: markers settings sha {J.get("settings_sha256")} != frozen {GMG_MK["sha"]}')
    return J['balls'].get(OBJ, [])


def move_balls(balls, T):
    out = []
    for b in balls:
        b = dict(b); c = np.asarray(b['c'], np.float64)
        b['c'] = [float(v) for v in T[:3, :3] @ c + T[:3, 3]]
        out.append(b)
    return out


# ------------------------------------------------------------------------------------------------ joint
def icp_align(src, dst, iters=30, trim=0.8):
    """Rigid point-to-point trimmed ICP of src onto dst (both (N,3)); returns 4x4."""
    tree = cKDTree(dst)
    T = np.eye(4)
    X = src.copy()
    for _ in range(iters):
        d, j = tree.query(X)
        keep = d < np.percentile(d, trim * 100)
        A, B = X[keep], dst[j[keep]]
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T; t = cb - R @ ca
        X = X @ R.T + t
        Ti = np.eye(4); Ti[:3, :3] = R; Ti[:3, 3] = t
        T = Ti @ T
        if np.linalg.norm(t) < 1e-6:
            break
    return T, float(np.median(d))


def mean_rigid(Ts):
    """Mean of rigid transforms: chordal mean rotation (SVD projection) + mean translation."""
    Rm = sum(T[:3, :3] for T in Ts) / len(Ts)
    U, _, Vt = np.linalg.svd(Rm)
    R = U @ np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]) @ Vt
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = np.mean([T_[:3, 3] for T_ in Ts], 0)
    return T


def lip_above_cut(P, C):
    """Pass 1 of the driver: lip height above this episode's table cut (m), and the cut normal."""
    fr = initial_frame(P, C)
    x, y, h = to_rack(P, fr)
    xl, xh, flip = find_cup(x, y, h)
    if flip:
        fr = rotate_frame(fr, math.pi); x, y, h = to_rack(P, fr); xl, xh, flip = find_cup(x, y, h)
    return rim_height(x, y, h, xh + 0.015), fr['up']


def joint(obs_list, prefix, variants=('joint', 'joint_nomk'), depth=None):
    """Align every episode's points to the reference (the episode with the most points) by trimmed ICP, merge,
    fit once with up = the mean of the episodes' (aligned) table-cut normals; the mesh (in the reference frame) is
    then moved by the mean of the reference->episode transforms."""
    data = [load(f) for f in obs_list]
    ref = int(np.argmax([len(d[0]) for d in data]))
    rng = np.random.default_rng(0)
    Pref = data[ref][0]
    dst = Pref[rng.choice(len(Pref), min(60000, len(Pref)), replace=False)]
    Ps, Cs, Fs, Ts, rep_al, ups = [], [], [], [], [], []
    for k, (P, C, F, band) in enumerate(data):
        if k == ref:
            T, med = np.eye(4), 0.0
        else:
            src = P[rng.choice(len(P), min(60000, len(P)), replace=False)]
            T, med = icp_align(src, dst)
        Ps.append(P @ T[:3, :3].T + T[:3, 3]); Cs.append(C @ T[:3, :3].T + T[:3, 3]); Fs.append(F + 100000 * k)
        Ts.append(T)
        ups.append(T[:3, :3] @ lip_above_cut(P, C)[1])
        ang = math.degrees(math.acos(np.clip((np.trace(T[:3, :3]) - 1) / 2, -1, 1)))
        rep_al.append(dict(obs=os.path.basename(obs_list[k]), icp_med_mm=round(med * 1e3, 2),
                           rot_deg=round(ang, 3), trans_mm=[round(v * 1e3, 2) for v in T[:3, 3]]))
    P = np.concatenate(Ps); C = np.concatenate(Cs); F = np.concatenate(Fs)
    key = np.floor(P / VOX).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    first = np.sort(first)
    P, C, F = P[first], C[first], F[first]
    # episode e's frame = inv(T_e) applied to the reference frame; the mean frame:
    Tm = mean_rigid([np.linalg.inv(T) for T in Ts])
    up_m = np.mean(ups, 0); up_m /= np.linalg.norm(up_m)
    jballs, jball_rep = None, None
    if GMG_MK is not None:
        # C0b: each episode's balls -> reference frame (its ICP T) -> final frame (Tm); the detector's frozen overlap
        # suppression (centre distance < r_a + r_b: more votes stays) on the pooled balls; no new detection
        from gmg import markers as MK
        pooled = []
        for k, f in enumerate(obs_list):
            pooled += move_balls(gmg_episode_balls(f), Tm @ Ts[k])
        kept = MK._nms(MK.balls_from_json(pooled))
        jballs = [MK.ball_dict(b) for b in kept]
        jball_rep = dict(pooled=len(pooled), kept=len(jballs))
    rep, geo, fr = build(P, C, F, data[ref][3], list(variants), prefix, fr_out=Tm, depth=depth, up_fixed=up_m,
                         balls=jballs)
    if jball_rep is not None:
        rep['joint_balls'] = jball_rep
    rep['alignment'] = dict(reference=os.path.basename(obs_list[ref]), episodes=rep_al,
                            mean_frame_T=Tm.tolist(), up_mean=up_m.tolist(),
                            up_spread_deg=[float(math.degrees(math.acos(np.clip(u @ up_m, -1, 1)))) for u in ups])
    json.dump(rep, open(prefix + '.json', 'w'), indent=1, default=float)
    return rep


def fidelity(obs, paths):
    """obs_fidelity.py (GT-free) on the given meshes against the comma-joined observation files."""
    outp = subprocess.run([sys.executable, f'{HERE}/obs_fidelity.py', obs] + list(paths),
                          capture_output=True, text=True, check=True).stdout
    fid = [json.loads(l) for l in outp.splitlines() if l.startswith('{')]
    for p, j in zip(paths, fid):
        assert p.endswith(j['mesh'])
    return fid


# ------------------------------------------------------------------------------------------------ driver
def run(obs_dir, out_dir, episodes, variants=('full', 'nomk'), joint_variants=('joint', 'joint_nomk')):
    os.makedirs(out_dir, exist_ok=True)
    jobs = [(ep, f'{obs_dir}/ep{ep}_{OBJ}.npz') for ep in episodes if os.path.exists(f'{obs_dir}/ep{ep}_{OBJ}.npz')]
    cands = []
    # pass 1: shared floor depth below the lip. The floor is unseen in every episode, so it lies below the lowest
    # table cut of all episodes: depth = max over episodes of (lip above cut) + table_band - T_WALL (the floor
    # plate lying on the table under the deepest cut)
    lips = {}
    for ep, f in jobs:
        P, C, F, band = load(f)
        lips[ep] = lip_above_cut(P, C)[0]
    depth = max(lips.values()) + band - T_WALL
    print(json.dumps(dict(pass1_lip_above_cut_mm={k: round(v * 1e3, 1) for k, v in lips.items()},
                          floor_depth_mm=round(depth * 1e3, 1))), flush=True)
    for ep, f in jobs:
        prefix = f'{out_dir}/{OBJ}/ep{ep}'
        os.makedirs(os.path.dirname(prefix), exist_ok=True)
        P, C, F, band = load(f)
        rep, geo, fr = build(P, C, F, band, list(variants), prefix, depth=depth,
                             balls=gmg_episode_balls(f) if GMG_MK is not None else None)
        for var, v in rep['variants'].items():
            cands.append(dict(object=OBJ, episode=str(ep), variant=var, path=os.path.abspath(v['path']),
                              faces=v['faces'], watertight=v['watertight'], n_markers=rep['info']['n_markers'],
                              H_r_mm=rep['info']['H_r'] * 1e3, cup_top_mm=rep['info']['cup']['top'] * 1e3,
                              n_pegs=sum(len(r['xc']) for r in rep['info']['pegs'])))
        print(json.dumps(cands[-1]), flush=True)
    obs = ','.join(f for _, f in jobs)
    fid = fidelity(obs, [c['path'] for c in cands])
    for c, j in zip(cands, fid):
        c.update(fid_obs_to_mesh_mm=j['obs_to_mesh_mm'], fid_mesh_to_obs_mm=j['mesh_to_obs_mm'], fid_sum_mm=j['sum_mm'])
    if joint_variants:
        # consistency check before merging (GT-free): an episode enters the joint fit only if its own 'full' fit
        # explains all episodes' points within JOINT_TOL x the best episode's fidelity (a hand resting on the cup
        # holder or a failed part fit shows up there)
        fe = {c['episode']: c['fid_sum_mm'] for c in cands if c['variant'] == 'full'}
        best_f = min(fe.values())
        use = [(ep, f) for ep, f in jobs if fe.get(str(ep), 1e9) <= JOINT_TOL * best_f]
        print(json.dumps(dict(joint_episodes=[ep for ep, _ in use], fid_full=fe)), flush=True)
        prefix = f'{out_dir}/{OBJ}/joint'
        rep = joint([f for _, f in use], prefix, joint_variants, depth=depth)
        for var, v in rep['variants'].items():
            cands.append(dict(object=OBJ, episode='all', variant=var, path=os.path.abspath(v['path']),
                              faces=v['faces'], watertight=v['watertight'], n_markers=rep['info']['n_markers'],
                              H_r_mm=rep['info']['H_r'] * 1e3, cup_top_mm=rep['info']['cup']['top'] * 1e3,
                              n_pegs=sum(len(r['xc']) for r in rep['info']['pegs'])))
        print(json.dumps(dict(alignment=rep['alignment']['episodes'])), flush=True)
        jc = [c for c in cands if c['episode'] == 'all']
        for c, j in zip(jc, fidelity(obs, [c['path'] for c in jc])):
            c.update(fid_obs_to_mesh_mm=j['obs_to_mesh_mm'], fid_mesh_to_obs_mm=j['mesh_to_obs_mm'],
                     fid_sum_mm=j['sum_mm'])
    best = min(cands, key=lambda c: c['fid_sum_mm'])
    sel = dict(episode=best['episode'], variant=best['variant'], path=best['path'], fid_sum_mm=best['fid_sum_mm'],
               obs=obs)
    with open(f'{out_dir}/candidates.jsonl', 'w') as fh:
        for c in cands:
            fh.write(json.dumps(c) + '\n')
    json.dump(dict(selection={OBJ: sel}), open(f'{out_dir}/selection.json', 'w'), indent=1)
    with open(f'{out_dir}/manifest_all.tsv', 'w') as fh:
        for c in cands:
            tag = 'selected' if c['path'] == best['path'] else 'candidate'
            fh.write(f"rack/ep{c['episode']}_{c['variant']}\t{OBJ}\t{c['path']}\t{tag}\n")
    for c in cands:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if k != 'path'}))
    print(json.dumps(dict(selection=(sel['episode'], sel['variant'], sel['fid_sum_mm']))))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('obs'); b.add_argument('prefix')
    b.add_argument('--variants', default='full,nomk'); b.add_argument('--depth', type=float, default=None)
    j = sub.add_parser('joint'); j.add_argument('obs'); j.add_argument('prefix')
    j.add_argument('--variants', default='joint,joint_nomk'); j.add_argument('--depth', type=float, default=None)
    r = sub.add_parser('run'); r.add_argument('--obs_dir', required=True); r.add_argument('--out', required=True)
    r.add_argument('--episodes', default='12,13,26,27,31')
    for q in (b, j, r):
        q.add_argument('--t_wall', type=float, default=None, help='C0b: wall / floor thickness T (m), replaces T_WALL')
        q.add_argument('--s0_min_t', action='store_true', help='C0b: lip width lower bound S0_MIN = T')
        q.add_argument('--markers_dir', default=None, help='C0b: gmg detect_episode outputs <dir>/ep<N>.json')
    a = p.parse_args()
    global T_WALL, S0_MIN, GMG_MK
    if a.t_wall is not None:
        if a.t_wall < 0:
            raise SystemExit('C0b: rack wall needs thickness.py (< 200 measurements) or t0_C0b (not fittable)')
        T_WALL = C0B_USED['t_wall'] = float(a.t_wall)
    if a.s0_min_t:
        S0_MIN = C0B_USED['s0_min'] = T_WALL
    if a.markers_dir is not None:
        sys.path.insert(0, os.path.dirname(HERE))
        from gmg import markers as MK
        GMG_MK = dict(dir=a.markers_dir, sha=MK.SETTINGS_SHA256)
        C0B_USED['markers_dir'] = a.markers_dir
    if C0B_USED:
        C0B_USED.update(cup_lean=CUP_LEAN, joint_tol=JOINT_TOL)
        print(json.dumps(dict(c0b=C0B_USED)), flush=True)
    if a.cmd == 'build':
        P, C, F, band = load(a.obs)
        rep, geo, fr = build(P, C, F, band, a.variants.split(','), a.prefix, depth=a.depth,
                             balls=gmg_episode_balls(a.obs) if GMG_MK is not None else None)
        inf = rep['info']
        print(json.dumps(dict(obs=os.path.basename(a.obs), H_r=round(inf['H_r'] * 1e3, 1), outline=inf['outline'],
                              cup=inf['cup'], pegs=[(len(r['xc']), round(r['H_p'] * 1e3, 1), [round(v * 1e3, 1) for v in r['a']],
                                                     round(r['kappa'], 2), round(r['v1'], 3), round(r['med_abs_res_mm'], 2))
                                                    for r in inf['pegs']],
                              markers=inf['n_markers'], variants=rep['variants']), default=float))
    elif a.cmd == 'joint':
        rep = joint(a.obs.split(','), a.prefix, a.variants.split(','), depth=a.depth)
        print(json.dumps(dict(alignment=rep['alignment'], variants=rep['variants']), default=float))
    else:
        run(a.obs_dir, a.out, a.episodes.split(','))


if __name__ == '__main__':
    main()
