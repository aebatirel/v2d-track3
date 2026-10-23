"""DIAGNOSTIC (2026-10-23): record every body pose of a rollout played like the official evaluator (frame 0 to the end,
VOC 0, no early termination, no auto-reset), to see where the hands are relative to the objects. Run with FlashCHORD's
venv from the flash_chord directory.
  trace_rollout.py policy OUT.npz <view_policy overrides...>  the trained policy (pass tools/render_eval.sh's overrides)
  trace_rollout.py zero OUT.npz PARQUET N                     zero residual action: the reference played in physics
OUT.npz: q (frames, bodies, 7) body poses [x y z qx qy qz qw], frame (reference frame per row), labels (body names).
No ground truth is read. Analysis: tools/hand_object_gap.py.
"""
import atexit, dataclasses, os, sys

import numpy as np

mode, out = sys.argv[1], sys.argv[2]
REC = {'q': [], 'frame': [], 'labels': []}


def record(env):
    REC['q'].append(env.state_0.body_q.numpy().copy()); REC['frame'].append(int(env.timestep.numpy()[0]))


def save():
    np.savez_compressed(out, q=np.array(REC['q'], np.float32), frame=np.array(REC['frame']), labels=np.array(REC['labels']))
    print(f'trace: {len(REC["q"])} frames -> {out}', flush=True)


def labels_of(model):
    return list(getattr(model, 'body_label', None) or getattr(model, 'body_key', []))


if mode == 'policy':
    sys.argv = [sys.argv[0]] + sys.argv[3:]
    sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
    import view_policy as vp
    init0, step0 = vp.FlashSACPolicyViewer.__init__, vp.FlashSACPolicyViewer.step

    def init(self, *a, **k):
        init0(self, *a, **k); REC['labels'] = labels_of(self.model); record(self.env); atexit.register(save)

    def step(self):
        step0(self); record(self.env)
    vp.FlashSACPolicyViewer.__init__, vp.FlashSACPolicyViewer.step = init, step
    vp.main.__wrapped__.__module__ = '__main__'   # hydra then finds its config relative to scripts/view_policy.py
    vp.main()
else:
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    parquet, n = sys.argv[3], int(sys.argv[4])
    off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + off
                      + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))   # EMB: embodiment config name
    env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
    emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
    with wp.ScopedDevice(os.environ.get('DEV', 'cuda')):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                         world_count=1, include_support=True, decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config); REC['labels'] = labels_of(st.scene.model)
        env.reset(frame_id=0); record(env)
        for _ in range(n - 1):
            env.step(None); record(env)
    save()
