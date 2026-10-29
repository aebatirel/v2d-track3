"""Reset the FlashCHORD training env (1 world, CPU) to reference frame 0 and step with a zero residual action:
where do the robot wrists go vs the reference? Usage: replay_probe.py PARQUET STEPS"""
import os, sys, numpy as np, warp as wp
from hydra import compose, initialize_config_dir
FC = os.environ['FC']
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import pyarrow.parquet as pq
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{sys.argv[1]}'"] + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = instantiate_typed(cfg.env, RLEnvConfig); emb = instantiate_typed(cfg.embodiment, Embodiment)
if os.environ.get('STIFF') == '1':
    from flash_chord.embodiments.sharpa_hands import SharpaHands, SharpaHandsConfig
    emb = SharpaHands(SharpaHandsConfig.stiff_tracking())
col = instantiate_typed(cfg.collision, CollisionPolicy)
t = pq.read_table(sys.argv[1]); refw = {s: np.array(t.column(f'robot_{s}_wrist_position')[0].as_py(), float).reshape(-1, 3) for s in ('left', 'right')}
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=sys.argv[1], control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                     world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config)
    m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    pick = {s: [i for i, l in enumerate(labels) if s in l.lower() and ('c_mc' in l.lower() or 'palm' in l.lower() or 'hand_base' in l.lower())] for s in ('left', 'right')}
    print('bodies', len(labels), 'wrist bodies', {s: [labels[i] for i in v[:3]] for s, v in pick.items()}, flush=True)
    names = [n for n in t.column('object_body_names')[0].as_py()]
    objs = [next(i for i, l in enumerate(labels) if l.split('/')[0].endswith(n) or n in l) for n in names]
    refo = np.concatenate([np.array(t.column('object_body_position')[0].as_py(), float).reshape(len(refw['left']), len(names), 3),
                           np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(len(refw['left']), len(names), 4)], 2)
    print('objects', names, [labels[i] for i in objs], flush=True); q0 = {}
    env.reset(frame_id=0)
    def report(k):
        q = env.state_0.body_q.numpy()
        ts = int(env.timestep.numpy()[0]) if hasattr(env, 'timestep') else k
        out = []
        for s in ('left', 'right'):
            i = pick[s][0]; p = q[i, :3]; f = min(ts, len(refw[s]) - 1)
            out.append(f'{s} {np.round(p, 3)} ref {np.round(refw[s][f], 3)} err {100 * np.linalg.norm(p - refw[s][f]):.1f} cm')
        from scipy.spatial.transform import Rotation as Rot
        for j, ob in enumerate(objs):
            p = q[ob, :3]; rq = q[ob, 3:7]
            f = min(ts, len(refo) - 1); rp = refo[f, j, :3]; rr = refo[f, j, 3:7]
            if k == 0: q0[j] = (p.copy(), rq.copy())
            out.append(f'{labels[ob].split("/")[-1][:14]} sim-ref {100 * np.linalg.norm(p - rp):.1f} cm '
                       f'{np.degrees((Rot.from_quat(rq) * Rot.from_quat(rr[[1, 2, 3, 0]]).inv()).magnitude()):.0f} deg, '
                       f'z {p[2]:.3f}, tilt since reset {np.degrees((Rot.from_quat(rq) * Rot.from_quat(q0[j][1]).inv()).magnitude()):.0f} deg')
        print(f'step {k} (frame {ts}): ' + ' | '.join(out), flush=True)
    report(0)
    for k in range(1, int(sys.argv[2]) + 1):
        env.step(None)
        if k in (1, 5, 10, 15, 20, 25, 30, 40, 60, 100, 150, 200, 260, 300, 340): report(k)
