"""Dynamical-system (DS) obstacle modulation of a reference's wrist path (2026-11-13). OPTIONAL, OFF BY DEFAULT: nothing in
the pipeline calls it. Phase 1 of the pre-registered test docs/research/work/ds-modulation-20261113/PREREG.md; the idea
is a hypothesis [H], not a shipped fix.

Source of the idea: Khansari-Zadeh & Billard, "A dynamical system approach to realtime obstacle avoidance", Autonomous
Robots 32:433-454, 2012 ("KZB"), as used in romanklis/ann2snn-pychromo-drone (src/drone6dof/field.py modulate_ds,
control.py). A motion's velocity field is reshaped near obstacles by a modulation matrix M = E D E^T (E = [n, e1, e2],
n the obstacle normal) with eigenvalues 1 - 1/Gamma (normal) and 1 + 1/Gamma (tangent); Gamma = 1 on the
(margin-inflated) obstacle surface, > 1 outside. The attractor is kept and, for a trajectory starting outside, the
normal velocity vanishes on the boundary (impenetrability).

What it does to a FlashCHORD reference (reads ONLY our reference, our object meshes or their convex pieces, our support
USDA and the robot's own collision meshes; never ground truth):
  * Phases, per hand, from our reference (pipeline/hold_phases.py: MANO contact labels + our object track):
      APPROACH frames: no hold, and the hand body >= D_PRE from the object of its next hold and from the object of its
        previous hold (grasp and release zones). Covers approach and retreat. The target (excluded from the obstacles)
        is the next hold's object, after the last hold the last held object.
      TRANSPORT frames: a one-hand hold whose object is >= D_PRE from the support it was lifted from AND the support it is
        put on (another object or the table).
      Never modulated: grasp / release zones (< D_PRE from the target), lift-off and placement zones, two-handed holds.
    A window is a maximal run of APPROACH (or TRANSPORT) frames; windows are computed once, from the input reference.
  * In each window [a, b] the wrist position follows the modulated tracking DS
        xdot = M(x, t) (f(x, t) - v_o) + v_o,      f(x, t) = pdot(t) + K (p(t) - x)
    from x(a) = p(a), integrated with sub-steps on the original clock (frame index = time: timing kept). The deviation
    x - p is faded to 0 over the last FADE frames (smoothstep), so the window ends exactly on the original (goal kept).
    Stall guard: when more than the margin is left to fade and the fade would move the wrist faster than the reference's
    own fastest frame step in that window
    (the DS stopped at a saddle point in front of an obstacle the reference crosses head-on), the window is left
    unchanged and reported as stalled.
  * Moving body: the hand (the robot's collision meshes, posed by the reference's link frames) and, in TRANSPORT, the held
    object's surface. Translation only: the wrist and all robot frames shift by the same vector (fingers follow
    rigidly); in TRANSPORT the held object, and this hand's MANO contact points, shift with it.
  * Obstacles: every object that is not this hand's target / held object, at its reference pose (with its reference
    velocity while a hand holds it: KZB's moving-obstacle form); the table (our support disc top) only for the held
    object's samples, because FlashCHORD turns robot-support collision off (configs/collision/training.yaml,
    manipulation.yaml: robot_support_collision false). The other hand is not an obstacle (hand-hand is a guard).
  * Gamma: for obstacle k the C-space distance of the translating body is d_k(x) = min over body samples of the signed
    distance to obstacle k. Gamma_k = ((d_k + R_k) / (m + R_k))^2: KZB's Gamma for a sphere (p = 1) of radius R_k
    (obstacle bounding radius) inflated by the margin m (KZB safety factor eta = (R_k + m) / R_k).
    Eigenvalues lambda_n = 1 - w_k / Gamma_k^(1/rho), lambda_t = 1 + w_k / Gamma_k^(1/rho), with KZB's multi-obstacle
    weights w_k = prod_{i != k} (Gamma_i - 1) / ((Gamma_k - 1) + (Gamma_i - 1)); M_bar = product of the M_k (closest
    applied last); v_o = sum_k w_k v_o,k.
    Documented deviations from KZB (both keep M = I far away and the normal velocity at 0 on the boundary):
      1. locality cutoff: 1/Gamma is renormalised to reach exactly 0 at d = D_INF (M = I beyond), so far-away motion is
         untouched; inside the margin (Gamma < 1) lambda_n < 0 pushes out, clipped to [LAM_N_MIN, LAM_T_MAX];
      2. tail negligence of Huber, Slotine & Billard 2022 (RA-L; arXiv 2205.04928, eq. 14, with w_r = 1) instead of a hard
         switch: while the nominal relative velocity leaves obstacle k (n.v = s > 0), both eigenvalues blend to 1 with
         w_v = s / |v|, which keeps the velocity continuous.
  * Signed distance of a sampled surface: nearest surface sample (KD tree), sign from that sample's outward normal.
    Obstacle surfaces: FlashCHORD's own convex pieces of our mesh (geom 'fc_hulls', what the simulator collides with;
    needs the FlashCHORD venv), or our mesh itself (geom 'mesh'), or a directory of piece_*.obj (geom 'pieces').

Parameters (DEFAULTS below) are fixed in the PREREG from geometry and the paper, not from outcomes.

Usage (FlashCHORD venv for --geom fc_hulls; any python with numpy, scipy, trimesh, pyarrow otherwise):
  ds_modulate.py IN.parquet OUT.parquet --meshes DIR --hand_urdf_dir DIR [--support USDA] [--geom fc_hulls]
                 [--phases_json OUT.json] [--report OUT.json] [--margin ... (see DEFAULTS)]
"""
import argparse, glob, json, os, sys, time

