"""DIAGNOSTIC (2026-10-23): record every body pose of a rollout played like the official evaluator (frame 0 to the end,
VOC 0, no early termination, no auto-reset), to see where the hands are relative to the objects. Run with FlashCHORD's
venv from the flash_chord directory.
  trace_rollout.py policy OUT.npz <view_policy overrides...>  the trained policy (pass tools/render_eval.sh's overrides)
  trace_rollout.py zero OUT.npz PARQUET N                     zero residual action: the reference played in physics
OUT.npz: q (frames, bodies, 7) body poses [x y z qx qy qz qw], frame (reference frame per row), labels (body names).
CONTACTS=1 also records per frame and body pair the summed contact normal force, tangential force and contact count
(cf: frames x bodies x bodies x 3; body -1 = world/support stored in the last slot) from FlashCHORD's own contact
readout (solver.update_contacts with forces), for grip-force analysis (docs/research/notes/24).
CONTACTS=2 (2026-10-30) also keeps every individual contact: cl (n, 10) rows [record index, body0, body1, position xyz,
normal xyz (shape0 -> shape1), force on shape0 along the normal], world frame (tools/sim_contacts.py).
STATE=1 (2026-10-31, solver<->RL loop) also keeps the full simulator state of world 0 per frame (jq joint_q, jqd joint_qd,
qd body_qd, qw MuJoCo qacc_warmstart, es episode_step), the input of tools/physics_solve/solve.py --start_state (a solve
from the policy's state at a failure) and of the reset-state bank (tools/physics_solve/merge_ref.py).
No ground truth is read. Analysis: tools/hand_object_gap.py, tools/physics_solve/failures.py.
"""
import atexit, dataclasses, os, sys

import numpy as np

mode, out = sys.argv[1], sys.argv[2]
REC = {'q': [], 'frame': [], 'labels': [], 'cf': []}
CONTACTS = os.environ.get('CONTACTS', '0') not in ('', '0')
CONTACT_LIST = os.environ.get('CONTACTS', '0') == '2'
REC['cl'] = []
STATE = os.environ.get('STATE', '0') not in ('', '0')
for k in ('jq', 'jqd', 'qd', 'qw', 'es'):
    REC[k] = []


def contact_table(env):
    """(bodies+1, bodies+1, 3): summed |normal force|, |tangential force|, count per body pair (last index = world)."""
    from flash_chord.runtime.contact import read_contacts_w
    model = env.model if hasattr(env, 'model') else env.scene.model
    rd = read_contacts_w(model, env.state_0, env.contacts); nb = env.state_0.body_q.shape[0]; t = np.zeros((nb + 1, nb + 1, 3), np.float32)
    for b0, b1, f, n in zip(rd.body0_ids, rd.body1_ids, rd.contact_force_w, rd.contact_normal_w):
        fn = float(np.dot(f, n)); ft = float(np.linalg.norm(f - fn * n)); i, k = sorted((int(b0) if b0 >= 0 else nb, int(b1) if b1 >= 0 else nb))
        t[i, k] += (abs(fn), ft, 1.0)
    return t


def record(env):
    REC['q'].append(env.state_0.body_q.numpy().copy()); REC['frame'].append(int(env.timestep.numpy()[0]))
    if STATE:                                    # world 0's full state (the evaluator replays one world)
        W = env.world_count
        REC['jq'].append(env.state_0.joint_q.numpy().reshape(W, -1)[0].copy())
        REC['jqd'].append(env.state_0.joint_qd.numpy().reshape(W, -1)[0].copy())
        REC['qd'].append(env.state_0.body_qd.numpy().reshape(W, -1)[0].copy())
        REC['qw'].append(env.solver.mjw_data.qacc_warmstart.numpy()[0].copy())
        REC['es'].append(int(env.episode_step.numpy()[0]))
    if CONTACTS:
        REC['cf'].append(contact_table(env))
    if CONTACT_LIST:
        from flash_chord.runtime.contact import read_contacts_w
        model = env.model if hasattr(env, 'model') else env.scene.model
        rd = read_contacts_w(model, env.state_0, env.contacts); i = len(REC['q']) - 1
        for b0, b1, p, n, f in zip(rd.body0_ids, rd.body1_ids, rd.contact_pos_w, rd.contact_normal_w, rd.contact_force_w):
            REC['cl'].append([i, int(b0), int(b1), *p, *n, float(np.dot(f, n))])


def save():
    extra = dict(cf=np.array(REC['cf'], np.float32)) if REC['cf'] else {}
    if CONTACT_LIST:
        extra['cl'] = np.array(REC['cl'], np.float64).reshape(-1, 10)
    if STATE:
        extra.update(jq=np.array(REC['jq'], np.float32), jqd=np.array(REC['jqd'], np.float32),
                     qd=np.array(REC['qd'], np.float32), qw=np.array(REC['qw'], np.float32), es=np.array(REC['es']))
    np.savez_compressed(out, q=np.array(REC['q'], np.float32), frame=np.array(REC['frame']), labels=np.array(REC['labels']), **extra)
    print(f'trace: {len(REC["q"])} frames -> {out}', flush=True)


def labels_of(model):
    return list(getattr(model, 'body_label', None) or getattr(model, 'body_key', []))


if mode == 'policy':
    sys.argv = [sys.argv[0]] + sys.argv[3:]
    sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
    import view_policy as vp
    from flash_chord.envs.rl import RLEnv as _RLEnv
    _cap0 = _RLEnv.capture_step

    def _capture_step(self):                     # Warp graph capture crashes on the CPU (2026-10-31): step eagerly
        if not self.device.is_cpu:               # there (the same transition); CUDA unchanged
            _cap0(self)
    _RLEnv.capture_step = _capture_step
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
