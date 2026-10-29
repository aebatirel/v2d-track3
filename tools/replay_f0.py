"""DIAGNOSTIC (2026-10-23): reset the FlashCHORD training env (1 world) at reference frame 0 and step with ZERO residual
action for N frames, termination and auto-reset off (as the evaluator: frame 0 to the end); prints wrist and object
errors vs the reference. Env: FC (flash_chord dir), VOC (virtual object controller scale, default 1.0), DEV (cpu|cuda).
Found the VOC explosion of the spoon (ops/box/fc_v2d_voc.py). Usage: replay_f0.py PARQUET N"""
import os, sys, dataclasses, numpy as np, warp as wp
from hydra import compose, initialize_config_dir
from scipy.spatial.transform import Rotation as Rot
FC = os.environ['FC']
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import pyarrow.parquet as pq
off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{sys.argv[1]}'"] + off)
env_config = instantiate_typed(cfg.env, RLEnvConfig); env_config = dataclasses.replace(env_config, auto_reset=False, voc_scale=float(os.environ.get("VOC", "1.0")))
emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py()
refw = {s: np.array(t.column(f'robot_{s}_wrist_position')[0].as_py(), float).reshape(-1, 3) for s in ('left', 'right')}; T = len(refw['left'])
refo = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
with wp.ScopedDevice(os.environ.get('DEV', 'cpu')):
    st = setup_scene(parquet=sys.argv[1], control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config); m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    wb = {s: next(i for i, l in enumerate(labels) if f'{s}_hand_C_MC' in l) for s in ('left', 'right')}
    ob = [next(i for i, l in enumerate(labels) if l.startswith(f'track3_{n}/')) for n in names]
    env.reset(frame_id=0)
    for k in range(int(sys.argv[2]) + 1):
        if k <= 8 or k % 10 == 0:
            q = env.state_0.body_q.numpy(); f = min(k, T - 1)
            w = ' '.join(f'{s[0].upper()} {100 * np.linalg.norm(q[wb[s], :3] - refw[s][f]):5.1f}' for s in ('left', 'right'))
            o = ' '.join(f'{n[:6]} {100 * np.linalg.norm(q[i, :3] - refo[f, j]):5.1f}' for j, (n, i) in enumerate(zip(names, ob)))
            print(f'frame {k:3d} wrist err cm {w} | object err cm {o} | R wrist sim {np.round(q[wb["right"], :3], 3)} ref {np.round(refw["right"][f], 3)}', flush=True)
        env.step(None)