import numpy as np

DEFAULTS = dict(
    margin=0.010,       # m   safety margin m: Gamma = 1 at d = m (PREREG section 4)
    d_inf=0.08,         # m   influence cutoff: M = I beyond (>= 3 frames of warning at the fastest reference approach)
    rho=1.0,            # -   KZB reactivity
    k_track=5.0,        # 1/s tracking gain K of the nominal DS (time constant 0.2 s)
    d_pre=0.08,         # m   grasp / placement zone: never modulated closer than this to the target or supports
    fade=3,             # frames over which the deviation returns to 0 at a window's end
    sub_mm=1.0,         # mm  maximum nominal displacement per integration sub-step
    min_sub=4,          # -   minimum sub-steps per frame
    body_spacing=0.006, # m   surface sample spacing of the moving body (hand links, held object)
    obs_spacing=0.003,  # m   surface sample spacing of obstacles
    lam_n_min=-1.0,     # -   clip of the normal eigenvalue inside the margin (push out at most at the nominal speed)
    lam_t_max=2.0,      # -   clip of the tangent eigenvalue (KZB's maximum, reached at Gamma = 1)
)
EPS = 1e-9


# ===================================================================================== DS modulation (pure numpy)
def tangent_basis(n):
    """E = [n, e1, e2] (3x3, orthonormal columns) for a unit normal n."""
    n = np.asarray(n, float); n = n / max(np.linalg.norm(n), EPS)
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(n, a); e1 /= np.linalg.norm(e1)
    return np.stack([n, e1, np.cross(n, e1)], 1)


def inv_gamma(d, R, margin, d_inf):
    """1/Gamma for KZB's sphere-form Gamma = ((d + R) / (m + R))^2, renormalised so that it is 1 at d = m and exactly 0 at
    d >= d_inf (deviation 1 in the module docstring). Above 1 inside the margin; d may be an array."""
    d = np.asarray(d, float)
    g = lambda x: ((margin + R) / np.maximum(x + R, 1e-6)) ** 2
    g_inf = g(np.asarray(d_inf, float))
    u = (g(d) - g_inf) / (1.0 - g_inf)
    return np.where(d >= d_inf, 0.0, np.maximum(u, 0.0))


def kzb_weights(u):
    """KZB multi-obstacle weights w_k = prod_{i != k} (G_i - 1) / ((G_k - 1) + (G_i - 1)) from u_k = 1/G_k (> 0).
    Obstacles at or inside the margin (u >= 1) take weight 1 and the others 0 (the limit of the formula)."""
    u = np.asarray(u, float)
    if len(u) == 1:
        return np.ones(1)
    inside = u >= 1.0
    if inside.any():
        return inside.astype(float)
    gm1 = 1.0 / u - 1.0
    w = np.ones(len(u))
    for k in range(len(u)):
        for i in range(len(u)):
            if i != k:
                w[k] *= gm1[i] / (gm1[k] + gm1[i])
    return w


