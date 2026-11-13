"""CPU check for arm V (actor sees object body velocity): (1) the override reaches the resolved config the checkpoint
stores; (2) the evaluator's path (harness.apply_evaluation_composition + instantiate cfg.env) keeps it; (3) the actor
observation grows by 6 values per object and those values move when objects move. Our reference parquet only."""
import os, sys, dataclasses
sys.path.insert(0, '/home/user/v2d-track3/tools/physics_solve')
import numpy as np, warp as wp
wp.config.log_level = wp.LOG_WARNING
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
from flash_chord.configuration import instantiate_typed
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.embodiments.base import Embodiment
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
from flash_chord.evaluation.harness import apply_evaluation_composition
ref = sys.argv[1]
res = {}
for arm, extra in (('C', []), ('V', ['observation.object_body_velocity.enabled=true'])):
    ov = ['experiment=sharpa_flash_sac', f"task.parquet='{ref}'", 'embodiment=sharpa_hands_mid'] + extra
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=ov)
    saved = OmegaConf.to_container(cfg, resolve=True)                       # what the checkpoint stores (resolved)
    stored = saved['env']['observation']['object_body_velocity']['enabled']
    ev = apply_evaluation_composition(saved, world_count=2, reset_mode='explicit')   # the evaluator's composition
    ecfg = instantiate_typed(OmegaConf.create(ev).env, RLEnvConfig)
    env_config = dataclasses.replace(ecfg, auto_reset=False)
    emb = instantiate_typed(cfg.embodiment, Embodiment)
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=ref, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb,
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=2,
                         include_support=True, decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config)
        o0 = env.reset(frame_id=0).numpy().copy()
        for k in range(30):
            env.step(None)
        o30 = env.observation.numpy().copy()
    nobj = len(st.reference.object_names) if hasattr(st.reference, 'object_names') else None
    res[arm] = dict(stored=stored, eval_cfg=ecfg.observation.object_body_velocity.enabled, dim=env.observation_dim,
                    o0=o0, o30=o30, nobj=nobj)
    print(arm, 'stored', stored, 'eval cfg', ecfg.observation.object_body_velocity.enabled, 'actor obs dim', env.observation_dim,
          'critic ctx vel', ecfg.critic_context.object_body_velocity, flush=True)
c, v = res['C'], res['V']
print('dim delta', v['dim'] - c['dim'])
# columns of V that are not in C: compare by finding the extra block (V obs = C obs with the velocity block inserted)
d = v['dim'] - c['dim']
for t, name in ((0, 'o0'), (30, 'o30')):
    a, b = c[name].reshape(2, -1), v[name].reshape(2, -1)
    # try every insertion offset; the one that matches C exactly elsewhere is the velocity block
    hits = [s for s in range(c['dim'] + 1) if np.allclose(np.delete(b, range(s, s + d), axis=1), a, atol=1e-5)]
    blk = b[:, hits[0]:hits[0] + d] if hits else None
    print(f'step {t}: velocity block offset {hits[:3]}; block |max| {np.abs(blk).max() if blk is not None else None}')
