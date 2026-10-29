"""Physics grasp search for one hold phase (2026-10-23; owner: "secure grasp is more important than replicating it",
then "the grasp angle and position come second but are also very important"; docs/research/notes/23).
Starts from a grasp-lock reference (pipeline/grasp_lock.py, optionally wrist_ilc.py) and tries, in one FlashCHORD scene
with many worlds (evaluator physics: VOC 0, no termination), grasp variants around the locked grasp:
  ALONG  shift along the object's long axis (cm),  DOWN  shift down in world z (cm; hands pass through the table),
  ROLL   rotation of the hand about the object's long axis (deg),  SQUEEZE  extra flexion on top of the reference (rad),
  APPROACH  where the hand comes from: an offset (SIDE cm along the object's horizontal cross axis, BELOW cm down) held
         until APPROACH_IN frames before the hold and then slid in. Without it the hand came down ON the eval ep3 spoon
         handle (target 2 cm below the table top, inside the space under the handle) and stayed on top of it.
Each variant runs TRIALS times with different smooth wrist disturbances (NOISE_CM / NOISE_DEG random walk = pushes).
The variant is applied as a constant residual action (raw mode: residual = action x scale), from the approach start
FRAMES before the hold to HOLD frames into it. A trial holds when the object does not slip in the hand: its position
in the hand (C_MC) frame stays within SLIP_CM of where it was when the fingers had closed (CLOSE frames after the hold
start) to the end of the window, and it was lifted with the hand (path error is reported too, but it mixes the soft
wrist's own tracking error with the grasp).
Choice (security first, closeness to the human grasp second): among variants holding in >= MIN_RATE of the trials,
the one closest to the human grasp (|along, down| cm + |roll| / 15 deg); if none reaches MIN_RATE, the highest rate,
then the closest. Our reference only, no ground truth.
Usage (FlashCHORD python, from the flash_chord dir):
  grasp_search.py REF.parquet OUT.json --hand right --object wooden_spoon --start H0 [--frames 70] [--approach 10]
"""
import argparse, dataclasses, itertools, json, os, time

import numpy as np
import pyarrow.parquet as pq
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as Rot

SCALE = dict(pos=0.05, rot=0.15, finger=0.15); CLIP = dict(pos=0.2, rot=1.0, finger=1.0)