def modulation_matrix(n, a, v_rel, p=DEFAULTS):
    """M_k = E diag(lambda_n, lambda_t, lambda_t) E^T for one obstacle; a = w_k / Gamma_k^(1/rho); v_rel the nominal velocity
    relative to the obstacle. Tail negligence (deviation 2): while v_rel leaves the obstacle both eigenvalues blend to 1."""
    lam_n = max(1.0 - a, p['lam_n_min']); lam_t = min(1.0 + a, p['lam_t_max'])
    s = float(np.dot(n, v_rel)); vn = float(np.linalg.norm(v_rel))
    if s > 0.0 and vn > EPS:
        wv = s / vn
        lam_t = wv + (1.0 - wv) * lam_t; lam_n = lam_t
    E = tangent_basis(n)
    return E @ np.diag([lam_n, lam_t, lam_t]) @ E.T


def modulate(f, obstacles, p=DEFAULTS):
    """Modulated velocity. f: nominal velocity (3,); obstacles: list of (n unit outward normal, u = 1/Gamma, v_o obstacle
    velocity). Returns M_bar (f - v_o) + v_o (KZB moving-obstacle form) with KZB's weights; M = I when the list is empty."""
    f = np.asarray(f, float)
    obs = [o for o in obstacles if o[1] > 0.0]
    if not obs:
        return f.copy()
    u = np.array([o[1] for o in obs]); w = kzb_weights(u)
    v_o = sum(wk * np.asarray(o[2], float) for wk, o in zip(w, obs))
    v = f - v_o
    out = v.copy()
    for k in np.argsort(u):                                    # farthest first, the closest obstacle applied last
        n, uk, _ = obs[k]
        a = w[k] * uk ** (1.0 / p['rho'])
        out = modulation_matrix(n, a, v, p) @ out              # each M_k from the nominal relative velocity (KZB)
    return out + v_o


# ===================================================================================== sampled signed distance
def _quat_wxyz_to_mat(q):
    q = np.asarray(q, float); q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
                     np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
                     np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)


def sample_surface(vertices, faces, spacing):
    """Area-uniform surface samples (and their face normals) at roughly SPACING, plus the vertices' nearest-face normals."""
    v = np.asarray(vertices, float); f = np.asarray(faces, int)
    tri = v[f]; cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); area = 0.5 * np.linalg.norm(cr, axis=1)
    fn = cr / np.maximum(2 * area[:, None], EPS)
    n = max(int(np.ceil(area.sum() / spacing ** 2)), 1)
    rng = np.random.default_rng(0)                              # fixed seed: deterministic geometry
    idx = rng.choice(len(f), n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n); s = np.sqrt(r1)
    pts = tri[idx, 0] * (1 - s)[:, None] + tri[idx, 1] * (s * (1 - r2))[:, None] + tri[idx, 2] * (s * r2)[:, None]
    return pts, fn[idx]


class SampledSurface:
    """Signed distance to a closed surface given by samples with outward normals (body frame), via a KD tree: nearest
    sample s, sign from (q - s).n_s (see query). R = bounding radius about the sample centroid."""

    def __init__(self, points, normals, spacing, name=''):
        from scipy.spatial import cKDTree
        self.P = np.asarray(points, float); self.N = np.asarray(normals, float)
        self.N /= np.maximum(np.linalg.norm(self.N, axis=1, keepdims=True), EPS)
        self.h = float(spacing); self.tree = cKDTree(self.P); self.name = name
        self.c = self.P.mean(0); self.R = float(np.linalg.norm(self.P - self.c, axis=1).max())

    def coarse(self, spacing):
        """A random subset at roughly SPACING (the samples are area-uniform, so a stride keeps them uniform)."""
        k = max(1, int(round((spacing / self.h) ** 2)))
        return SampledSurface(self.P[::k], self.N[::k], spacing, self.name)

    @classmethod
    def from_mesh(cls, vertices, faces, spacing, name=''):
        return cls(*sample_surface(vertices, faces, spacing), spacing, name)

    @classmethod
    def from_convex_pieces(cls, pieces, spacing, name=''):
        """Union of convex pieces (list of (k, 3) vertex arrays): hull surfaces sampled, samples inside another piece
        dropped, so the samples lie on the union's boundary with outward normals."""
        from scipy.spatial import ConvexHull
        hulls = [ConvexHull(np.asarray(v, float)) for v in pieces]
        P, N = [], []
        for i, h in enumerate(hulls):
            pts, nrm = sample_surface(h.points, h.simplices, spacing)
            c = h.points[h.vertices].mean(0); flip = np.einsum('ij,ij->i', nrm, pts - c) < 0; nrm[flip] *= -1
            keep = np.ones(len(pts), bool)
            for j, g in enumerate(hulls):
                if j != i:
                    keep &= ~((pts @ g.equations[:, :3].T + g.equations[:, 3]) < -1e-4).all(1)
            P.append(pts[keep]); N.append(nrm[keep])
        return cls(np.vstack(P), np.vstack(N), spacing, name)

    def query(self, q, ub=np.inf):
        """q (n, 3) body-frame points -> signed distance (n,), outward unit gradient (n, 3). Points farther than UB from
        every sample get +inf (callers only need the body's minimum; a contiguous body that reaches deep inside also has
        samples near the surface). Within two sample spacings of the nearest sample: point-to-plane distance along its
        normal (exact on smooth surfaces, an underestimate at convex edges, i.e. conservative); beyond four spacings: the
        Euclidean distance to it; linear blend in between."""
        r, j = self.tree.query(q, distance_upper_bound=ub)
        far = ~np.isfinite(r); j = np.where(far, 0, j); r = np.where(far, 1.0, r)
        s, ns = self.P[j], self.N[j]; dv = q - s
        d_plane = np.einsum('ij,ij->i', dv, ns)
        sign = np.where(d_plane < 0, -1.0, 1.0)
        g_dir = dv * (sign / np.maximum(r, EPS))[:, None]
        w = np.clip(r / (2 * self.h) - 1.0, 0, 1)
        d = w * sign * r + (1 - w) * d_plane
        g = w[:, None] * g_dir + (1 - w[:, None]) * ns
        return np.where(far, np.inf, d), g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), EPS)


