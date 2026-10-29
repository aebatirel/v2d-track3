"""Timed zero-action replay (same composition as tools/trace_rollout.py zero mode: evaluator-like, VOC 0, no early
termination, no auto-reset, 1 world, frame 0 start). Prints import / scene-setup / env-build / per-step timings and
saves the trace (q, frame, labels) for tools/trace_score.py. Run from the flash_chord dir with the FlashCHORD venv.
Usage: timed_zero.py PARQUET N OUT.npz     (EMB = embodiment config name, DEV = cpu | cuda)"""
import dataclasses, os, sys, time

t_start = time.time()
import numpy as np
import warp as wp
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
t_import = time.time()

parquet, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + off
                  + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
Q, F = [], []
with wp.ScopedDevice(os.environ.get('DEV', 'cpu')):
    t0 = time.time()
    st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    t1 = time.time()
    env = RLEnv(st.scene, st.reference, config=env_config)
    labels = list(getattr(st.scene.model, 'body_label', None) or getattr(st.scene.model, 'body_key', []))
    t2 = time.time()
    env.reset(frame_id=0); Q.append(env.state_0.body_q.numpy().copy()); F.append(int(env.timestep.numpy()[0]))
    step_t = []
    for _ in range(n - 1):
        s = time.time(); env.step(None); Q.append(env.state_0.body_q.numpy().copy()); F.append(int(env.timestep.numpy()[0]))
        step_t.append(time.time() - s)
    t3 = time.time()
np.savez_compressed(out, q=np.array(Q, np.float32), frame=np.array(F), labels=np.array(labels))
st_ = np.array(step_t)
print(f'TIMING imports {t_import - t_start:.1f} s | setup_scene {t1 - t0:.1f} s | RLEnv build {t2 - t1:.1f} s | '
      f'{len(st_)} steps {t3 - t2:.1f} s = {st_.mean():.4f} s/frame (median {np.median(st_):.4f}, first {st_[0]:.2f} s, '
      f'p95 {np.percentile(st_, 95):.4f}) | total {t3 - t_start:.1f} s | bodies {len(labels)} | sim fps {env_config.sim.fps} '
      f'substeps {env_config.sim.substeps}', flush=True)
