"""Per-start-frame cleanliness map (CPU, 1 world, real soft wrists, zero policy action, explicit reset = no settling,
as in the official evaluation). For start frames f = 0, STEP, 2*STEP, ...: reset to f, step K times, report the worst
object deviation from the reference (cm / deg), whether the episode terminated, and each object's height change
after the first step (dz cm: about -1.2 = free fall during a carry, + = pushed up). Usage: PARQUET STEP K"""
import os, sys, numpy as np, warp as wp, pyarrow.parquet as pq
from hydra import compose, initialize_config_dir
from scipy.spatial.transform import Rotation as Rot
FC = os.environ['FC']
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{sys.argv[1]}'"]
                  + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = instantiate_typed(cfg.env, RLEnvConfig); emb = instantiate_typed(cfg.embodiment, Embodiment)
col = instantiate_typed(cfg.collision, CollisionPolicy)
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py()
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
RP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
RQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
step, K = int(sys.argv[2]), int(sys.argv[3])
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=sys.argv[1], control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config); m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    objs = [next(i for i, l in enumerate(labels) if n in l) for n in names]
    print('frame  ' + '  '.join(f'{n[:14]:>22s}' for n in names) + '   survived')
    for f in range(0, T - K, step):
        env.reset(frame_id=f); worst = np.zeros((len(names), 2)); surv = K; dz = np.zeros(len(names))
        for k in range(1, K + 1):
            env.step(None)
            ts = int(env.timestep.numpy()[0])
            if ts != f + k:
                surv = k - 1; break
            q = env.state_0.body_q.numpy()
            for j, ob in enumerate(objs):
                dp = 100 * np.linalg.norm(q[ob, :3] - RP[ts, j]); da = np.degrees((Rot.from_quat(q[ob, 3:7]) * Rot.from_quat(RQ[ts, j]).inv()).magnitude())
                worst[j] = np.maximum(worst[j], [dp, da]); dz[j] = 100 * (q[ob, 2] - RP[ts, j, 2]) if k == 1 else dz[j]
        print(f'{f:5d}  ' + '  '.join(f'{w[0]:8.1f} cm {w[1]:6.1f} deg' for w in worst) + f'   {surv:2d}/{K}  dz ' + ' '.join(f'{v:+.2f}' for v in dz), flush=True)