class HalfSpace:
    """z <= z0 (the table top); outward normal +z. Used only for held-object samples."""

    def __init__(self, z0, name='table'):
        self.z0 = float(z0); self.name = name; self.R = np.inf

    def query_world(self, q):
        return q[:, 2] - self.z0, np.tile([0.0, 0.0, 1.0], (len(q), 1))


# ===================================================================================== obstacles in the world
class PosedObstacle:
    """A SampledSurface carried by per-frame poses (positions (T, 3), rotations (T, 3, 3)) and velocities (T, 3)."""

    def __init__(self, surf, pos, rot, vel):
        self.s, self.pos, self.rot, self.vel = surf, np.asarray(pos, float), np.asarray(rot, float), np.asarray(vel, float)
        self.R = surf.R; self.name = surf.name

    def at(self, tf):
        """Pose at fractional frame tf: position lerped, rotation of the nearest frame (objects turn slowly)."""
        t0 = int(np.floor(tf)); t1 = min(t0 + 1, len(self.pos) - 1); al = tf - t0
        return (1 - al) * self.pos[t0] + al * self.pos[t1], self.rot[t0 if al < 0.5 else t1], self.vel[t0]

    def query_world(self, q, tf, ub=np.inf):
        p, Rm, _ = self.at(tf)
        d, g = self.s.query((q - p) @ Rm, ub)                    # world -> body: R^T (q - p)
        return d, g @ Rm.T

    def center_world(self, tf):
        p, Rm, _ = self.at(tf)
        return p + Rm @ self.s.c


def cspace_distance(x, offsets, obstacle, tf, ub=np.inf):
    """C-space distance of a translating body at wrist position x: min over body samples (x + offsets) of the signed
    distance to the obstacle, and the outward normal at the minimising sample (+inf if no sample is within UB)."""
    q = x[None, :] + offsets
    d, g = obstacle.query_world(q, tf, ub) if isinstance(obstacle, PosedObstacle) else obstacle.query_world(q)
    i = int(np.argmin(d))
    return float(d[i]), g[i]


# ===================================================================================== one window
def smoothstep(s):
    s = np.clip(s, 0, 1); return s * s * (3 - 2 * s)


