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
patched into its target buffers; the planner worlds (raw residual input, EMA 0) are set to the truth state (joint_q/qd,
body_q/qd, MuJoCo warm start) before every rollout batch. CPU (--device cpu): WORKERS processes x WORLDS worlds (Warp's
CPU kernels are single-threaded). CUDA (--device cuda, 2026-10-30 port): one in-process planner env with WORLDS worlds
(WORKERS is ignored); the truth env runs on --truth_device (default: the same device).
--deadline_s bounds the wall time: past it, the remaining frames are committed without optimisation (warm-start plan
decaying to the reference) and no further rollbacks happen; the output is still a complete reference.

Usage (FlashCHORD python, run from the flash_chord dir):
  CPU:  EMB=sharpa_hands_mid python solve.py IN.parquet OUT.parquet [--workers 4 --worlds 24 --robust 4 --horizon 16
        --knot 4 --ctrl 4 --iters 4 --retries 4 --back 3]
  CUDA: EMB=sharpa_hands_mid python solve.py IN.parquet OUT.parquet --device cuda --worlds 1024 --robust 4 ...
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


def build_env(parquet, world_count, planner, device='cpu'):
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
    emb = instantiate_typed(cfg.embodiment, Embodiment)
    with wp.ScopedDevice(device):                       # every later call on this env runs under on(env)
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=emb,
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=world_count,
                         include_support=True, decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config)
    env.ps_embodiment = emb; env.ps_device = device
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


def on(env):
    """Run calls on env's device (the truth and planner envs may live on different devices in one process)."""
    import warp as wp
    return wp.ScopedDevice(env.ps_device)


def snapshot(env, world=0):
    """World `world`'s simulation state as host arrays (state, MuJoCo warm start, reference counters)."""
    W = env.world_count; s = env.state_0
    snap = {f: getattr(s, f).numpy().reshape(W, -1)[world].copy() for f in STATE_FIELDS}
    snap['qacc_warmstart'] = env.solver.mjw_data.qacc_warmstart.numpy()[world].copy()
    snap['timestep'] = int(env.timestep.numpy()[world]); snap['episode_step'] = int(env.episode_step.numpy()[world])
    return snap


def _fill(arr, row, W):
    """arr (a per-world warp array: W x row) <- row in every world, with one host-to-device copy (any device)."""
    import warp as wp
    L = getattr(arr.dtype, '_length_', 1) or 1
    row = np.asarray(row); host = np.broadcast_to(row[None], (W,) + row.shape)
    host = np.ascontiguousarray(host, dtype=np.int32 if arr.dtype == wp.int32 else np.float32)
    arr.assign(host.reshape(tuple(arr.shape) + ((L,) if L > 1 else ())))


def restore(env, snap):
    """Every world <- the snapshot (exact on CPU: checked bit-identical against a 1-world replay)."""
    W = env.world_count; s = env.state_0
    for f in STATE_FIELDS:
        _fill(getattr(s, f), snap[f], W)
    _fill(env.solver.mjw_data.qacc_warmstart, snap['qacc_warmstart'], W)
    _fill(env.timestep, np.int32(snap['timestep']), W); _fill(env.episode_step, np.int32(snap['episode_step']), W)


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
        import warp as wp
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
        with wp.ScopedDevice('cpu'):                      # the loader binds on the CPU whatever the simulation device
            for i in range(n):
                self.state.joint_q.assign(JQ[i])
                self.newton.eval_fk(self.model, self.state.joint_q, self.state.joint_qd, self.state)
                bq[i] = np.asarray(self.state.body_q.numpy(), dtype=np.float32).reshape(-1, 7)
        b = _bind_hand(bq, hand, JQ)                     # BoundHandReference: float32 re-normalised quaternion
        return np.asarray(b.wrist_pos_w), np.asarray(b.wrist_quat_w)[:, [1, 2, 3, 0]], np.asarray(b.finger_joint_pos)


