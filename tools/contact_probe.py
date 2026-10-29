"""After reset to frame 0 and one step (training env, 1 world, CPU, stiff wrists): every MuJoCo contact with
penetration, as body pairs. Usage: contact_probe.py PARQUET"""
import os, sys, numpy as np, warp as wp
from hydra import compose, initialize_config_dir
FC = os.environ['FC']
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.embodiments.sharpa_hands import SharpaHands, SharpaHandsConfig
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{sys.argv[1]}'"] + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = instantiate_typed(cfg.env, RLEnvConfig); col = instantiate_typed(cfg.collision, CollisionPolicy)
emb = SharpaHands(SharpaHandsConfig.stiff_tracking()) if not os.environ.get('EMB') else instantiate_typed(cfg.embodiment, Embodiment)
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=sys.argv[1], control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config); m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    env.reset(frame_id=0); env.step(None)
    s = env.solver; d = s.mjw_data; c = d.contact
    n = int(d.nacon.numpy()[0]) if hasattr(d, 'nacon') else int(d.ncon.numpy()[0])
    geom = c.geom.numpy()[:n]; dist = c.dist.numpy()[:n]; wid = c.worldid.numpy()[:n] if hasattr(c, 'worldid') else np.zeros(n, int)
    wid = wid if len(wid) == n else np.zeros(n, int); print('geom', geom.shape, 'dist', dist.shape, 'g2s', s.mjc_geom_to_newton_shape.numpy().shape)
    g2s = s.mjc_geom_to_newton_shape.numpy()
    sb = m.shape_body.numpy()
    def name(g, w):
        sh = g2s[w, g] if g2s.ndim == 2 else g2s[g]
        if sh < 0: return f'geom{g}'
        b = sb[sh]; return 'support/table' if b < 0 else labels[b].split('/')[-1]
    pairs = {}
    for (g0, g1), dd, w in zip(geom, dist, wid):
        k = tuple(sorted((name(g0, w), name(g1, w)))); pairs.setdefault(k, []).append(dd)
    print(f'{n} contacts after reset + 1 step')
    for k, v in sorted(pairs.items(), key=lambda kv: min(kv[1])):
        print(f'  {k[0]:>28s} <-> {k[1]:<28s} n {len(v):3d} min dist {1000 * min(v):+7.2f} mm')