def modulate_window(p, a, b, fps, body_fn, obstacles_fn, prm=DEFAULTS):
    """Modulated wrist path on frames a..b (inclusive) of p (T, 3).
    body_fn(tf) -> list of (offsets (n, 3) relative to the wrist, tag); obstacles_fn(tf) -> list of (obstacle, tags)
    where an obstacle acts only on the body groups whose tag is in tags. Returns (x (b-a+1, 3), info)."""
    dt = 1.0 / fps; x = p[a].copy(); out = [x.copy()]; nsub_tot = 0; dmin = np.inf; active = 0
    for t in range(a, b):
        step = np.linalg.norm(p[t + 1] - p[t])
        nsub = int(np.clip(np.ceil(2 * step * 1000 / prm['sub_mm']), prm['min_sub'], 200)); h = dt / nsub
        pdot = (p[t + 1] - p[t]) / dt
        for j in range(nsub):
            al = j / nsub; tf = t + al; pt = (1 - al) * p[t] + al * p[t + 1]
            f = pdot + prm['k_track'] * (pt - x)
            groups = body_fn(tf); obs = []
            for ob, tags in obstacles_fn(tf):
                best = None
                for offs, tag in groups:
                    if tag not in tags or not len(offs):
                        continue
                    if isinstance(ob, PosedObstacle):              # bounding-sphere cull
                        bc = x + offs.mean(0); br = np.linalg.norm(offs - offs.mean(0), axis=1).max()
                        if np.linalg.norm(bc - ob.center_world(tf)) - br - ob.R > prm['d_inf']:
                            continue
                    d, n = cspace_distance(x, offs, ob, tf, prm['d_inf'] + 4 * ob.s.h if isinstance(ob, PosedObstacle) else np.inf)
                    if best is None or d < best[0]:
                        best = (d, n)
                if best is None or not np.isfinite(best[0]):
                    continue
                d, n = best; dmin = min(dmin, d)
                R = ob.R if np.isfinite(ob.R) else 1.0             # a half-space: unit radius (only the cutoff matters)
                u = float(inv_gamma(d, R, prm['margin'], prm['d_inf']))
                if u > 0:
                    vo = ob.at(tf)[2] if isinstance(ob, PosedObstacle) else np.zeros(3)
                    obs.append((n, u, vo))
            v = modulate(f, obs, prm); active += bool(obs)
            x = x + h * v; nsub_tot += 1
        out.append(x.copy())
    X = np.array(out); dev = X - p[a:b + 1]
    L = min(int(prm['fade']), b - a)
    pull = float(np.linalg.norm(dev[len(dev) - 1 - L]) if L > 0 else np.linalg.norm(dev[-1]))
    if L > 0:
        for i in range(1, L + 1):
            dev[len(dev) - 1 - L + i] *= 1.0 - smoothstep(i / L)
    else:
        dev[-1] = 0.0
    dev[0] = 0.0
    # Stall guard (KZB saddle points: a body driven head-on into an obstacle stops on its boundary). If more than the
    # margin is left to fade AND the fade would move the wrist faster than the reference's own fastest frame step in this
    # window, the DS did not get round the obstacle in time: the window is left as it was (no snap back through the
    # obstacle) and reported as stalled.
    max_step = float(np.linalg.norm(np.diff(p[a:b + 1], axis=0), axis=1).max()) if b > a else 0.0
    stalled = L > 0 and pull > prm['margin'] and pull * 1.5 / L > max_step   # 1.5 = max slope of the smoothstep
    if stalled or active == 0:                                  # no obstacle in reach: the window is bit-identical
        dev[:] = 0.0
    return p[a:b + 1] + dev, dict(substeps=nsub_tot, active_substeps=int(active), min_cspace_d_m=float(dmin),
                                   fade_pull_m=pull, stalled=bool(stalled),
                                   max_dev_m=float(np.linalg.norm(dev, axis=1).max()))


