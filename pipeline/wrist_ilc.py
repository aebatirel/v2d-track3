"""Wrist lag correction by iterative learning control (2026-10-23, grasp-lock reference, docs/research/notes/23).
The soft floating wrist (PD kp 25 N/m, kd 6) trails fast reference motion: replaying eval ep3 with zero action the hand
was up to 10 cm behind on the reach (f25-35) and arrived late at the grasp. Each iteration replays the reference with
zero residual action under evaluator conditions (VOC 0, no termination, no auto-reset), measures the simulated wrist
(C_MC body) against the INTENDED wrist path (the input reference's kinematic frames, i.e. robot_*_frames C_MC), and
moves the wrist TARGET columns by GAIN x the error LEAD frames ahead (smoothed, capped at CAP), position and rotation.
Frames, finger joints and objects are unchanged, so rewards still aim at the intended hand pose. Our reference only.
Usage (FlashCHORD python, from the flash_chord dir): wrist_ilc.py IN_PARQUET OUT_PARQUET [--iters 4] [--device cuda]
OUT_PARQUET must sit in a reference tree with reconstructed_stage/ like IN_PARQUET (iterations are written there).
"""
import argparse, dataclasses, json, os, shutil, time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.ndimage import uniform_filter1d
from scipy.spatial.transform import Rotation as Rot


def replay(parquet, n, device):
    """Zero-action rollout like the evaluator; returns body poses (n, bodies, 7) and body labels."""
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + off
                      + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))   # EMB: embodiment config name
    env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
    with wp.ScopedDevice(device):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config); env.reset(frame_id=0); Q = [env.state_0.body_q.numpy().copy()]
        for _ in range(n - 1):
            env.step(None); Q.append(env.state_0.body_q.numpy().copy())
        labels = list(getattr(st.scene.model, 'body_label', None) or getattr(st.scene.model, 'body_key', []))
    return np.array(Q), labels


def main():
    p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--iters', type=int, default=4); p.add_argument('--gain', type=float, default=0.8)
    p.add_argument('--lead', type=int, default=2); p.add_argument('--smooth', type=int, default=5)
    p.add_argument('--cap', type=float, default=0.12); p.add_argument('--cap_rot', type=float, default=0.6)
    p.add_argument('--device', default='cuda')
    a = p.parse_args(); t0 = time.time()
    t = pq.read_table(a.inp); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    want, tgt, stats = {}, {}, []
    for s in ('left', 'right'):
        fn = t.column(f'{s}_robot_frame_names')[0].as_py(); F = np.array(t.column(f'robot_{s}_frames')[0].as_py(), float).reshape(T, -1, 7)
        c = F[:, fn.index(f'{s}_hand_C_MC')]; want[s] = (c[:, :3], Rot.from_quat(c[:, [4, 5, 6, 3]]))
        tgt[s] = [np.array(t.column(f'robot_{s}_wrist_position')[0].as_py(), float).reshape(T, 3),
                  Rot.from_quat(np.array(t.column(f'robot_{s}_wrist_wxyz')[0].as_py(), float).reshape(T, 4)[:, [1, 2, 3, 0]])]
    base = {s: [tgt[s][0].copy(), tgt[s][1]] for s in tgt}
    work = os.path.splitext(a.out)[0]; cur = a.inp; last_ok = None
    for it in range(a.iters + 1):
        Q, labels = replay(os.path.abspath(cur), T, a.device); row = dict(iter=it)
        bad = ~np.isfinite(Q).all(axis=(1, 2))
        if bad.any():   # the replay diverged (eval 25, 2026-10-24: iteration 3 NaN): stop, keep the last finite iteration
            row['diverged_from_frame'] = int(np.argmax(bad)); stats.append(row)
            print(f'[{time.time() - t0:.0f}s] iter {it}: replay diverged from frame {row["diverged_from_frame"]}; '
                  f'keeping {os.path.basename(last_ok or a.inp)}', flush=True)
            break
        last_ok = cur
        for s in ('left', 'right'):
            b = next(i for i, l in enumerate(labels) if l.endswith(f'{s}_hand_C_MC'))
            ep = want[s][0] - Q[:, b, :3]; er = (want[s][1] * Rot.from_quat(Q[:, b, 3:7]).inv()).as_rotvec()
            row[s] = dict(pos_err_cm_mean=round(100 * float(np.linalg.norm(ep, axis=1).mean()), 2),
                          pos_err_cm_p95=round(100 * float(np.percentile(np.linalg.norm(ep, axis=1), 95)), 2),
                          rot_err_deg_mean=round(float(np.degrees(np.linalg.norm(er, axis=1)).mean()), 1))
            if it == a.iters:
                continue
            sh = lambda x: np.concatenate([x[a.lead:], np.repeat(x[-1:], a.lead, 0)])  # noqa: E731  error LEAD frames ahead
            dp = uniform_filter1d(sh(ep), a.smooth, axis=0, mode='nearest') * a.gain
            dr = uniform_filter1d(sh(er), a.smooth, axis=0, mode='nearest') * a.gain
            newp = tgt[s][0] + dp; offs = newp - base[s][0]; n_ = np.linalg.norm(offs, axis=1, keepdims=True)
            tgt[s][0] = base[s][0] + offs * np.minimum(1, a.cap / np.maximum(n_, 1e-9))
            newr = Rot.from_rotvec(dr) * tgt[s][1]; ro = (newr * base[s][1].inv()).as_rotvec(); rn = np.linalg.norm(ro, axis=1, keepdims=True)
            tgt[s][1] = Rot.from_rotvec(ro * np.minimum(1, a.cap_rot / np.maximum(rn, 1e-9))) * base[s][1]
        stats.append(row); print(f'[{time.time() - t0:.0f}s] iter {it}: {json.dumps(row)}', flush=True)
        if it == a.iters:
            break
        out = t
        for s in ('left', 'right'):
            for c, v in ((f'robot_{s}_wrist_position', tgt[s][0]), (f'robot_{s}_wrist_wxyz', tgt[s][1].as_quat()[:, [3, 0, 1, 2]])):
                i = out.column_names.index(c); out = out.set_column(i, c, pa.array([v.tolist()], type=out.schema.field(c).type))
        cur = f'{work}_ilc{it + 1}.parquet'; pq.write_table(out, cur)
    shutil.copyfile(last_ok or a.inp, a.out)
    json.dump(dict(iterations=stats, args=vars(a)), open(f'{work}_wrist_ilc.json', 'w'), indent=1)
    print(f'[{time.time() - t0:.0f}s] wrote {a.out}', flush=True)


if __name__ == '__main__':
    main()