def floats(s):
    return [float(x) for x in s.split(',')]


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('out')
    p.add_argument('--hand', default='right'); p.add_argument('--object', default='wooden_spoon'); p.add_argument('--start', type=int, required=True)
    p.add_argument('--approach', type=int, default=10); p.add_argument('--frames', type=int, default=70)
    p.add_argument('--along', default='-4,-2,0,2,4'); p.add_argument('--down', default='0,-1,-2'); p.add_argument('--roll', default='-30,-15,0,15,30')
    p.add_argument('--squeeze', default='0,0.3'); p.add_argument('--trials', type=int, default=2)
    p.add_argument('--side', default='0'); p.add_argument('--below', default='0'); p.add_argument('--approach_in', type=int, default=4)
    p.add_argument('--noise_cm', type=float, default=1.0); p.add_argument('--noise_deg', type=float, default=3.0)
    p.add_argument('--hold_cm', type=float, default=3.0); p.add_argument('--min_rate', type=float, default=0.8)
    p.add_argument('--slip_cm', type=float, default=2.0); p.add_argument('--close', type=int, default=6)
    a = p.parse_args(); t0 = time.time()
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene

    t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); j = names.index(a.object)
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)[:, j]
    OR = Rot.from_quat(np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, j][:, [1, 2, 3, 0]])
    WP = np.array(t.column(f'robot_{a.hand}_wrist_position')[0].as_py(), float).reshape(T, 3)
    WR = Rot.from_quat(np.array(t.column(f'robot_{a.hand}_wrist_wxyz')[0].as_py(), float).reshape(T, 4)[:, [1, 2, 3, 0]])
    fj = t.column(f'{a.hand}_robot_finger_joint_names')[0].as_py()
    flex = np.array([any(k in n for k in ('_FE', '_PIP', '_DIP', '_IP')) for n in fj], float)
    f0 = max(0, a.start - a.approach); f1 = min(T, a.start + a.frames)
    grid = list(itertools.product(floats(a.along), floats(a.down), floats(a.roll), floats(a.squeeze), floats(a.side), floats(a.below)))
    W = len(grid) * a.trials
    off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{os.path.abspath(a.ref)}'",
                                                               'action.input_mode=raw'] + off)
    env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
    with wp.ScopedDevice('cuda'):
        st = setup_scene(parquet=os.path.abspath(a.ref), control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment), collision=instantiate_typed(cfg.collision, CollisionPolicy),
                         world_count=W, include_support=True, decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config); m = st.scene.model
        labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', [])); bpw = m.body_count // W
        ob0 = next(i for i, l in enumerate(labels) if l.startswith(f'track3_{a.object}/')); obj_ids = ob0 + bpw * np.arange(W)
        # object long axis (object frame) from its collision pieces; grasp point = nearest axis point to the wrist at H0
        sb = m.shape_body.numpy(); V = np.vstack([np.asarray(m.shape_source[s].vertices, float) * m.shape_scale.numpy()[s] for s in range(m.shape_count)
                                                   if sb[s] == ob0 and m.shape_source[s] is not None and hasattr(m.shape_source[s], 'vertices')])
        c0 = V.mean(0); axes = np.linalg.svd(V - c0, full_matrices=False)[2]; axis = axes[0]
        wl = OR[a.start].inv().apply(WP[a.start] - OP[a.start]); cg = c0 + axis * np.dot(wl - c0, axis)
        A_dim = env.action_input.shape[0] // W; ho = 0 if a.hand == 'left' else A_dim // 2   # flat [W * A] buffer, hands (left, right)
        rng = np.random.default_rng(0); n_steps = f1 - f0
        noise_p = gaussian_filter1d(rng.normal(size=(W, n_steps, 3)), 3, axis=1); noise_p *= a.noise_cm / 100 / max(noise_p.std(), 1e-9)
        noise_r = gaussian_filter1d(rng.normal(size=(W, n_steps, 3)), 3, axis=1); noise_r *= np.radians(a.noise_deg) / max(noise_r.std(), 1e-9)
        G = np.array([g for g in grid for _ in range(a.trials)]); trial = np.tile(np.arange(a.trials), len(grid))
        noise_p[trial == 0] = 0; noise_r[trial == 0] = 0           # trial 0 of every variant is undisturbed
        # every world starts at frame 0 like the evaluator (a mid-episode reset places the hand instantly and changed the
        # outcome: the unchanged wrap slipped 37 cm from a frame-25 reset but held from frame 0); zero action until F0
        env.reset(frame_id=0); zero = wp.zeros(W * A_dim, dtype=wp.float32, device='cuda')
        for f in range(0, f0):
            env.step(zero)
        act = np.zeros((W, A_dim), np.float32); err = np.zeros((W, n_steps)); inhand = np.zeros((W, n_steps, 3))
        wb0 = next(i for i, l in enumerate(labels) if l.endswith(f'{a.hand}_hand_C_MC')); hand_ids = wb0 + bpw * np.arange(W)
        for k, f in enumerate(range(f0, f1)):
            ax_w = OR[f].apply(axis); c_w = OR[f].apply(cg) + OP[f]
            Rroll = Rot.from_rotvec(np.radians(G[:, 2])[:, None] * ax_w[None])
            Pd = c_w + Rroll.apply(WP[f] - c_w) + ax_w[None] * G[:, 0:1] / 100 + np.c_[np.zeros((W, 2)), G[:, 1] / 100]
            cross = np.cross([0, 0, 1.0], ax_w); cross /= max(np.linalg.norm(cross), 1e-9)   # horizontal, across the object
            w_app = np.clip((a.start - f) / max(1, a.approach_in), 0.0, 1.0)              # 1 before, 0 from the hold start
            Pd = Pd + w_app * (cross[None] * G[:, 4:5] / 100 + np.c_[np.zeros((W, 2)), -G[:, 5] / 100])
            rp = Pd - WP[f] + noise_p[:, k]
            # FlashCHORD composes the wrist residual as ref * quat_rpy(r, p, y) (= extrinsic xyz Euler)
            rr = (Rot.from_quat(np.repeat(WR[f].as_quat()[None], W, 0)).inv() * Rot.from_rotvec(noise_r[:, k]) * Rroll * WR[f]).as_euler('xyz')
            rf = (G[:, 3:4] * flex[None]) * (1.0 if f >= a.start else 0.0)
            act[:, ho:ho + 3] = np.clip(rp, -CLIP['pos'], CLIP['pos']) / SCALE['pos']
            act[:, ho + 3:ho + 6] = np.clip(rr, -CLIP['rot'], CLIP['rot']) / SCALE['rot']
            act[:, ho + 6:ho + 28] = np.clip(rf, -CLIP['finger'], CLIP['finger']) / SCALE['finger']
            env.step(wp.array(act.reshape(-1), dtype=wp.float32, device='cuda'))
            BQ = env.state_0.body_q.numpy(); q = BQ[obj_ids]; hq = BQ[hand_ids]
            err[:, k] = np.linalg.norm(q[:, :3] - OP[min(f + 1, T - 1)], axis=1)
            inhand[:, k] = Rot.from_quat(hq[:, 3:7]).inv().apply(q[:, :3] - hq[:, :3])
            if k == a.approach and os.environ.get('GS_DEBUG'):          # wrist placement check: does the variant move the hand?
                wb0 = next(i for i, l in enumerate(labels) if l.endswith(f'{a.hand}_hand_C_MC')); wq = env.state_0.body_q.numpy()[wb0 + bpw * np.arange(W)]
                for i in range(0, W, max(1, W // 12)):
                    print('debug f', f, 'variant', G[i].tolist(), 'wrist sim', np.round(wq[i, :3], 3).tolist(), 'target', np.round(Pd[i], 3).tolist(), flush=True)
    moving = np.nonzero(np.linalg.norm(OP[f0:f1] - OP[f0], axis=1) > 0.01)[0]; ks = int(moving[0]) if len(moving) else 0
    kc = min(n_steps - 1, a.start - f0 + a.close)                       # fingers closed
    slip = np.linalg.norm(inhand[:, kc:] - inhand[:, kc:kc + 1], axis=2).max(1)
    path_ok = err[:, ks:].max(1) < a.hold_cm / 100
    held = slip < a.slip_cm / 100; mean_err = 100 * err[:, ks:].mean(1)
    rows = []
    for i, g in enumerate(grid):
        sel = slice(i * a.trials, (i + 1) * a.trials)
        rows.append(dict(along_cm=g[0], down_cm=g[1], roll_deg=g[2], squeeze_rad=g[3], side_cm=g[4], below_cm=g[5], hold_rate=float(held[sel].mean()),
                         slip_cm=round(float(100 * slip[sel].max()), 1), path_rate=float(path_ok[sel].mean()),
                         mean_err_cm=round(float(mean_err[sel].mean()), 2), max_err_cm=round(float(100 * err[sel, ks:].max()), 1),
                         human_dev=round(float(np.hypot(g[0], g[1]) + abs(g[2]) / 15), 2)))
    best_rate = max(r['hold_rate'] for r in rows)
    pool = [r for r in rows if r['hold_rate'] >= a.min_rate] or [r for r in rows if r['hold_rate'] >= best_rate - 1e-9]
    choice = min(pool, key=lambda r: (r['human_dev'], r['mean_err_cm']))
    out = dict(ref=a.ref, hand=a.hand, object=a.object, start=a.start, frames=[f0, f1], worlds=W, object_moves_from=f0 + ks,
               axis_obj=axis.tolist(), grasp_point_obj=cg.tolist(), best_rate=best_rate, choice=choice,
               baseline=next((r for r in rows if not any(r[k] for k in ('along_cm', 'down_cm', 'roll_deg', 'squeeze_rad', 'side_cm', 'below_cm'))), None),
               rows=sorted(rows, key=lambda r: (-r['hold_rate'], r['human_dev'], r['mean_err_cm'])), args=vars(a))
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'[{time.time() - t0:.0f}s] {W} worlds, {len(grid)} variants x {a.trials} trials; best hold rate {best_rate:.2f}; '
          f'choice {json.dumps(choice)}; baseline {json.dumps(out["baseline"])}', flush=True)
    for r in out['rows'][:10]:
        print(json.dumps(r), flush=True)


if __name__ == '__main__':
    main()
