"""Per-frame MuJoCo contact breakdown (2026-10-21): reset to every STEP-th reference frame without settling, one step,
then the penetrating contacts (> 2 mm) by category (hand-obj / hand-table / hand-hand; self and object-table skipped)
and by robot link. Run from the FlashCHORD dir with FC set. Usage: PARQUET [STEP]"""
import os, sys, json, numpy as np, warp as wp, collections
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
fc = os.environ['FC']; pq_ = sys.argv[1]; step = int(sys.argv[2]) if len(sys.argv) > 2 else 5
with initialize_config_dir(version_base='1.3', config_dir=f'{fc}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{pq_}'"])
ec = instantiate_typed(cfg.env, RLEnvConfig)
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=pq_, control_fps=ec.sim.fps, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=ec); m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    g2s = env.solver.mjc_geom_to_newton_shape.numpy(); sb = m.shape_body.numpy()
    def who(g):
        sh = g2s[0, g] if g2s.ndim == 2 else g2s[g]
        if sh < 0 or sb[sh] < 0: return 'table', 'table'
        lab = labels[sb[sh]].split('/')[-1]
        if lab.startswith('left_') or lab.startswith('right_'): return lab.split('_')[0], lab
        return 'obj', labels[sb[sh]].split('/')[0]
    T = int(st.reference.num_frames); cat = collections.Counter(); links = collections.Counter(); worst = collections.defaultdict(list)
    for t in range(0, T, step):
        env.reset(frame_id=t); env.step(None); d = env.solver.mjw_data; c = d.contact
        n = int((d.nacon if hasattr(d, 'nacon') else d.ncon).numpy()[0])
        fw = collections.defaultdict(float)
        for (g0, g1), dd in zip(c.geom.numpy()[:n], c.dist.numpy()[:n]):
            if dd >= -0.002: continue
            (a, la), (b, lb) = who(g0), who(g1)
            if a == b: continue
            if 'table' in (a, b) and 'obj' in (a, b): continue
            k = '-'.join(sorted(['hand' if x in ('left', 'right') else x for x in (a, b)]))
            fw[k] = max(fw[k], -dd); cat[k] += 1
            for x, l in ((a, la), (b, lb)):
                if x in ('left', 'right'): links[l] += 1
        for k, v in fw.items(): worst[k].append(v * 1000)
    out = dict(frames=len(range(0, T, step)), frames_with={k: len(v) for k, v in worst.items()},
               p95_mm={k: round(float(np.percentile(v, 95)), 1) for k, v in worst.items()},
               top_links=links.most_common(12))
    print(json.dumps(out))