# ---------------------------------------------------------------------------------------------- planner
class Planner:
    """W planner worlds of one env on one device. rollout(snap, U): every world <- snap, then world w plays the
    offsets U[w] (H frames) through FlashCHORD's residual action; returns the per-frame object cost (W, H)."""

    def __init__(self, parquet, W, cfg, device):
        import warp as wp
        self.wp = wp; self.W = W; self.cfg = cfg
        self.env, labels = build_env(parquet, W, planner=True, device=device)
        with on(self.env):
            self.env.reset(frame_id=0)   # required: an explicit reset sets the reset policy's VOC assist to the config's 0
        # and ends its reset hold; a never-reset env starts with VOC 1 and holds the reference frame (v1 bug)
        self.ref = Ref(parquet); self.nb = len(labels) // W
        self.ob = [labels.index(f'track3_{n}/object') for n in self.ref.names]
        buf = self.env.action.buffers; self.A = buf.layout.action_dim
        self.scale = buf.scale.numpy()[:self.A].astype(np.float64)
        self.pts = sphere_points(cfg['npts'])

    def rollout(self, snap, U):
        wp, env, ref, W = self.wp, self.env, self.ref, self.W
        H = U.shape[1]; t0 = snap['timestep']; cost = np.zeros((W, H))
        with on(env):
            restore(env, snap)
            for h in range(H):
                act = (U[:, h] / self.scale).astype(np.float32).reshape(-1)
                env.step(wp.array(act, dtype=wp.float32, device=env.ps_device))
                q = env.state_0.body_q.numpy().reshape(W, self.nb, 7)[:, self.ob].astype(np.float64)
                k = min(t0 + h + 1, ref.T - 1)
                d = add_dist(q, ref.OP[k], ref.OQ[k], self.pts)   # (W, B)
                c = np.minimum(d, self.cfg['clip']).sum(-1)
                c[~np.isfinite(c)] = 10.0
                cost[:, h] = c
        return cost


def worker_main(conn, parquet, W, cfg):
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    import warp as wp
    wp.config.log_level = wp.LOG_WARNING
    pl = Planner(parquet, W, cfg, 'cpu')
    conn.send(dict(ready=True, A=pl.A, nb=pl.nb))
    while True:
        msg = conn.recv()
        if msg[0] == 'quit':
            break
        _, snap, U = msg                                    # U: (W, H, A) physical offsets
        conn.send(pl.rollout(snap, U))


