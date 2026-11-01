"""CPU check: does a training override sim.njmax=1024 sim.nconmax=512 reach the evaluator's solver?
(stored in the resolved config -> harness.apply_evaluation_composition -> RLEnvConfig -> SolverMuJoCo)."""
import os, sys, dataclasses
sys.path.insert(0, '/home/user/v2d-track3/tools/physics_solve')
import warp as wp
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
for arm, extra in (('stock', []), ('njmax1024', ['sim.njmax=1024', 'sim.nconmax=512'])):
    ov = ['experiment=sharpa_flash_sac', f"task.parquet='{ref}'", 'embodiment=sharpa_hands_mid'] + extra
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=ov)
    saved = OmegaConf.to_container(cfg, resolve=True)
    ev = apply_evaluation_composition(saved, world_count=1, reset_mode='explicit')
    ecfg = instantiate_typed(OmegaConf.create(ev).env, RLEnvConfig)
    emb = instantiate_typed(cfg.embodiment, Embodiment)
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=ref, control_fps=ecfg.sim.fps, motion_speed=1.0, embodiment=emb,
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True, decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=dataclasses.replace(ecfg, auto_reset=False))
    md = env.solver.mjw_data
    print(arm, 'stored env.sim', saved['env']['sim']['njmax'], saved['env']['sim']['nconmax'], '| eval RLEnvConfig.sim', ecfg.sim.njmax, ecfg.sim.nconmax,
          '| solver data njmax', getattr(md, 'njmax', None), 'naconmax', getattr(md, 'naconmax', None), flush=True)