# ===================================================================================== the reference
def runs(mask):
    m = np.concatenate([[0], np.asarray(mask, int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1))   # inclusive [a, b]


def col(t, name):
    return np.array(t.column(name)[0].as_py(), float)


def load_hand_samples(urdf_dir, side, frame_names, spacing):
    """Per robot link with a collision mesh (FlashCHORD's {side}_sharpawave.urdf, the embodiment the evaluator uses):
    link-frame surface samples. Returns [(frame index, (k, 3))]."""
    import xml.etree.ElementTree as ET, trimesh
    urdf = os.path.join(urdf_dir, f'{side}_sharpawave.urdf'); root = ET.parse(urdf).getroot(); out = []
    for link in root.findall('link'):
        name = link.get('name')
        for c in link.findall('collision'):
            m = c.find('geometry/mesh')
            if m is None or name not in frame_names:
                continue
            o = c.find('origin'); xyz = np.array([float(v) for v in (o.get('xyz', '0 0 0') if o is not None else '0 0 0').split()])
            rpy = (o.get('rpy', '0 0 0') if o is not None else '0 0 0').split()
            if any(abs(float(r)) > 1e-9 for r in rpy):
                raise ValueError(f'{urdf}: collision origin rpy on {name} not handled')
            mesh = trimesh.load(os.path.normpath(os.path.join(os.path.dirname(urdf), m.get('filename'))), force='mesh')
            pts, _ = sample_surface(mesh.vertices, mesh.faces, spacing)
            out.append((frame_names.index(name), np.vstack([pts, np.asarray(mesh.vertices)]) + xyz))
    if not out:
        raise ValueError(f'no collision links of {urdf} match the reference frame names')
    return out


def hand_world(frames, links):
    """(T, n, 3) world positions of the hand's collision samples, posed by the reference's link frames (pos + wxyz)."""
    T = len(frames); allp = []
    for fi, pts in links:
        Rm = _quat_wxyz_to_mat(frames[:, fi, 3:7]); allp.append(np.einsum('tij,nj->tni', Rm, pts) + frames[:, fi, None, :3])
    return np.concatenate(allp, 1)


def object_surface(name, meshes, geom, spacing, pieces_dir=None):
    import trimesh
    path = next((p for p in (f'{meshes}/{name}.glb', f'{meshes}/{name}/{name}.glb', f'{meshes}/{name}/{name}.obj')
                 if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(f'no mesh for {name} under {meshes}')
    m = trimesh.load(path, force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, int)
    if geom == 'mesh':
        return SampledSurface.from_mesh(v, f, spacing, name)
    if geom == 'pieces':
        pcs = sorted(glob.glob(f'{pieces_dir}/{name}/piece_*.obj'))
        if not pcs:
            raise FileNotFoundError(f'no pieces for {name} under {pieces_dir}')
        return SampledSurface.from_convex_pieces([np.asarray(trimesh.load(q).vertices) for q in pcs], spacing, name)
    from flash_chord.assets.mesh import convex_decompose               # geom == 'fc_hulls': the simulator's own pieces
    return SampledSurface.from_convex_pieces([np.asarray(h.vertices, float) for h in convex_decompose(v, f)], spacing, name)


def table_top(usda):
    """Top of the 'table' cylinder of our support USDA (translate z + height / 2)."""
    txt = open(usda).read(); import re
    h = float(re.search(r'double height\s*=\s*([-0-9.eE]+)', txt).group(1))
    z = float(re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', txt).group(1).split(',')[2])
    return z + h / 2


def phase_labels(ref_path, T, names, hand_world, obj_surf, OP, OR, table, d_pre, phases=None, obj_pts=None):
    """Per hand: (T,) arrays role ('A' approach window, 'X' transport window, '-' never modulated), target / held object
    index (-1 none). PHASES (hold_phases output) may be passed for tests; else it is read from the reference."""
    if phases is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hold_phases import hold_phases
        phases = hold_phases(ref_path)[0]['phases']
    idx = {n: i for i, n in enumerate(names)}
    held = {s: -np.ones(T, int) for s in ('left', 'right')}; spans = {s: [] for s in held}
    for ph in phases:
        s, k = ph['hand'], idx[ph['object']]
        sl = slice(ph['start'], ph['end']); free = held[s][sl] < 0
        held[s][sl] = np.where(free, k, held[s][sl]); spans[s].append((ph['start'], ph['end'] - 1, k))
    two = np.zeros(T, bool)
    for t in range(T):
        two[t] = held['left'][t] >= 0 and held['left'][t] == held['right'][t]

    obj_pts = obj_pts if obj_pts is not None else [o.P for o in obj_surf]

    def obj_samples(k, t):
        return OP[t, k] + obj_pts[k] @ OR[t, k].T

    def dist_to(q, k, t):                                         # min signed distance of world points q to object k at t
        d, _ = obj_surf[k].query((q - OP[t, k]) @ OR[t, k]); return float(d.min())

    out = {}
    for s in ('left', 'right'):
        role = np.array(['-'] * T, dtype='<U1'); target = -np.ones(T, int)
        sp = sorted(spans[s])
        for t in range(T):
            if held[s][t] < 0:
                nxt = [k for a, b, k in sp if a > t]; prv = [k for a, b, k in sp if b < t]
                target[t] = nxt[0] if nxt else (prv[-1] if prv else -1)
                near = [k for k in {nxt[0] if nxt else -1, prv[-1] if prv else -1} if k >= 0]
                if all(dist_to(hand_world[s][t], k, t) >= d_pre for k in near):   # not in a grasp / release zone
                    role[t] = 'A'
            else:
                target[t] = held[s][t]
        for a, b, k in sp:
            others = [j for j in range(len(names)) if j != k]

            def support(t):                                       # nearest of the other objects / table to object k
                q = obj_samples(k, t)
                c = [(dist_to(q, j, t), j) for j in others] + [(float(q[:, 2].min() - table), -2)]
                return min(c)[1]

            org, dst = support(a), support(b)

            def gap(t, j):
                q = obj_samples(k, t)
                return float(q[:, 2].min() - table) if j == -2 else dist_to(q, j, t)

            for t in range(a, b + 1):
                if held[s][t] == k and not two[t] and gap(t, org) >= d_pre and gap(t, dst) >= d_pre:
                    role[t] = 'X'
        out[s] = dict(role=role, target=target, held=held[s].copy(), two_handed=two.copy())
    return out


def modulate_reference(table, ref_path, meshes, urdf_dir, support_usda, prm=DEFAULTS, geom='fc_hulls', pieces_dir=None,
                       sides=('left', 'right')):
    """Returns (new pyarrow table, report dict, labels). Hands are processed left then right; the second hand sees the
    first hand's moved held object."""
    names = list(table.column('object_body_names')[0].as_py()); fps = float(table.column('fps')[0].as_py())
    T = len(col(table, 'robot_left_wrist_position').reshape(-1, 3)); B = len(names)
    OP = col(table, 'object_body_position').reshape(T, B, 3)
    OR = _quat_wxyz_to_mat(col(table, 'object_body_wxyz').reshape(T, B, 4))
    surf = [object_surface(n, meshes, geom, prm['obs_spacing'], pieces_dir) for n in names]
    bsurf = [s.coarse(prm['body_spacing']) for s in surf]      # coarser held-object samples (moving body)
    z_table = table_top(support_usda)
    W, F, links, Hw = {}, {}, {}, {}
    for s in ('left', 'right'):
        W[s] = col(table, f'robot_{s}_wrist_position').reshape(T, 3)
        F[s] = col(table, f'robot_{s}_frames').reshape(T, -1, 7)
        links[s] = load_hand_samples(urdf_dir, s, list(table.column(f'{s}_robot_frame_names')[0].as_py()), prm['body_spacing'])
        Hw[s] = hand_world(F[s], links[s])
    labels = phase_labels(ref_path, T, names, Hw, surf, OP, OR, z_table, prm['d_pre'], obj_pts=[b.P for b in bsurf])
    rep = dict(params=dict(prm), geom=geom, fps=fps, frames=T, objects=names, table_z=z_table, hands={})
    delta = {s: np.zeros((T, 3)) for s in ('left', 'right')}
    t0 = time.time()
    for s in sides:
        role, target = labels[s]['role'], labels[s]['target']
        vel = np.zeros((T, B, 3)); mv = np.r_[np.diff(OP, axis=0), np.zeros((1, B, 3))] * fps
        for o in ('left', 'right'):                            # objects carried by a hand move with their reference velocity
            for t in np.nonzero(labels[o]['held'] >= 0)[0]:
                vel[t, labels[o]['held'][t]] = mv[t, labels[o]['held'][t]]
        posed = [PosedObstacle(surf[k], OP[:, k], OR[:, k], vel[:, k]) for k in range(B)]
        hand_off = Hw[s] - W[s][:, None, :]
        wins = [(a, b, 'A') for a, b in runs(role == 'A')] + [(a, b, 'X') for a, b in runs(role == 'X')]
        rep['hands'][s] = []
        for a, b, kind in sorted(wins):
            if b - a < 2:
                continue
            kt = int(target[a])

            def lerp(arr, tf):
                i = int(np.floor(tf)); j = min(i + 1, T - 1); al = tf - i
                return (1 - al) * arr[i] + al * arr[j]

            def body_fn(tf, kind=kind, kt=kt):
                g = [(lerp(hand_off, tf), 'hand')]
                if kind == 'X':
                    i = int(round(tf)); i = min(i, T - 1)
                    g.append((OP[i, kt] + bsurf[kt].P @ OR[i, kt].T - lerp(W[s], tf), 'held'))
                return g

            obst = [(posed[k], ('hand', 'held')) for k in range(B) if k != kt]
            if kind == 'X':
                obst.append((HalfSpace(z_table), ('held',)))
            X, info = modulate_window(W[s], a, b, fps, body_fn, lambda tf, o=obst: o, prm)
            delta[s][a:b + 1] = X - W[s][a:b + 1]
            rep['hands'][s].append(dict(kind=kind, start=int(a), end=int(b), target=names[kt] if kt >= 0 else None, **info))
        # apply this hand's shift, and in transport its held object's, before the next hand is processed
        for t in np.nonzero(role == 'X')[0]:
            OP[t, target[t]] += delta[s][t]
    rep['seconds'] = round(time.time() - t0, 1)
    new = apply_delta(table, delta, labels, names)
    return new, rep, labels


def apply_delta(table, delta, labels, names):
    """Shift wrist positions and robot frames by delta[side]; in transport frames also the held object's position (and the
    root position when it is that body) and this hand's active MANO contact points."""
    import pyarrow as pa
    T = len(delta['left']); B = len(names)

    def put(tb, name, arr):
        i = tb.column_names.index(name)
        return tb.set_column(i, name, pa.array([np.asarray(arr).tolist()], type=tb.schema.field(name).type))

    OP = col(table, 'object_body_position').reshape(T, B, 3); OP0 = OP.copy()
    root = col(table, 'object_root_position').reshape(T, 3) if 'object_root_position' in table.column_names else None
    root_is0 = root is not None and np.allclose(root, OP0[:, 0], atol=1e-7)
    for s, d in delta.items():
        if not np.any(d):
            continue
        table = put(table, f'robot_{s}_wrist_position', col(table, f'robot_{s}_wrist_position').reshape(T, 3) + d)
        Fr = col(table, f'robot_{s}_frames'); Fr = Fr.reshape(T, -1, 7); Fr[..., :3] += d[:, None, :]
        table = put(table, f'robot_{s}_frames', Fr)
        X = labels[s]['role'] == 'X'; k = labels[s]['target']
        for c in (f'mano_{s}_object_contact_positions', f'mano_{s}_link_contact_positions'):
            if c not in table.column_names:
                continue
            C = col(table, c)
            if C.size == 0:
                continue
            C = C.reshape(T, -1, 3)
            pid = col(table, f'mano_{s}_object_contact_part_ids').reshape(T, -1).astype(int)
            for t in np.nonzero(X)[0]:
                act = pid[t] == k[t] + 1; C[t, act] += d[t]
            table = put(table, c, C)
        for t in np.nonzero(X)[0]:
            OP[t, k[t]] += d[t]
    if not np.array_equal(OP, OP0):
        table = put(table, 'object_body_position', OP.reshape(T, B, 3))
        if root_is0:
            table = put(table, 'object_root_position', OP[:, 0])
    return table


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--meshes', required=True, help='OUR object meshes (e.g. meshes/library_v3)')
    ap.add_argument('--hand_urdf_dir', required=True, help='FlashCHORD src/flash_chord/assets/urdfs/sharpawave')
    ap.add_argument('--support', help='support USDA (default: <ref tree>/reconstructed_stage/*_support.usda)')
    ap.add_argument('--geom', default='fc_hulls', choices=('fc_hulls', 'mesh', 'pieces'))
    ap.add_argument('--pieces_dir'); ap.add_argument('--report'); ap.add_argument('--phases_json')
    for k, v in DEFAULTS.items():
        ap.add_argument(f'--{k}', type=type(v), default=v)
    a = ap.parse_args()
    import pyarrow.parquet as pq
    prm = {k: getattr(a, k) for k in DEFAULTS}
    sup = a.support
    if sup is None:
        tree = os.path.abspath(a.inp).split('/processed/')[0]
        sup = sorted(glob.glob(f'{tree}/reconstructed_stage/*_support.usda'))[0]
    t = pq.read_table(a.inp)
    new, rep, lab = modulate_reference(t, os.path.abspath(a.inp), a.meshes, a.hand_urdf_dir, sup, prm, a.geom, a.pieces_dir)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); pq.write_table(new, a.out)
    rep.update(inp=os.path.abspath(a.inp), out=os.path.abspath(a.out), support=sup)
    if a.phases_json:
        json.dump({s: dict(role=''.join(v['role']), target=v['target'].tolist(), held=v['held'].tolist(),
                           two_handed=v['two_handed'].astype(int).tolist()) for s, v in lab.items()} | dict(objects=rep['objects']),
                  open(a.phases_json, 'w'))
    if a.report:
        json.dump(rep, open(a.report, 'w'), indent=1)
    print(json.dumps({s: [(w['kind'], w['start'], w['end'], round(w['max_dev_m'] * 100, 2)) for w in v]
                      for s, v in rep['hands'].items()}))


if __name__ == '__main__':
    main()
