"""Physics solver (2026-10-30): receding-horizon sampling MPC that searches, INSIDE FlashCHORD (the scored simulator:
Newton + MuJoCo-Warp, 20 Hz x 5 substeps, our embodiment), for wrist-pose and finger-target offsets that make the
simulated objects follow OUR reference object trajectory. Output: the input reference parquet with the offsets folded
into its target columns (robot_<side>_wrist_position / _wrist_wxyz / _finger_joints), so a plain zero-action replay
(tools/trace_rollout.py zero) plays the optimised trajectory and RL can train on it.

Method (an independent re-implementation of the idea, not their code): annealed sampling MPC as in SPIDER
(Pan et al., arXiv 2511.09484, CC BY-NC 4.0: no code copied) and Do as I Do (arXiv 2606.19333, code MIT,
github.com/malik-group/do-as-i-do @ 824591b, retargeting/retargeting/utils/sampling.py: knot noise with a log ramp
over the horizon, per-iteration annealing beta = final^(1/iters), softmax over the top 10 % of normalised rewards,
receding-horizon warm start with the appended segment blended to the reference). Differences from both: no separate
MuJoCo model (FlashCHORD's own worlds are the rollouts, so there is no sim-to-sim gap), the decision variables are
FlashCHORD's own residual channels (wrist position m, wrist rotation rpy rad, finger targets rad), the cost is the
kit's ADD point distance on a 5 cm sphere (clipped at 10 cm, like the 1-9 cm AUC), and the committed window is the
lowest-cost evaluated sequence (sample 0 of iteration 0 is the warm start, so a commit never predicts worse than it).
Options: --robust K scores each candidate on K copies (copy 0 nominal, the others with per-frame target noise; cf. Do as
I Do's perturbed copies); --retries N rolls the truth back BACK chunks when a moving object is lost and re-plans with
more iterations and noise (cf. SPIDER's difficulty boosting). No contact guidance, no penetration term.
Finding (2026-10-30, docs/research/physics-2026-10-30/physics-solver.md): at CPU budgets the nominal gains do not
survive 0.5 mm target noise (tools/physics_solve/jitter_check.py) - judge outputs by the jittered mean, not copy 0.

Inputs: the reference parquet only (object poses = our perception; NO ground truth is read). Object names / order,
URDFs and the support come from the parquet's reference tree, as for any replay.
Processes: the master holds a 1-world "truth" env = the zero-action replay of the reference with the committed offsets
patched into its target buffers; N workers hold W-world planner envs (raw residual input, EMA 0) whose worlds are
reset to the truth state (joint_q/qd, body_q/qd, MuJoCo warm start) before every rollout batch.

Usage (FlashCHORD python, run from the flash_chord dir, CPU):
  EMB=sharpa_hands_mid python solve.py IN.parquet OUT.parquet [--workers 4 --worlds 12 --horizon 16 --knot 4
        --ctrl 4 --iters 3] [--f0 0 --f1 -1]
Writes OUT.parquet, OUT_solve.json (args, per-replan log, timing), OUT_solve.npz (offsets, truth trajectory in the
tools/trace_rollout.py npz layout: q, frame, labels).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time

import numpy as np

OFF = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]


def build_env(parquet, world_count, planner):
    """FlashCHORD RLEnv as tools/trace_rollout.py zero builds it (VOC 0, no termination, no auto-reset). planner=True:
    raw residual input with EMA 0, so action = offset / scale exactly (zero action is identical either way)."""
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    ov = ['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + OFF
    ov += [f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []
    ov += ['action.input_mode=raw', 'action.ema=0.0'] if planner else []
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=ov)
    env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
    wp.set_device('cpu')
    emb = instantiate_typed(cfg.embodiment, Embodiment)
    st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                     embodiment=emb,
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=world_count,
                     include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config); env.ps_embodiment = emb
    labels = list(getattr(st.scene.model, 'body_label', None) or getattr(st.scene.model, 'body_key', []))
    return env, labels


class Ref:
    """Reference arrays from the parquet (our perception; no ground truth)."""

    def __init__(self, path):
        import pyarrow.parquet as pq
        self.table = t = pq.read_table(path)
        g = lambda c: t.column(c)[0].as_py()  # noqa: E731
        self.names = g('object_body_names'); B = len(self.names)
        self.T = T = len(g('robot_left_wrist_position'))
        self.OP = np.array(g('object_body_position'), float).reshape(T, B, 3)
        self.OQ = np.array(g('object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]   # xyzw
        self.radius = np.array(g('object_mesh_radius'), float)
        self.wpos, self.wquat, self.fing, self.frames = {}, {}, {}, {}
        for s in ('right', 'left'):
            self.wpos[s] = np.array(g(f'robot_{s}_wrist_position'), float).reshape(T, 3)
            self.wquat[s] = np.array(g(f'robot_{s}_wrist_wxyz'), float).reshape(T, 4)
            self.fing[s] = np.array(g(f'robot_{s}_finger_joints'), float).reshape(T, -1)
            self.frames[s] = np.array(g(f'robot_{s}_frames'), float).reshape(T, -1, 7)[:, :, :3]


def sphere_points(n=64, r=0.05, seed=0):
    p = np.random.default_rng(seed).normal(size=(n, 3)); return r * p / np.linalg.norm(p, axis=1, keepdims=True)


def quat_xyzw_to_mat(q):
    x, y, z, w = (q[..., i] for i in range(4))
    return np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                     2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                     2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1).reshape(q.shape[:-1] + (3, 3))


def add_dist(sim_q, ref_p, ref_q, pts):
    """ADD (m): mean distance of sphere points; sim_q (..., B, 7) [x y z qx qy qz qw], ref (B, 3) / (B, 4 xyzw)."""
    Ms, Mr = quat_xyzw_to_mat(sim_q[..., 3:7]), quat_xyzw_to_mat(ref_q)
    d = np.einsum('...bij,vj->...bvi', Ms - Mr, pts) + (sim_q[..., :3] - ref_p)[..., None, :]
    return np.linalg.norm(d, axis=-1).mean(-1)


# ---------------------------------------------------------------------------------------------- state transfer
STATE_FIELDS = ('joint_q', 'joint_qd', 'body_q', 'body_qd')


def snapshot(env, world=0):
    W = env.world_count; s = env.state_0
    snap = {f: getattr(s, f).numpy().reshape(W, -1)[world].copy() for f in STATE_FIELDS}
    snap['qacc_warmstart'] = env.solver.mjw_data.qacc_warmstart.numpy()[world].copy()
    snap['timestep'] = int(env.timestep.numpy()[world]); snap['episode_step'] = int(env.episode_step.numpy()[world])
    return snap


def restore(env, snap):
    """Every world <- the snapshot (CPU warp arrays: numpy() is a view, so writes go to the simulator)."""
    W = env.world_count; s = env.state_0
    for f in STATE_FIELDS:
        getattr(s, f).numpy().reshape(W, -1)[:] = snap[f][None]
    env.solver.mjw_data.qacc_warmstart.numpy()[:] = snap['qacc_warmstart'][None]
    env.timestep.numpy()[:] = snap['timestep']; env.episode_step.numpy()[:] = snap['episode_step']


class ExactTargets:
    """Target buffers exactly as FlashCHORD's loader makes them from a parquet: values stored as float32
    (pyarrow schema), read back as float64 (as_py), quaternion normalised in float64 (data/mano_sharpa.py), cast to
    float32 into joint_q (embodiments/sharpa_hands.py bind_reference), Newton FK of a ROBOT-ONLY model built the way
    scene/builder.py builds the binding copy, palm frame and the float32 re-normalisation via binding._bind_hand. The scene model's FK differs from
    the binding model's by 1 float32 ulp on some frames, and such differences change contact outcomes, so the truth env
    is patched only through this path (bit-identity with a fresh replay is checked by --verify)."""

    def __init__(self, env):
        import newton
        self.newton = newton
        b = newton.ModelBuilder(); self.layout = env.ps_embodiment.build(b)
        self.jq0 = np.asarray(b.joint_q, dtype=np.float32)
        self.model = b.finalize(device='cpu', skip_all_validations=True)
        self.state = self.model.state(); self.state.joint_qd.zero_()

    def __call__(self, side, pos64, wxyz64, fing64):
        from flash_chord.embodiments.binding import _bind_hand
        hand = self.layout.hand(side)
        st = lambda x: np.asarray(np.asarray(x, dtype=np.float32), dtype=np.float64)   # noqa: E731  parquet round trip
        pos, q, fing = st(pos64), st(wxyz64), st(fing64)
        q = q / np.linalg.norm(q, axis=-1, keepdims=True)
        n = len(pos); JQ = np.tile(self.jq0, (n, 1))
        JQ[:, list(hand.wrist_pos_q_ids)] = pos.astype(np.float32)
        JQ[:, hand.wrist_orient_q_id:hand.wrist_orient_q_id + 4] = q.astype(np.float32)[:, [1, 2, 3, 0]]
        JQ[:, list(hand.finger_q_ids)] = fing.astype(np.float32)
        bq = np.empty((n, self.model.body_count, 7), np.float32)
        for i in range(n):
            self.state.joint_q.assign(JQ[i])
            self.newton.eval_fk(self.model, self.state.joint_q, self.state.joint_qd, self.state)
            bq[i] = np.asarray(self.state.body_q.numpy(), dtype=np.float32).reshape(-1, 7)
        b = _bind_hand(bq, hand, JQ)                     # BoundHandReference: float32 re-normalised quaternion
        return np.asarray(b.wrist_pos_w), np.asarray(b.wrist_quat_w)[:, [1, 2, 3, 0]], np.asarray(b.finger_joint_pos)


# ---------------------------------------------------------------------------------------------- worker
def worker_main(conn, parquet, W, cfg):
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    import warp as wp
    wp.config.log_level = wp.LOG_WARNING
    env, labels = build_env(parquet, W, planner=True)
    env.reset(frame_id=0)   # required: an explicit reset sets the reset policy's VOC assist to the config's 0 and ends its
    # reset hold; a never-reset env starts with VOC 1 and holds the reference frame for voc_decay_steps (v1 bug)
    ref = Ref(parquet); nb = len(labels) // W
    ob = [labels.index(f'track3_{n}/object') for n in ref.names]
    buf = env.action.buffers; A = buf.layout.action_dim
    scale = buf.scale.numpy()[:A].astype(np.float64)
    pts = sphere_points(cfg['npts'])
    conn.send(dict(ready=True, A=A, nb=nb))
    while True:
        msg = conn.recv()
        if msg[0] == 'quit':
            break
        _, snap, U = msg                                    # U: (W, H, A) physical offsets
        restore(env, snap); t0 = snap['timestep']; H = U.shape[1]
        cost = np.zeros((W, H))
        for h in range(H):
            act = (U[:, h] / scale).astype(np.float32).reshape(-1)
            env.step(wp.array(act, dtype=wp.float32, device='cpu'))
            q = env.state_0.body_q.numpy().reshape(W, nb, 7)[:, ob].astype(np.float64)
            k = min(t0 + h + 1, ref.T - 1)
            d = add_dist(q, ref.OP[k], ref.OQ[k], pts)       # (W, B)
            c = np.minimum(d, cfg['clip']).sum(-1)
            c[~np.isfinite(c)] = 10.0
            cost[:, h] = c
        conn.send(cost)


# ---------------------------------------------------------------------------------------------- master
def fold(ref, offsets, sides, starts, nf, lo, hi):
    """Fold per-frame physical offsets (T, A) into the parquet target values (float64): side -> (pos, wxyz, fingers)."""
    sl = slice(0, len(offsets))
    return {s: fold_slice(ref, s, offsets, starts[h], nf[h], lo[h], hi[h], sl) for h, s in enumerate(sides)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--workers', type=int, default=4); p.add_argument('--worlds', type=int, default=12)
    p.add_argument('--horizon', type=int, default=16); p.add_argument('--knot', type=int, default=4)
    p.add_argument('--ctrl', type=int, default=4); p.add_argument('--iters', type=int, default=3)
    p.add_argument('--sig_pos', type=float, default=0.01); p.add_argument('--sig_rot', type=float, default=0.05)
    p.add_argument('--sig_fin', type=float, default=0.10)
    p.add_argument('--ramp', type=float, nargs=2, default=(1.0, 3.0), help='noise multiplier at the first / last knot')
    p.add_argument('--anneal', type=float, default=0.5, help='noise factor per iteration')
    p.add_argument('--temperature', type=float, default=1.0); p.add_argument('--top', type=float, default=0.1)
    p.add_argument('--w_pos', type=float, default=0.1); p.add_argument('--w_rot', type=float, default=0.03)
    p.add_argument('--w_fin', type=float, default=0.01); p.add_argument('--terminal', type=float, default=3.0)
    p.add_argument('--clip', type=float, default=0.10, help='per-object ADD clip in the cost (m)')
    p.add_argument('--npts', type=int, default=64)
    p.add_argument('--gate', type=float, default=0.10, help='a hand is optimised while a reference hand frame is within '
                   'this distance (m) of a moving object\'s bounding sphere in the horizon')
    p.add_argument('--move', type=float, default=0.02, help='an object "moves" if its reference travels more than this (m)')
    p.add_argument('--f0', type=int, default=0); p.add_argument('--f1', type=int, default=-1,
                   help='optimise only frames f0..f1 (the rest is played with zero offset); -1 = to the end')
    p.add_argument('--stop', type=int, default=-1, help='debug: stop the solve at this frame and write what exists')
    p.add_argument('--retry', type=float, default=0.05, help='rollback trigger: a moving object\'s ADD crosses this (m)')
    p.add_argument('--retries', type=int, default=0, help='total rollbacks allowed in the episode (0 = off, as v1)')
    p.add_argument('--back', type=int, default=2, help='chunks to go back on a rollback')
    p.add_argument('--robust', type=int, default=1, help='K: each candidate runs as K worlds, copy 0 nominal, copies 1..K-1 '
                   'with fresh per-frame target noise (common to all candidates of an iteration); J = mean over copies '
                   '(Do as I Do evaluates 4 perturbed copies per sample; here target noise like tools/physics_solve/jitter_check.py)')
    p.add_argument('--rob_pos', type=float, default=0.0005); p.add_argument('--rob_fin', type=float, default=0.005)
    p.add_argument('--seed', type=int, default=0)
    a = p.parse_args(); t_start = time.time(); rng = np.random.default_rng(a.seed)
    import multiprocessing as mp
    import pyarrow as pa
    import pyarrow.parquet as pq
    import warp as wp
    wp.config.log_level = wp.LOG_WARNING

    ref = Ref(a.inp); T = ref.T; B = len(ref.names)
    log_path = os.path.splitext(a.out)[0] + '_solve.log'; LOG = open(log_path, 'w')

    def log(*x):
        s = ' '.join(str(v) for v in x); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
    log(f'{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} solve {a.inp} -> {a.out} T={T} objects={ref.names} args={vars(a)}')

    ctx = mp.get_context('spawn'); conns, procs = [], []
    cfgw = dict(clip=a.clip, npts=a.npts)
    for i in range(a.workers):
        c1, c2 = ctx.Pipe(); pr = ctx.Process(target=worker_main, args=(c2, os.path.abspath(a.inp), a.worlds, cfgw), daemon=True)
        pr.start(); conns.append(c1); procs.append(pr)
    truth, labels = build_env(os.path.abspath(a.inp), 1, planner=False)
    buf = truth.action.buffers; lay = buf.layout; A = lay.action_dim; sides = lay.sides; starts = lay.hand_action_starts
    nf = lay.finger_counts; nh = len(sides)
    rclip = buf.clip.numpy()[:A].astype(np.float64)                      # residual clips per action dim
    model = truth.model; fd = np.array(lay.finger_dof_ids)
    lo_all, hi_all = model.joint_limit_lower.numpy()[fd].astype(float), model.joint_limit_upper.numpy()[fd].astype(float)
    lo = [lo_all[lay.hand_finger_starts[h]:lay.hand_finger_starts[h] + nf[h]] for h in range(nh)]
    hi = [hi_all[lay.hand_finger_starts[h]:lay.hand_finger_starts[h] + nf[h]] for h in range(nh)]
    for c in conns:
        info = c.recv(); assert info['A'] == A
    log(f'[{time.time() - t_start:.0f}s] {a.workers} workers x {a.worlds} worlds ready; action dim {A}, sides {sides}')
    nb = len(labels); ob = [labels.index(f'track3_{n}/object') for n in ref.names]
    pts = sphere_points(a.npts)
    # truth reference buffers (views): patched with the committed offsets frame by frame
    RB = buf.reference
    rb_pos = RB.wrist_pos_w.numpy().reshape(T, nh, 3); rb_q = RB.wrist_quat_w.numpy().reshape(T, nh, 4)
    rb_f = RB.finger_joint_pos.numpy().reshape(T, -1)
    rb0 = (rb_pos.copy(), rb_q.copy(), rb_f.copy())                       # the loader's own values (zero offset)
    exact = ExactTargets(truth)

    # per-dimension noise scale and hand masks
    sig = np.zeros(A); hand_dims = []
    for h in range(nh):
        s0 = starts[h]; sig[s0:s0 + 3] = a.sig_pos; sig[s0 + 3:s0 + 6] = a.sig_rot; sig[s0 + 6:s0 + 6 + nf[h]] = a.sig_fin
        hand_dims.append(np.arange(s0, s0 + 6 + nf[h]))
    # gate: moving objects, hand near them (reference only)
    travel = np.linalg.norm(ref.OP - ref.OP[:1], axis=-1).max(0)
    ang = np.array([np.degrees(np.arccos(np.clip(np.abs(np.sum(ref.OQ[:, j] * ref.OQ[:1, j], -1)), 0, 1)) * 2).max() for j in range(B)])
    moving = (travel > a.move) | (ang > 10.0)
    near = np.zeros((T, nh), bool)
    for h, s in enumerate(sides):
        d = np.linalg.norm(ref.frames[s][:, :, None] - ref.OP[:, None], axis=-1).min(1) - ref.radius[None]   # (T, B)
        near[:, h] = (d[:, moving] < a.gate).any(1) if moving.any() else False
    log(f'moving objects {[n for n, m in zip(ref.names, moving)]} (travel cm {np.round(100 * travel, 1).tolist()}, '
        f'rot deg {np.round(ang, 0).tolist()}); hand-near frames {dict(zip(sides, near.sum(0).tolist()))}')

    f1 = T - 1 if a.f1 < 0 else min(a.f1, T - 1); stop = T - 1 if a.stop < 0 else min(a.stop, T - 1)
    offsets = np.zeros((T, A)); plan = np.zeros((a.horizon, A))
    truth.reset(frame_id=0)
    Q = [truth.state_0.body_q.numpy().copy()]; FR = [0]
    replans = []; t = 0; chunks = []; boost, boost_until, retries = 0, -1, 0
    nk = a.horizon // a.knot + 1
    while t < stop:
        H = min(a.horizon, T - 1 - t); C = min(a.ctrl, H)
        win = np.arange(t, t + H + 1)
        active = [h for h in range(nh) if near[win, h].any()] if a.f0 <= t <= f1 else []
        row = dict(t=t, H=H, active=[sides[h] for h in active]); t_rep = time.time()
        if active:
            snap = snapshot(truth)
            dims = np.concatenate([hand_dims[h] for h in active])
            mean = plan[:H].copy(); mean[:, np.setdiff1d(np.arange(A), dims)] = 0.0
            ramp = np.logspace(np.log10(a.ramp[0]), np.log10(a.ramp[1]), nk)
            kpos = np.linspace(0, a.horizon - 1, nk)
            NW = a.workers * a.worlds; K = max(1, a.robust); N = NW // K; best = (np.inf, None, None); hist = []
            bst = boost if t < boost_until else 0; row['boost'] = bst
            for it in range(a.iters * (1 + bst)):
                eps = rng.normal(size=(N, nk, len(dims))) * (sig[dims] * (np.sqrt(2.0) ** bst) * (a.anneal ** (it % a.iters)))[None, None] * ramp[None, :, None]
                eps[0] = 0.0
                noise = np.zeros((N, H, A))
                for j in range(len(dims)):
                    noise[:, :, dims[j]] = np.array([np.interp(np.arange(H), kpos, eps[i, :, j]) for i in range(N)])
                U = mean[None] + noise
                if t == 0:
                    U[:, 0] = 0.0                              # frame 0 is the reset pose: never edited
                def clipf(X):                                  # offsets inside FlashCHORD's residual clips (0.2 m, 1 rad,
                    X = np.clip(X, -rclip[None, None], rclip[None, None])   # 1 rad: the planner's action path clips
                    for h in active:                           # there; v3 did not, see the doc); finger targets no
                        s = sides[h]; s0 = starts[h] + 6; fr = ref.fing[s][t:t + H]   # further outside the joint limits
                        # than the reference itself (zero offset stays zero)
                        lo_, hi_ = np.minimum(lo[h], fr), np.maximum(hi[h], fr)
                        X[:, :, s0:s0 + nf[h]] = np.clip(fr[None] + X[:, :, s0:s0 + nf[h]], lo_[None], hi_[None]) - fr[None]
                    return X
                U = clipf(U)
                UW = np.repeat(U, K, axis=0)                   # world c*K + k runs candidate c, copy k
                if K > 1:
                    jit = np.zeros((K, H, A))
                    for h in active:
                        s0 = starts[h]
                        jit[1:, :, s0:s0 + 3] = rng.normal(size=(K - 1, H, 3)) * a.rob_pos
                        jit[1:, :, s0 + 6:s0 + 6 + nf[h]] = rng.normal(size=(K - 1, H, nf[h])) * a.rob_fin
                    UW = clipf(UW + np.tile(jit, (N, 1, 1)))
                UW = np.concatenate([UW, np.repeat(UW[:1], NW - len(UW), 0)], 0) if len(UW) < NW else UW
                for i, c in enumerate(conns):
                    c.send(('rollout', snap, UW[i * a.worlds:(i + 1) * a.worlds].astype(np.float64)))
                cost_w = np.concatenate([c.recv() for c in conns], 0)[:N * K].reshape(N, K, -1)   # (N, K, H)
                cost_obj = cost_w[:, 0]                                                 # nominal copy
                reg = np.zeros((N, H))
                for h in active:
                    s0 = starts[h]
                    reg += (a.w_pos * np.linalg.norm(U[:, :, s0:s0 + 3], axis=-1) + a.w_rot * np.linalg.norm(U[:, :, s0 + 3:s0 + 6], axis=-1)
                            + a.w_fin * np.linalg.norm(U[:, :, s0 + 6:s0 + 6 + nf[h]], axis=-1))
                wts = np.ones(H); wts[-1] = a.terminal
                J = ((cost_w + reg[:, None]) * wts).sum(-1).mean(1) / wts.sum()        # mean over the K copies
                i_best = int(np.argmin(J))
                if J[i_best] < best[0]:
                    best = (float(J[i_best]), U[i_best].copy(), cost_obj[i_best].copy()); best_from = (it, i_best)
                hist.append(dict(it=it, J0=round(float(J[0]), 5), Jbest=round(float(J[i_best]), 5), Jmed=round(float(np.median(J)), 5)))
                k = max(2, int(round(a.top * N))); top = np.argsort(J)[:k]
                r = -J[top]; r = (r - r.mean()) / (r.std() + 1e-2); w = np.exp(r / a.temperature); w /= w.sum()
                mean = np.einsum('i,iha->ha', w, U[top])
            chosen = best[1]; row.update(J_warm=hist[0]['J0'], J_best=round(best[0], 5), iters=hist, best_from=best_from,
                                        pred_obj_cost=round(float(best[2][:C].mean()), 5))
        else:
            chosen = plan[:H].copy()
        # commit C frames on the truth env (reference buffers patched with the folded offsets; zero action)
        offsets[t:t + C] = chosen[:C]
        sl = slice(t, t + C); fs = [slice(lay.hand_finger_starts[h], lay.hand_finger_starts[h] + nf[h]) for h in range(nh)]
        chunks.append(dict(t=t, snap=snapshot(truth), plan=plan.copy(), nQ=len(Q), add=add_dist(Q[-1][ob].astype(np.float64), ref.OP[t], ref.OQ[t], pts)))
        for h, s in enumerate(sides):                          # every committed frame is (re)written: rollback-safe
            rb_pos[sl, h], rb_q[sl, h], rb_f[sl, fs[h]] = rb0[0][sl, h], rb0[1][sl, h], rb0[2][sl, fs[h]]
            nz = np.any(offsets[sl][:, hand_dims[h]] != 0, axis=1)   # zero-offset frames keep the loader's values,
            if nz.any():                                       # as in the written parquet
                P32, Q32, F32 = exact(s, *fold_slice(ref, s, offsets[sl], starts[h], nf[h], lo[h], hi[h], sl))
                rb_pos[sl, h][nz], rb_q[sl, h][nz] = P32[nz], Q32[nz]
                rb_f[sl, fs[h]][nz] = F32[nz]
        real = []
        for k in range(C):
            truth.step(None)
            q = truth.state_0.body_q.numpy().copy(); Q.append(q); FR.append(int(truth.timestep.numpy()[0]))
            kk = min(t + k + 1, T - 1)
            real.append(float(np.minimum(add_dist(q[ob].astype(np.float64), ref.OP[kk], ref.OQ[kk], pts), a.clip).sum()))
        row['real_obj_cost'] = round(float(np.mean(real)), 5)
        add_now = add_dist(Q[-1][ob].astype(np.float64), ref.OP[min(t + C, T - 1)], ref.OQ[min(t + C, T - 1)], pts)
        row['add_cm'] = np.round(100 * add_now, 1).tolist(); row['sec'] = round(time.time() - t_rep, 1)
        replans.append(row)
        log(f'[{time.time() - t_start:.0f}s] t={t} {row.get("active")} J warm {row.get("J_warm", "-")} best {row.get("J_best", "-")} {row.get("best_from", "")} '
            f'pred {row.get("pred_obj_cost", "-")} real {row["real_obj_cost"]} ADD cm {row["add_cm"]} ({row["sec"]} s)')
        # receding horizon: shift, append the last offset decaying to zero (Do as I Do's blend to the reference)
        tail = chosen[C:]
        if len(tail) == 0:
            tail = chosen[-1:]
        app = tail[-1:] * np.linspace(1.0, 0.0, a.horizon - len(tail) + 1)[1:, None]
        plan = np.concatenate([tail, app], 0)[:a.horizon]
        t += C
        # rollback (SPIDER's "difficulty boosting", here with an exact restore of the truth env): a moving object that
        # was within RETRY of the reference at the chunk start and is beyond it at the chunk end was just lost ->
        # go back BACK chunks and re-plan them with (1 + boost) x iterations and sqrt(2)^boost x noise
        lost = [j for j in range(B) if moving[j] and chunks[-1]['add'][j] <= a.retry and add_now[j] > a.retry]
        if lost and a.retries > 0 and retries < a.retries:
            e = chunks[max(0, len(chunks) - a.back)]; ib = chunks.index(e)
            restore(truth, e['snap']); del Q[e['nQ']:]; del FR[e['nQ']:]; offsets[e['t']:] = 0.0; plan = e['plan'].copy()
            boost = boost + 1 if t - C < boost_until else 1; boost_until = t; retries += 1
            log(f'  rollback {retries}/{a.retries}: {[ref.names[j] for j in lost]} lost at frame {t}; back to t={e["t"]}, boost {boost}')
            replans[-1]['rollback_to'] = e['t']; t = e['t']; del chunks[ib:]
        elif not lost and t >= boost_until:
            boost = 0
        if len(replans) % 5 == 0:
            np.savez_compressed(os.path.splitext(a.out)[0] + '_solve_partial.npz', offsets=offsets, t=t)
    for c in conns:
        c.send(('quit',))
    # the rest (debug --stop): zero offsets; last frame keeps the previous frame's offset (never used in a replay)
    if stop == T - 1:
        offsets[T - 1] = offsets[T - 2]
    fo = fold(ref, offsets, sides, starts, nf, lo, hi)
    out = ref.table
    for h, s in enumerate(sides):
        pos, wxyz, fing = fo[s]
        z = ~np.any(offsets[:, hand_dims[h]] != 0, axis=1)                 # untouched frames: original values
        pos[z], wxyz[z], fing[z] = ref.wpos[s][z], ref.wquat[s][z], ref.fing[s][z]
        for col, v in ((f'robot_{s}_wrist_position', pos), (f'robot_{s}_wrist_wxyz', wxyz), (f'robot_{s}_finger_joints', fing)):
            i = out.column_names.index(col); out = out.set_column(i, col, pa.array([v.tolist()], type=out.schema.field(col).type))
    pq.write_table(out, a.out)
    np.savez_compressed(os.path.splitext(a.out)[0] + '_solve.npz', offsets=offsets, q=np.array(Q, np.float32),
                        frame=np.array(FR), labels=np.array(labels))
    json.dump(dict(args=vars(a), T=T, objects=ref.names, moving=moving.tolist(), replans=replans,
                   wall_s=round(time.time() - t_start, 1)), open(os.path.splitext(a.out)[0] + '_solve.json', 'w'), indent=1)
    log(f'[{time.time() - t_start:.0f}s] wrote {a.out} (+ _solve.json/.npz); truth trajectory {len(Q)} frames')
    # check: a fresh load of the written parquet gives bit-identical target buffers to the patched truth env
    fresh, _ = build_env(os.path.abspath(a.out), 1, planner=False); FB = fresh.action.buffers.reference
    same = {k: bool(np.array_equal(getattr(FB, k).numpy(), getattr(RB, k).numpy())) for k in ('wrist_pos_w', 'wrist_quat_w', 'finger_joint_pos')}
    log(f'[{time.time() - t_start:.0f}s] fresh load of {os.path.basename(a.out)}: target buffers bit-identical to the truth env: {same}')


def fold_slice(ref, s, off_rows, a0, nfh, lo, hi, sl):
    """Folded float64 values for frames sl of one side, from offset rows (len(sl), A): wrist position + offset,
    wrist quaternion * quat_rpy(offset) (FlashCHORD's residual composition), finger targets + offset clipped to limits."""
    from scipy.spatial.transform import Rotation as R
    dp = off_rows[:, a0:a0 + 3]; dr = off_rows[:, a0 + 3:a0 + 6]; df = off_rows[:, a0 + 6:a0 + 6 + nfh]
    pos = ref.wpos[s][sl] + dp
    q0 = ref.wquat[s][sl] / np.linalg.norm(ref.wquat[s][sl], axis=1, keepdims=True)
    q = (R.from_quat(q0[:, [1, 2, 3, 0]]) * R.from_euler('xyz', dr)).as_quat()
    q[np.sum(q * q0[:, [1, 2, 3, 0]], 1) < 0] *= -1.0
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    return pos, q[:, [3, 0, 1, 2]], ref.fing[s][sl] + df          # df is already limit-clipped by the sampler


if __name__ == '__main__':
    main()
