"""Contact-anchored retargeting of a FlashCHORD reference (owner's idea, 2026-10-21): trust the object, fit the robot hand to it.

Evidence: E2S fits the Sharpa hand to the human wrist and scaled keypoints; the larger robot hand then sits 16-20 mm (p95)
inside the objects at 63-88 % of frames (ep12/27/18/24), and resetting to a contact frame pops the object in one physics
step. The human fingertips themselves sit 0.6-1.8 cm off the surfaces (never inside after mkref's depenetration).

Per hand and frame, starting from the E2S solution (wrist pose + 22 finger joints):
  1. contact targets: each human fingertip (MANO 4/8/12/16/20) within SNAP of an object surface is projected onto it
     (object SDF gradient) and offset outward by the robot tip site's depth under its pad; targets are smoothed per contact
     run in the object frame (window 5) to remove frame-to-frame jitter;
  2. solve wrist translation + rotation (at most MAX_SHIFT / MAX_TURN from E2S) and finger joints (joint limits) with
     least squares on the robot's own geometry (Newton forward kinematics of the FlashCHORD scene): the nearest distal-
     link surface point on each target (pseudo-Huber beyond ROBUST), no penetration as the simulator sees it (CPU MuJoCo
     collision of the scene's own convex pieces: objects, table and the other hand; CR_PEN=samples for the older
     hull-sample test), close to E2S, continuous with the previous frame. Frames without contact or penetration relax
     back toward E2S. Hands are solved left then right; the right sees the solved left.
  3. write the new wrist position / quaternion, finger joints and all 67 robot frames (rigid offsets to their links).
Usage (FlashCHORD python, run from the flash_chord dir, FC set):
  python contact_retarget.py IN_PARQUET OUT_PARQUET [--snap 0.025] [--margin 0.001] [--frames A:B]
OUT_PARQUET must sit in a reference tree with reconstructed_stage/ (the support USDA) like IN_PARQUET.
"""
import argparse, json, os, re, sys, time
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
from scipy.optimize import least_squares
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import uniform_filter1d
from scipy.spatial.transform import Rotation as Rot

FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')
MANO_TIPS = (4, 8, 12, 16, 20)
ROBUST = 0.015                                                     # tip errors beyond this pull with sqrt weight (m)
SIDES = {'left': 0, 'right': 29}                                    # joint_q offset of each hand (wrist xyz, quat xyzw, 22)


def build_scene(parquet, fc):
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    with initialize_config_dir(version_base='1.3', config_dir=f'{fc}/src/flash_chord/configs'):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"])
    env_config = instantiate_typed(cfg.env, RLEnvConfig)
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config)
    return st, env


class FK:
    """Newton forward kinematics of the whole scene on CPU; returns body poses (n, 7: p, quat xyzw)."""

    def __init__(self, model):
        import warp as wp, newton
        self.wp, self.newton, self.m = wp, newton, model
        self.q = model.joint_q.numpy().copy(); self.qd = wp.zeros(model.joint_dof_count, dtype=wp.float32, device='cpu')
        self.state = model.state()

    def __call__(self, q58):
        self.q[:58] = q58
        self.newton.eval_fk(self.m, self.wp.array(self.q, dtype=self.wp.float32, device='cpu'), self.qd, self.state)
        return self.state.body_q.numpy().copy()                     # .numpy() is a live view of one buffer


def hull_samples(V, n):
    """Vertices plus area-weighted points on the convex hull of V (what MuJoCo collides for a mesh geom)."""
    from scipy.spatial import ConvexHull
    try:
        h = ConvexHull(V)
    except Exception:
        return V[np.linspace(0, len(V) - 1, min(n, len(V))).astype(int)]
    P = V[h.vertices]; tri = V[h.simplices]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(0); k = rng.choice(len(tri), size=n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n); flip = u + v > 1; u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    S = tri[k, 0] + u[:, None] * (tri[k, 1] - tri[k, 0]) + v[:, None] * (tri[k, 2] - tri[k, 0])
    return np.vstack([P[np.linspace(0, len(P) - 1, min(n, len(P))).astype(int)], S])