class Workers:
    """CPU: the planner worlds split over worker processes (same interface as Planner)."""

    def __init__(self, parquet, n, W, cfg):
        import multiprocessing as mp
        ctx = mp.get_context('spawn'); self.conns = []; self.W = W
        for _ in range(n):
            c1, c2 = ctx.Pipe(); ctx.Process(target=worker_main, args=(c2, parquet, W, cfg), daemon=True).start()
            self.conns.append(c1)
        self.A = [c.recv() for c in self.conns][0]['A']

    def rollout(self, snap, UW):
        for i, c in enumerate(self.conns):
            c.send(('rollout', snap, UW[i * self.W:(i + 1) * self.W]))
        return np.concatenate([c.recv() for c in self.conns], 0)

    def close(self):
        for c in self.conns:
            c.send(('quit',))


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
    p.add_argument('--device', default=os.environ.get('DEV', 'cpu'), help='planner device: cpu (worker processes) or cuda')
    p.add_argument('--truth_device', default='', help='truth env device (default: --device)')
    p.add_argument('--deadline_s', type=float, default=0.0, help='> 0: past this wall time, commit the rest without '
                   'optimisation and without rollbacks (bounded box time)')
    p.add_argument('--early_rel', type=float, default=0.0, help='> 0: early stop of a replan\'s iterations (Do as I Do: '
                   'improvement < 0.01 for 2 checks): stop once the best sample beats sample 0 (the current mean) by less '
                   'than EARLY_REL x J0 in EARLY_N consecutive iterations, after at least MIN_ITERS')
    p.add_argument('--early_n', type=int, default=2); p.add_argument('--min_iters', type=int, default=4)
    p.add_argument('--pace_s', type=float, default=0.0, help='> 0: pacing; when the solve loop is behind PACE_S seconds per '
                   'committed frame, a replan runs only MIN_ITERS iterations and no boosted (rollback) iterations')
    p.add_argument('--start_state', default='', help='solve from a recorded simulator state instead of frame 0: a '
                   'tools/trace_rollout.py STATE=1 npz (e.g. the policy\'s rollout); --t0 = its reference frame. Offsets '
                   'stay zero before t0 (2026-10-31, solver<->RL loop)')
    p.add_argument('--t0', type=int, default=0)
    p.add_argument('--record', action='store_true', help='also store the truth\'s full state per committed frame (jq, jqd, '
                   'qd, qw, es as trace_rollout STATE=1) and its contacts (cl as CONTACTS=2) in OUT_solve.npz')
    p.add_argument('--seed', type=int, default=0)
    # --method grasp (2026-11-01): GRASP's window optimiser (tools/physics_solve/grasp_window.py) instead of the annealed
    # sampler, with the SAME cost, robust copies, commit, rollbacks and rollout budget (ITERS batches per replan)
    p.add_argument('--method', default='anneal', choices=('anneal', 'grasp'))
    p.add_argument('--g_rho', type=float, default=0.9, help='AR(1) knot correlation (GRASP hands: 0.9)')
    p.add_argument('--g_sig', type=float, default=0.8, help='AR(1) innovation width = G_SIG x SIG_* x the RAMP factor')
    p.add_argument('--g_sig_abs', type=float, nargs=3, default=None, metavar=('POS', 'ROT', 'FIN'),
                   help='absolute AR(1) innovation widths (m, rad, rad) x the RAMP factor instead of G_SIG x SIG_* '
                   '(GRASP hands: 0.0044 0.0044 0.044 = sigma 0.0044, finger channel scale 10)')
    p.add_argument('--g_beta', type=float, default=100.0, help='beta = G_BETA / J(warm start) of the window')
    p.add_argument('--g_ess', type=float, default=0.9); p.add_argument('--g_moves', type=int, default=2)
    p.add_argument('--g_step', type=float, default=0.59, help='MALA step in prior widths (GRASP hands 0.0026 / 0.0044)')
    p.add_argument('--g_acc', type=float, default=0.05); p.add_argument('--g_rate', type=float, default=3.0)
    p.add_argument('--g_step_min', type=float, default=0.1)
    p.add_argument('--g_rank', type=int, default=2); p.add_argument('--g_quad', default='diag', choices=('diag', 'full'))
    p.add_argument('--g_ridge', type=float, default=1e-3); p.add_argument('--g_window', type=float, default=3.0)
    p.add_argument('--g_carry', type=float, default=0.5, help='share of the next window\'s initial particles carried '
                   'from this window\'s final population (lowest cost first), shifted by the commit')
    a = p.parse_args(); t_start = time.time(); rng = np.random.default_rng(a.seed)
    a.truth_device = a.truth_device or a.device
    import pyarrow as pa
    import pyarrow.parquet as pq
    import warp as wp
    wp.config.log_level = wp.LOG_WARNING
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import grasp_window as GW

    ref = Ref(a.inp); T = ref.T; B = len(ref.names)
    log_path = os.path.splitext(a.out)[0] + '_solve.log'; LOG = open(log_path, 'w')

    def log(*x):
        s = ' '.join(str(v) for v in x); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
    log(f'{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} solve {a.inp} -> {a.out} T={T} objects={ref.names} args={vars(a)}')

    cfgw = dict(clip=a.clip, npts=a.npts)
    if a.device == 'cpu' and a.workers > 0:            # Warp CPU kernels are single-threaded: one process per core
        planner = Workers(os.path.abspath(a.inp), a.workers, a.worlds, cfgw); NW = a.workers * a.worlds
    else:                                              # one in-process env with all planner worlds (CUDA; or
        # --workers 0 on CPU, which runs the CUDA code path on the CPU for testing)
        planner = Planner(os.path.abspath(a.inp), a.worlds, cfgw, a.device); NW = a.worlds
    truth, labels = build_env(os.path.abspath(a.inp), 1, planner=False, device=a.truth_device)
    buf = truth.action.buffers; lay = buf.layout; A = lay.action_dim; sides = lay.sides; starts = lay.hand_action_starts
    nf = lay.finger_counts; nh = len(sides)
    rclip = buf.clip.numpy()[:A].astype(np.float64)                      # residual clips per action dim
    model = truth.model; fd = np.array(lay.finger_dof_ids)
    lo_all, hi_all = model.joint_limit_lower.numpy()[fd].astype(float), model.joint_limit_upper.numpy()[fd].astype(float)
    lo = [lo_all[lay.hand_finger_starts[h]:lay.hand_finger_starts[h] + nf[h]] for h in range(nh)]
    hi = [hi_all[lay.hand_finger_starts[h]:lay.hand_finger_starts[h] + nf[h]] for h in range(nh)]
    assert planner.A == A
    log(f'[{time.time() - t_start:.0f}s] planner {a.device}: {NW} worlds' + (f' ({a.workers} workers x {a.worlds})' if isinstance(planner, Workers) else ' (in-process)')
        + f', truth on {a.truth_device}; action dim {A}, sides {sides}')
    nb = len(labels); ob = [labels.index(f'track3_{n}/object') for n in ref.names]
    pts = sphere_points(a.npts)
    # truth reference buffers (views): patched with the committed offsets frame by frame
    RB = buf.reference                                   # host copies, written back with assign (any device)
    rb_pos = RB.wrist_pos_w.numpy().reshape(T, nh, 3).copy(); rb_q = RB.wrist_quat_w.numpy().reshape(T, nh, 4).copy()
    rb_f = RB.finger_joint_pos.numpy().reshape(T, -1).copy()
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
    with on(truth):
        truth.reset(frame_id=0)
    t = 0
    if a.start_state:                                   # continue from a recorded state (the policy's, at frame t0)
        tr = np.load(a.start_state); fr_ = [int(x) for x in tr['frame']]
        i0 = fr_.index(a.t0)                            # first row of that frame (a trace ends with the viewer's reset)
        snap0 = dict(joint_q=tr['jq'][i0], joint_qd=tr['jqd'][i0], body_q=tr['q'][i0].reshape(-1), body_qd=tr['qd'][i0],
                     qacc_warmstart=tr['qw'][i0], timestep=a.t0, episode_step=int(tr['es'][i0]))
        with on(truth):
            restore(truth, snap0)
        t = a.t0
        log(f'[{time.time() - t_start:.0f}s] start state: {os.path.basename(a.start_state)} row {i0} (frame {a.t0})')
    REC = {k: [] for k in ('jq', 'jqd', 'qd', 'qw', 'es', 'cl')}

    def rec_state():                                    # --record: the truth's state (world 0) and contacts, per row
        if not a.record:
            return
        REC['jq'].append(truth.state_0.joint_q.numpy().copy()); REC['jqd'].append(truth.state_0.joint_qd.numpy().copy())
        REC['qd'].append(truth.state_0.body_qd.numpy().reshape(-1).copy())
        REC['qw'].append(truth.solver.mjw_data.qacc_warmstart.numpy()[0].copy()); REC['es'].append(int(truth.episode_step.numpy()[0]))
        rows = []
        if len(REC['jq']) > 1:                          # the first row (reset or restore) has no step contacts
            from flash_chord.runtime.contact import read_contacts_w
            rd = read_contacts_w(truth.model, truth.state_0, truth.contacts); i = len(REC['jq']) - 1
            for b0, b1, p_, n_, f_ in zip(rd.body0_ids, rd.body1_ids, rd.contact_pos_w, rd.contact_normal_w, rd.contact_force_w):
                rows.append([i, int(b0), int(b1), *p_, *n_, float(np.dot(f_, n_))])
        REC['cl'].append(rows)
    Q = [truth.state_0.body_q.numpy().copy()]; FR = [t]; rec_state()
    replans = []; chunks = []; boost, boost_until, retries = 0, -1, 0; deadline_t = None
    gcarry = None                                      # --method grasp: samples carried to the next window
    t_loop0 = time.time(); n_paced = 0
    nk = a.horizon // a.knot + 1
    while t < stop:
        H = min(a.horizon, T - 1 - t); C = min(a.ctrl, H)
        win = np.arange(t, t + H + 1)
        active = [h for h in range(nh) if near[win, h].any()] if a.f0 <= t <= f1 else []
        if a.deadline_s > 0 and time.time() - t_start > a.deadline_s:
            if deadline_t is None:
                deadline_t = t; log(f'[{time.time() - t_start:.0f}s] deadline {a.deadline_s:.0f} s reached at t={t}: the rest is committed without optimisation')
            active = []
        row = dict(t=t, H=H, active=[sides[h] for h in active]); t_rep = time.time()
        if active:
            snap = snapshot(truth)
            dims = np.concatenate([hand_dims[h] for h in active])
            mean = plan[:H].copy(); mean[:, np.setdiff1d(np.arange(A), dims)] = 0.0
            ramp = np.logspace(np.log10(a.ramp[0]), np.log10(a.ramp[1]), nk)
            kpos = np.linspace(0, a.horizon - 1, nk)
            Mint = np.stack([np.interp(np.arange(H), kpos, np.eye(nk)[k]) for k in range(nk)], 1)   # (H, nk)
            K = max(1, a.robust); N = NW // K; best = (np.inf, None, None); hist = []
            bst = boost if t < boost_until else 0
            n_it = a.iters * (1 + bst)
            if a.pace_s > 0 and time.time() - t_loop0 > a.pace_s * (t + C):   # behind schedule: cheapest replan
                n_it, bst = min(a.min_iters, a.iters), 0; n_paced += 1; row['paced'] = True
            row['boost'] = bst; small = 0

            def clipf(X):                                      # offsets inside FlashCHORD's residual clips (0.2 m, 1 rad,
                X = np.clip(X, -rclip[None, None], rclip[None, None])   # 1 rad: the planner's action path clips
                for h in active:                               # there; v3 did not, see the doc); finger targets no
                    s = sides[h]; s0 = starts[h] + 6; fr = ref.fing[s][t:t + H]   # further outside the joint limits
                    # than the reference itself (zero offset stays zero)
                    lo_, hi_ = np.minimum(lo[h], fr), np.maximum(hi[h], fr)
                    X[:, :, s0:s0 + nf[h]] = np.clip(fr[None] + X[:, :, s0:s0 + nf[h]], lo_[None], hi_[None]) - fr[None]
                return X
            for it in range(n_it if a.method == 'anneal' else 0):
                eps = rng.normal(size=(N, nk, len(dims))) * (sig[dims] * (np.sqrt(2.0) ** bst) * (a.anneal ** (it % a.iters)))[None, None] * ramp[None, :, None]
                eps[0] = 0.0
                noise = np.zeros((N, H, A))                    # knots -> frames: linear interpolation as a matrix
                noise[:, :, dims] = np.einsum('hk,nkd->nhd', Mint, eps)
                U = mean[None] + noise
                if t == 0:
                    U[:, 0] = 0.0                              # frame 0 is the reset pose: never edited
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
                cost_w = planner.rollout(snap, UW.astype(np.float64))[:N * K].reshape(N, K, -1)   # (N, K, H)
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
                if a.early_rel > 0:                            # Do as I Do's early stop (improvement of the best over sample 0)
                    small = small + 1 if float(J[0] - J[i_best]) < a.early_rel * max(float(J[0]), 1e-9) else 0
                    if small >= a.early_n and it + 1 >= a.min_iters:
                        row['early_stop_it'] = it + 1; break
                k = max(2, int(round(a.top * N))); top = np.argsort(J)[:k]
                r = -J[top]; r = (r - r.mean()) / (r.std() + 1e-2); w = np.exp(r / a.temperature); w /= w.sum()
                mean = np.einsum('i,iha->ha', w, U[top])
            if a.method == 'grasp':
                # GRASP window: the robust copies' target noise is drawn ONCE per window (common to every candidate and
                # every batch), so J is a deterministic function of the plan and the MH test on it is exact
                jit = np.zeros((K, H, A))
                if K > 1:
                    for h in active:
                        s0 = starts[h]
                        jit[1:, :, s0:s0 + 3] = rng.normal(size=(K - 1, H, 3)) * a.rob_pos
                        jit[1:, :, s0 + 6:s0 + 6 + nf[h]] = rng.normal(size=(K - 1, H, nf[h])) * a.rob_fin
                mean0 = mean.copy()

                def evaluate(Xk, mean0=mean0, jit=jit, dims=dims, H=H, K=K, N=N):
                    n_ = len(Xk); noise = np.zeros((n_, H, A))
                    noise[:, :, dims] = np.einsum('hk,nkd->nhd', Mint, Xk)
                    U = mean0[None] + noise
                    if t == 0:
                        U[:, 0] = 0.0                          # frame 0 is the reset pose: never edited
                    U = clipf(U)
                    UW = np.repeat(U, K, axis=0)
                    if K > 1:
                        UW = clipf(UW + np.tile(jit, (n_, 1, 1)))
                    UW = np.concatenate([UW, np.repeat(UW[:1], NW - len(UW), 0)], 0) if len(UW) < NW else UW
                    cost_w = planner.rollout(snap, UW.astype(np.float64))[:n_ * K].reshape(n_, K, -1)
                    reg = np.zeros((n_, H))
                    for h in active:
                        s0 = starts[h]
                        reg += (a.w_pos * np.linalg.norm(U[:, :, s0:s0 + 3], axis=-1) + a.w_rot * np.linalg.norm(U[:, :, s0 + 3:s0 + 6], axis=-1)
                                + a.w_fin * np.linalg.norm(U[:, :, s0 + 6:s0 + 6 + nf[h]], axis=-1))
                    wts = np.ones(H); wts[-1] = a.terminal
                    J = ((cost_w + reg[:, None]) * wts).sum(-1).mean(1) / wts.sum()
                    return J, [(U[i].copy(), cost_w[i, 0].copy()) for i in range(n_)]
                if a.g_sig_abs:
                    gs = np.zeros(A)
                    for h in range(nh):
                        s0 = starts[h]; gs[s0:s0 + 3], gs[s0 + 3:s0 + 6], gs[s0 + 6:s0 + 6 + nf[h]] = a.g_sig_abs
                    Dk = gs[dims][None] * ramp[:, None] * (np.sqrt(2.0) ** bst)
                else:
                    Dk = a.g_sig * sig[dims][None] * ramp[:, None] * (np.sqrt(2.0) ** bst)
                carry = None
                if (gcarry is not None and gcarry['t'] == t and np.array_equal(gcarry['dims'], dims) and a.g_carry > 0):
                    Up = gcarry['U'][:, gcarry['C']:]                     # shift by the commit, then the plan's decaying tail
                    tl = Up[:, -1:] * np.linspace(1.0, 0.0, a.horizon - Up.shape[1] + 1)[1:][None, :, None]
                    Us = np.concatenate([Up, tl], 1)[:, :H]
                    dev = (Us - mean0[None, :H])[:, :, dims]
                    m_ = int(a.g_carry * N); carry = np.einsum('kh,nhd->nkd', np.linalg.pinv(Mint), dev)[:m_]
                res = GW.run(evaluate, Dk, a.g_rho, N, n_it, rng, beta_rel=a.g_beta, ess=a.g_ess, moves=a.g_moves,
                             step=a.g_step, acc_target=a.g_acc, acc_rate=a.g_rate, step_min=a.g_step_min, rank=a.g_rank,
                             quad=a.g_quad, ridge=a.g_ridge, window=a.g_window, carry=carry, log=log)
                best = (res['best_J'], res['best_aux'][0], res['best_aux'][1])
                order = np.argsort(res['pop_J'])
                popx = res['pop_x'][order]
                pn = np.zeros((len(popx), H, A)); pn[:, :, dims] = np.einsum('hk,nkd->nhd', Mint, popx)
                gcarry = dict(t=t + C, dims=dims.copy(), C=C, U=clipf(mean0[None] + pn))
                hist = [dict(it=i, J0=round(res['J0'], 5), **hh) for i, hh in enumerate(res['hist'])] or [dict(it=0, J0=round(res['J0'], 5))]
                best_from = ('grasp', res['used'], res['archive'], len(carry) if carry is not None else 0)
            chosen = best[1]; row.update(J_warm=hist[0]['J0'], J_best=round(best[0], 5), iters=hist, best_from=best_from,
                                        pred_obj_cost=round(float(best[2][:C].mean()), 5))
        else:
            chosen = plan[:H].copy(); gcarry = None
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
        with on(truth):
            RB.wrist_pos_w.assign(rb_pos.reshape(-1, 3)); RB.wrist_quat_w.assign(rb_q.reshape(-1, 4))
            RB.finger_joint_pos.assign(rb_f.reshape(-1))
        real = []
        for k in range(C):
            with on(truth):
                truth.step(None)
            q = truth.state_0.body_q.numpy().copy(); Q.append(q); FR.append(int(truth.timestep.numpy()[0])); rec_state()
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
        if lost and a.retries > 0 and retries < a.retries and deadline_t is None:
            e = chunks[max(0, len(chunks) - a.back)]; ib = chunks.index(e)
            with on(truth):
                restore(truth, e['snap'])
            del Q[e['nQ']:]; del FR[e['nQ']:]; offsets[e['t']:] = 0.0; plan = e['plan'].copy()
            for k_ in REC:
                del REC[k_][e['nQ']:]
            boost = boost + 1 if t - C < boost_until else 1; boost_until = t; retries += 1
            log(f'  rollback {retries}/{a.retries}: {[ref.names[j] for j in lost]} lost at frame {t}; back to t={e["t"]}, boost {boost}')
            replans[-1]['rollback_to'] = e['t']; t = e['t']; del chunks[ib:]; gcarry = None
        elif not lost and t >= boost_until:
            boost = 0
        if len(replans) % 5 == 0:
            np.savez_compressed(os.path.splitext(a.out)[0] + '_solve_partial.npz', offsets=offsets, t=t)
    if isinstance(planner, Workers):
        planner.close()
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
    extra = {}
    if a.record:                                        # trace_rollout layout (STATE=1, CONTACTS=2)
        extra = dict(jq=np.array(REC['jq'], np.float32), jqd=np.array(REC['jqd'], np.float32), qd=np.array(REC['qd'], np.float32),
                     qw=np.array(REC['qw'], np.float32), es=np.array(REC['es']),
                     cl=np.array([r for rows in REC['cl'] for r in rows], np.float64).reshape(-1, 10))
    np.savez_compressed(os.path.splitext(a.out)[0] + '_solve.npz', offsets=offsets, q=np.array(Q, np.float32),
                        frame=np.array(FR), labels=np.array(labels), t0=a.t0, **extra)
    n_iters = [len(r['iters']) for r in replans if 'iters' in r]
    json.dump(dict(args=vars(a), T=T, objects=ref.names, moving=moving.tolist(), replans=replans, deadline_t=deadline_t,
                   rollbacks=retries, paced_replans=n_paced, mean_iters=round(float(np.mean(n_iters)), 2) if n_iters else None,
                   wall_s=round(time.time() - t_start, 1)), open(os.path.splitext(a.out)[0] + '_solve.json', 'w'), indent=1)
    log(f'[{time.time() - t_start:.0f}s] wrote {a.out} (+ _solve.json/.npz); truth trajectory {len(Q)} frames')
    # check: a fresh load of the written parquet gives bit-identical target buffers to the patched truth env
    fresh, _ = build_env(os.path.abspath(a.out), 1, planner=False, device=a.truth_device); FB = fresh.action.buffers.reference
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
