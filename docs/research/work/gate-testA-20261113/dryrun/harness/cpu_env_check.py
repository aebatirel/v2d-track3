"""DRY RUN ONLY (CPU): build FlashCHORD's training environment for one test-A reference on the PATCHED tree, with the
exact training overrides (std_learner recipe), then reset at frame 0 and take N zero-residual steps. This exercises the
reference loader, the scene with the assets the reference names, the support stage, CoACD decomposition, the reward
objective with the FDR patch hooks (FC_FDR_OBJ / FC_FDR_TIPS set in the environment) and the VOC patch, without JAX.
Run from the flash_chord directory with its venv:  python cpu_env_check.py PARQUET N OUT.json"""
import dataclasses, json, os, sys, time
import numpy as np
import warp as wp
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
parquet, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
FDR = 'curriculum=tracking_250m_mixed_reset_v2d objective.force_closure.enabled=true objective.force_closure.weight=6 ' \
      'objective.contact_wrench_support.weight=3 objective.unintended_contact.weight=-2'.split()
ov = ['experiment=sharpa_flash_sac', f"task.parquet='{os.path.dirname(parquet)}'", 'task.motion_speed=1.0', 'reset.seed=42',
      'logging.mode=disabled', 'training.total_environment_steps=250003456'] + FDR
t0 = time.time(); rec = dict(parquet=parquet, overrides=ov, env={k: v for k, v in os.environ.items() if k.startswith('FC_')})
with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=ov)
env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False)
emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    rec['setup_s'] = round(time.time() - t0, 1); rec['frames'] = int(st.reference.num_frames)
    env = RLEnv(st.scene, st.reference, config=env_config)
    rec['objective'] = type(env.objective).__name__
    env.reset(frame_id=0); rew = []
    for _ in range(n):
        r = env.step(None)
        x = getattr(r, 'reward', None)
        if x is None and isinstance(r, tuple) and len(r) > 1:
            x = r[1]
        try:
            rew.append(float(np.asarray(x.numpy() if hasattr(x, 'numpy') else x).ravel()[0]))
        except Exception as e:
            rew.append(f'unreadable: {type(e).__name__}')
rec['rewards'] = rew; rec['finite'] = all(isinstance(v, float) and np.isfinite(v) for v in rew)
rec['total_s'] = round(time.time() - t0, 1)
import flash_chord.objectives.tracking as T
rec['fdr_hook_in_tracking_py'] = 'v2d' in open(T.__file__).read()
json.dump(rec, open(out, 'w'), indent=1); print(json.dumps(rec)[:600])