def hand_geometry(model, side, max_pts=40):
    """Body ids, tip-site parents and collision-surface samples (body-local) of one hand."""
    import newton
    labels = list(getattr(model, 'body_label', None) or getattr(model, 'body_key', []))
    pre = f'{side}_sharpa_wave/'; bodies = {l[len(pre):]: i for i, l in enumerate(labels) if l.startswith(pre)}
    sb = model.shape_body.numpy(); flags = model.shape_flags.numpy(); tf = model.shape_transform.numpy()
    sc = model.shape_scale.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES)
    pts_b, pts_l = [], []
    inv = {v: k for k, v in bodies.items()}
    for s in range(model.shape_count):
        if sb[s] not in inv or not (int(flags[s]) & collide):
            continue
        src = model.shape_source[s]
        if src is None or not hasattr(src, 'vertices'):
            continue
        V = np.asarray(src.vertices, float) * sc[s]
        V = hull_samples(V, max_pts)
        V = Rot.from_quat(tf[s, 3:7]).apply(V) + tf[s, :3]
        pts_b.append(np.full(len(V), sb[s])); pts_l.append(V)
    return bodies, np.concatenate(pts_b), np.concatenate(pts_l)


def world_points(bq, body_ids, local):
    R = Rot.from_quat(bq[body_ids, 3:7]); return R.apply(local) + bq[body_ids, :3]


class ObjectSDF:
    """Signed distance (positive outside) on a grid in the object frame, trilinear."""

    def __init__(self, mesh_path, voxel=0.004, pad=0.03, cap=64):
        import trimesh
        m = trimesh.load(mesh_path, force='mesh'); lo, hi = m.bounds[0] - pad, m.bounds[1] + pad
        n = np.minimum(np.ceil((hi - lo) / voxel).astype(int) + 1, cap)
        axes = [np.linspace(lo[k], hi[k], n[k]) for k in range(3)]
        G = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
        d = -trimesh.proximity.signed_distance(m, G)               # trimesh: positive inside
        self.f = RegularGridInterpolator(axes, d.reshape(n), bounds_error=False, fill_value=None)
        self.lo, self.hi = lo, hi

    def __call__(self, P):
        return self.f(np.clip(P, self.lo, self.hi))

    def grad(self, P, h=0.002):
        g = np.stack([(self(P + e) - self(P - e)) / (2 * h) for e in np.eye(3) * h], -1)
        return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-9)


class HullSDF:
    """Signed distance (positive outside) to the union of the convex collision pieces of one object body, in its body
    frame: per piece max over face planes (exact inside, a lower bound outside), then the minimum over pieces."""

    def __init__(self, model, body, voxel=0.0025, pad=0.04, cap=160):
        import newton
        from scipy.spatial import ConvexHull
        sb = model.shape_body.numpy(); flags = model.shape_flags.numpy(); tf = model.shape_transform.numpy()
        sc = model.shape_scale.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES); self.planes = []; allv = []
        for s in range(model.shape_count):
            src = model.shape_source[s]
            if sb[s] != body or not (int(flags[s]) & collide) or src is None or not hasattr(src, 'vertices'):
                continue
            V = Rot.from_quat(tf[s, 3:7]).apply(np.asarray(src.vertices, float) * sc[s]) + tf[s, :3]
            self.planes.append(ConvexHull(V).equations); allv.append(V)  # n . x + d <= 0 inside
        if not self.planes:
            raise SystemExit(f'no collision pieces for body {body}')
        # exact plane tests per query cost ~9 s per solved frame: tabulate once on a grid and interpolate
        allv = np.vstack(allv); lo, hi = allv.min(0) - pad, allv.max(0) + pad
        n = np.minimum(np.ceil((hi - lo) / voxel).astype(int) + 1, cap)
        axes = [np.linspace(lo[k], hi[k], n[k]) for k in range(3)]
        G = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
        d = np.concatenate([self.exact(G[i:i + 100000]) for i in range(0, len(G), 100000)])
        self.f = RegularGridInterpolator(axes, d.reshape(n), bounds_error=False, fill_value=None); self.lo, self.hi = lo, hi

    def exact(self, P):
        P = np.atleast_2d(P)
        return np.min([np.max(P @ E[:, :3].T + E[:, 3], axis=1) for E in self.planes], axis=0)

    def __call__(self, P):
        P = np.atleast_2d(P); Q = np.clip(P, self.lo, self.hi)
        return self.f(Q) + np.linalg.norm(P - Q, axis=-1)           # beyond the grid: add the distance to it

    def grad(self, P, h=0.001):
        g = np.stack([(self(P + e) - self(P - e)) / (2 * h) for e in np.eye(3) * h], -1)
        return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-9)


class MjPen:
    """Hand penetration as the simulator sees it: CPU MuJoCo collision (Newton keeps the mj_model it hands to MuJoCo Warp:
    the same convex pieces, 0.3-0.7 ms per query; reproduces the warp contacts). frame(f) puts the scene at reference
    frame f (objects included); __call__(q58, side) returns, per collision geom of that hand, max(0, margin - depth)
    over its contacts with objects, the table and the other hand (geom margins set to MARGIN so near-contacts count)."""

    def __init__(self, env, margin):
        import mujoco
        self.mj, self.env, self.sol, self.m = mujoco, env, env.solver, env.solver.model
        self.mm = self.sol.mj_model; self.mm.geom_margin[:] = margin; self.md = mujoco.MjData(self.mm); self.margin = margin
        g2s = self.sol.mjc_geom_to_newton_shape.numpy(); g2s = g2s[0] if g2s.ndim == 2 else g2s
        sb = self.m.shape_body.numpy(); labels = list(getattr(self.m, 'body_label', None) or getattr(self.m, 'body_key', []))
        own = np.zeros(self.mm.ngeom, int)                         # 0 table/ground, 1 left, 2 right, 3 + body: objects
        for g in range(self.mm.ngeom):
            sh = g2s[g]
            if sh >= 0 and sb[sh] >= 0:
                lab = labels[sb[sh]].split('/')[-1]
                own[g] = 1 if lab.startswith('left_') else 2 if lab.startswith('right_') else 3 + sb[sh]
        self.own = own; self.geoms = {s: np.nonzero(own == k)[0] for s, k in (('left', 1), ('right', 2))}
        self.slot = {s: {g: i for i, g in enumerate(v)} for s, v in self.geoms.items()}
        self.state = self.m.state(); self.base = None

    def frame(self, f):
        self.env.reset(frame_id=f); self.base = self.env.state_0.joint_q.numpy().copy()

    def __call__(self, q58, side):
        q = self.base.copy(); q[:58] = q58; self.state.joint_q.assign(q.astype(np.float32))
        self.sol._update_mjc_data(self.md, self.m, self.state)
        self.mj.mj_kinematics(self.mm, self.md); self.mj.mj_collision(self.mm, self.md)
        out = np.zeros(len(self.geoms[side])); n = self.md.ncon; me = 1 if side == 'left' else 2
        if n:
            G = self.md.contact.geom[:n]; D = self.md.contact.dist[:n]; o0, o1 = self.own[G[:, 0]], self.own[G[:, 1]]
            for (g0, g1), d, a, b in zip(G, D, o0, o1):
                if a == b or (a != me and b != me):
                    continue
                i = self.slot[side][g0 if a == me else g1]; out[i] = max(out[i], self.margin - d)
        return np.maximum(out, 0)


def lm_solve(res, x0, h, iters=8, lo=None, hi=None):
    """Small Levenberg-Marquardt with explicit central-difference steps H (float32 kinematics and max(0, .) kinks make
    scipy's default tiny steps return a zero gradient). LO/HI clip the iterate."""
    x = x0.copy(); r = res(x); c = r @ r; mu = 1e-2
    for _ in range(iters):
        Jt = np.stack([(res(x + hi_ * e) - r) / hi_ for hi_, e in zip(h, np.eye(len(x)))])
        g = Jt @ r; A = Jt @ Jt.T
        while True:
            dx = -np.linalg.solve(A + mu * (np.diag(np.diag(A)) + 1e-9 * np.eye(len(x))), g)
            xn = x + dx
            if lo is not None:
                xn = np.clip(xn, lo, hi)
            rn = res(xn); cn = rn @ rn
            if cn < c:
                rel = (c - cn) / max(c, 1e-12); x, r, c = xn, rn, cn; mu = max(mu / 3, 1e-6); break
            mu *= 4
            if mu > 1e6:
                return x, c
        if rel < 1e-4:
            break
    return x, c


def parse_support(usda):
    s = open(usda).read()
    r = float(re.search(r'double radius = ([-0-9.e]+)', s).group(1)); h = float(re.search(r'double height = ([-0-9.e]+)', s).group(1))
    c = [float(x) for x in re.search(r'xformOp:translate = \(([^)]*)\)', s).group(1).split(',')]
    return np.array(c[:2]), r, c[2] + h / 2


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--snap', type=float, default=0.025, help='human fingertip within this of a surface = contact (m)')
    p.add_argument('--margin', type=float, default=0.001, help='clearance of hand surface samples (m)')
    p.add_argument('--max_shift', type=float, default=0.06, help='largest wrist translation from E2S per axis (m)')
    p.add_argument('--max_turn', type=float, default=0.5, help='largest wrist rotation from E2S per axis (rad)')
    p.add_argument('--frames', default=None, help='A:B only these frames (debug)')
    a = p.parse_args()
    fc = os.environ.get('FC', os.getcwd()); t0 = time.time()
    st, env = build_scene(os.path.abspath(a.inp), fc); m = st.scene.model
    mjp = MjPen(env, a.margin) if os.environ.get('CR_PEN', 'mj') == 'mj' else None   # CR_PEN=samples: hull samples vs SDF
    t = pq.read_table(a.inp); T = int(np.asarray(st.scene.robot_reference.joint_q).shape[0])
    qref = np.asarray(st.scene.robot_reference.joint_q, float).copy()
    names = t.column('object_body_names')[0].as_py(); paths = t.column('object_mesh_paths')[0].as_py()
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OR = [[Rot.from_quat(q) for q in np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, j][:, [1, 2, 3, 0]]] for j in range(len(names))]
    tree = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(a.inp)))))
    usda = [os.path.join(tree, 'reconstructed_stage', f) for f in os.listdir(os.path.join(tree, 'reconstructed_stage')) if f.endswith('.usda')][0]
    cxy, rdisc, ztop = parse_support(usda)
    blabels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    obj_body = [next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{n}/')) for n in names]
    sdfs = [HullSDF(m, b) for b in obj_body] if os.environ.get('CR_SDF', 'hull') == 'hull' else [ObjectSDF(pth) for pth in paths]
    print(f'[{time.time() - t0:.0f}s] scene + {len(sdfs)} object SDFs; table top {ztop:.3f} disc r {rdisc:.3f}', flush=True)
    fk = FK(m); lo_lim = m.joint_limit_lower.numpy(); hi_lim = m.joint_limit_upper.numpy()
    rng = range(T) if not a.frames else range(*[int(x) for x in a.frames.split(':')])
    q_new = qref.copy(); stats = {}

    def to_obj(j, f, X):                                           # world -> object j frame at frame f
        return OR[j][f].inv().apply(X - OP[f, j])

    for side, o in SIDES.items():
        bodies, pb, pl = hand_geometry(m, side)
        tip_parent = [bodies[f'{side}_{fn}_DP'] for fn in FINGERS]
        # tip-site offsets in their DP link frames, from the E2S frames (median over 10 frames)
        fnames = t.column(f'{side}_robot_frame_names')[0].as_py(); FR = np.array(t.column(f'robot_{side}_frames')[0].as_py(), float).reshape(T, -1, 7)
        offs = []
        for f in np.linspace(0, T - 1, 10).astype(int):
            bq = fk(qref[f]); row = []
            for k, fn in enumerate(FINGERS):
                b = tip_parent[k]; row.append(Rot.from_quat(bq[b, 3:7]).inv().apply(FR[f, fnames.index(f'{side}_{fn}_tip_site'), :3] - bq[b, :3]))
            offs.append(row)
        tip_local = np.median(np.array(offs), 0)
        dp_rows = [np.nonzero(pb == tip_parent[k])[0] for k in range(5)]   # distal-link surface samples (pad region)
        # depth of each tip site under its pad: distance to the nearest collision sample of its DP link
        depth = np.array([np.min(np.linalg.norm(pl[pb == tip_parent[k]] - tip_local[k], axis=1)) for k in range(5)])
        # 1) contact targets (object frame), smoothed per run
        J = np.array(t.column(f'mano_{side}_joints')[0].as_py(), float).reshape(T, 21, 3)
        tgt_obj = np.full((T, 5, 3), np.nan); tgt_id = np.full((T, 5), -1)
        for f in range(T):
            for k, ti in enumerate(MANO_TIPS):
                best = None
                for j, sdf in enumerate(sdfs):
                    x = to_obj(j, f, J[f, ti][None])[0]; d = float(sdf(x[None])[0])
                    if best is None or d < best[0]:
                        best = (d, j, x)
                d, j, x = best
                if d < a.snap:
                    g = sdfs[j].grad(x[None])[0]; tgt_obj[f, k] = x - (d - a.margin) * g; tgt_id[f, k] = j
        for k in range(5):                                         # smooth each contact run (same object) in its frame
            f = 0
            while f < T:
                if tgt_id[f, k] < 0:
                    f += 1; continue
                e = f
                while e < T and tgt_id[e, k] == tgt_id[f, k]:
                    e += 1
                if e - f < 3:
                    tgt_id[f:e, k] = -1; tgt_obj[f:e, k] = np.nan
                else:
                    tgt_obj[f:e, k] = uniform_filter1d(tgt_obj[f:e, k], 5, axis=0, mode='nearest')
                f = e
        # 2) per-frame solve, forward in time
        dof_lo = np.full(28, -np.inf); dof_hi = np.full(28, np.inf)
        jl = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', []))
        dstart = m.joint_qd_start.numpy(); jidx = {l: i for i, l in enumerate(jl)}
        fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
        for k, n_ in enumerate(fj):
            i = jidx[f'{side}_sharpa_wave/{n_}']; dof_lo[6 + k] = lo_lim[dstart[i]]; dof_hi[6 + k] = hi_lim[dstart[i]]
        prev = np.zeros(28); nopt = 0; pen_before = []; pen_after = []; tip_err = []
        scale = np.r_[np.full(3, 0.02), np.full(3, 0.3), np.full(22, 0.5)]
        cont = np.r_[np.full(3, 0.01), np.full(3, 0.1), np.full(22, 0.2)]

        def q_of(f, x):                                            # the other hand as solved so far
            q = q_new[f].copy(); q[o:o + 3] = qref[f, o:o + 3] + x[:3]
            q[o + 3:o + 7] = (Rot.from_rotvec(x[3:6]) * Rot.from_quat(qref[f, o + 3:o + 7])).as_quat()
            q[o + 7:o + 29] = np.clip(qref[f, o + 7:o + 29] + x[6:], dof_lo[6:], dof_hi[6:]); return q

        def penetration(f, bq, q=None):
            if mjp is not None:
                return mjp(q, side)
            X = world_points(bq, pb, pl); r = []
            for j, sdf in enumerate(sdfs):
                r.append(np.maximum(0, a.margin - sdf(to_obj(j, f, X))))
            on = np.linalg.norm(X[:, :2] - cxy, axis=1) < rdisc
            r.append(np.where(on, np.maximum(0, a.margin - (X[:, 2] - ztop)), 0))
            return np.concatenate(r)

        for f in rng:
            if mjp is not None:
                mjp.frame(f)
            q0 = q_of(f, prev * 0.8); pen = penetration(f, fk(q0), q0); has_c = (tgt_id[f] >= 0).any()
            qe = q_of(f, np.zeros(28)); pen_before.append(float(penetration(f, fk(qe), qe).max()))
            if not has_c and pen.max() <= a.margin:
                prev = prev * 0.8; q_new[f, o:o + 29] = q0[o:o + 29]; pen_after.append(float(pen.max())); continue
            ks = np.nonzero(tgt_id[f] >= 0)[0]
            tw = np.array([OR[tgt_id[f, k]][f].apply(tgt_obj[f, k]) + OP[f, tgt_id[f, k]] for k in ks]) if len(ks) else np.zeros((0, 3))

            def res(x):
                q = q_of(f, x); bq = fk(q)
                X = world_points(bq, pb, pl)
                tips = np.array([X[dp_rows[k]][np.argmin(np.linalg.norm(X[dp_rows[k]] - tw[i], axis=1))] for i, k in enumerate(ks)]) if len(ks) else np.zeros((0, 3))
                e = tips - tw; w = 1 / np.sqrt(np.maximum(1, np.linalg.norm(e, axis=1, keepdims=True) / ROBUST))  # pseudo-Huber
                return np.concatenate([(w * e / 0.005).ravel(), penetration(f, bq, q) / 0.002, x / scale, (x - prev) / cont])

            # wrist moves at most MAX_SHIFT / MAX_TURN from E2S: a contact the hand cannot reach without a larger move is
            # more likely a wrong target than a wrong hand (owner: "if the object and hand don't match, we made a mistake")
            lo_x = np.r_[np.full(3, -a.max_shift), np.full(3, -a.max_turn), dof_lo[6:] - qref[f, o + 7:o + 29]]
            hi_x = np.r_[np.full(3, a.max_shift), np.full(3, a.max_turn), dof_hi[6:] - qref[f, o + 7:o + 29]]
            x0 = np.clip(prev, lo_x, hi_x)
            xs, cs = lm_solve(res, x0, np.r_[np.full(3, 1e-3), np.full(25, 1e-2)], lo=lo_x, hi=hi_x)
            prev = xs; nopt += 1; qf = q_of(f, prev); q_new[f, o:o + 29] = qf[o:o + 29]; bq = fk(qf)
            pen_after.append(float(penetration(f, bq, qf).max()))
            if len(ks):
                X = world_points(bq, pb, pl)
                tips = np.array([X[dp_rows[k]][np.argmin(np.linalg.norm(X[dp_rows[k]] - tw[i], axis=1))] for i, k in enumerate(ks)])
                tip_err.extend(np.linalg.norm(tips - tw, axis=1).tolist())
            if f % 25 == 0:
                print(f'[{time.time() - t0:.0f}s] {side} f{f}: contacts {len(ks)}, pen {pen_before[-1] * 1000:.1f} -> {pen_after[-1] * 1000:.1f} mm, '
                      f'shift {np.linalg.norm(prev[:3]) * 100:.1f} cm', flush=True)
        stats[side] = dict(tip_site_depth_mm=np.round(depth * 1000, 1).tolist(), contact_frames=int((tgt_id >= 0).any(1).sum()),
                           optimised=nopt, pen_p95_mm_before=round(float(np.percentile(pen_before, 95) * 1000), 1),
                           pen_p95_mm_after=round(float(np.percentile(pen_after, 95) * 1000), 1),
                           tip_to_target_mm_median=round(float(np.median(tip_err) * 1000), 1) if tip_err else None,
                           tip_to_target_mm_p90=round(float(np.percentile(tip_err, 90) * 1000), 1) if tip_err else None)
        print(json.dumps({side: stats[side]}), flush=True)
    # 3) write: wrist, fingers, all robot frames (rigid offsets to their parent links, found on the E2S solution)
    out = t
    for side, o in SIDES.items():
        bodies, _, _ = hand_geometry(m, side, max_pts=1)
        fnames = t.column(f'{side}_robot_frame_names')[0].as_py(); FR = np.array(t.column(f'robot_{side}_frames')[0].as_py(), float).reshape(T, -1, 7)
        samp = np.linspace(0, T - 1, 4).astype(int); bq_ref = [fk(qref[f]) for f in samp]
        parent, rel = {}, {}
        for k, fn in enumerate(fnames):
            best = None
            for b in bodies.values():
                rels = []
                for i, f in enumerate(samp):
                    Rb = Rot.from_quat(bq_ref[i][b, 3:7]); Rf = Rot.from_quat(FR[f, k, [4, 5, 6, 3]])
                    rels.append(np.r_[Rb.inv().apply(FR[f, k, :3] - bq_ref[i][b, :3]), (Rb.inv() * Rf).as_quat()])
                rels = np.array(rels); spread = np.abs(rels[:, :3] - rels[0, :3]).max()
                if best is None or spread < best[0]:
                    best = (spread, b, rels[0])
            if best[0] < 1e-3:
                parent[k], rel[k] = best[1], best[2]
        newF = FR.copy()
        for f in range(T):
            bq = fk(q_new[f])
            for k, b in parent.items():
                Rb = Rot.from_quat(bq[b, 3:7]); pos = Rb.apply(rel[k][:3]) + bq[b, :3]; qx = (Rb * Rot.from_quat(rel[k][3:])).as_quat()
                newF[f, k] = np.r_[pos, qx[[3, 0, 1, 2]]]
        cols = {f'robot_{side}_wrist_position': q_new[:, o:o + 3], f'robot_{side}_wrist_wxyz': q_new[:, o + 3:o + 7][:, [3, 0, 1, 2]],
                f'robot_{side}_finger_joints': q_new[:, o + 7:o + 29], f'robot_{side}_frames': newF}
        for c, v in cols.items():
            i = out.column_names.index(c); out = out.set_column(i, c, pa.array([v.tolist()], type=out.schema.field(c).type))
        stats[side]['frames_rigidly_attached'] = f'{len(parent)}/{len(fnames)}'
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); pq.write_table(out, a.out)
    json.dump(stats, open(os.path.splitext(a.out)[0] + '_contact_retarget.json', 'w'), indent=1)
    print(f'[{time.time() - t0:.0f}s] wrote {a.out}', json.dumps(stats), flush=True)


if __name__ == '__main__':
    import warp as wp
    with wp.ScopedDevice('cpu'):
        main()
