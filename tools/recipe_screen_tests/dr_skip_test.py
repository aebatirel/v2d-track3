"""CPU test of FC_DR_SKIP_IMMEDIATE (ops/box/patch_flashchord_dr.py, 2026-10-31): with FC_IMMEDIATE_FIRST_FRAME's
deployment-exact starts active, DR must leave exactly those starts unperturbed when the flag is set. One configuration
per process (the patches read their variables at import). Run from a FlashCHORD dir with its venv, EMB=sharpa_hands_mid:
  USE_COPY=<patched flash_chord copy> FC_IMMEDIATE_FIRST_FRAME=p [FC_DR_RESET=...] [FC_DR_SKIP_IMMEDIATE=1] [MODE=evalseq] \
    python dr_skip_test.py REF.parquet OUT.npz
Records, for W worlds (RLEnv as tools/trace_rollout.py zero builds it: VOC 0, so the curriculum assist is below the
immediate-start threshold): joint_q, reset frame, finger factor and steps_since_reset right after each of two sampled
resets (40 zero-action steps between them), the DR skip counter, and (MODE=evalseq) the evaluator's sequence. Compared
by dr_skip_compare.py. No ground truth is read (our reference parquet only)."""
import os, sys

COPY = os.environ.get('USE_COPY', '')
if COPY:
    sys.path.insert(0, os.path.join(COPY, 'src'))
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'physics_solve'))
import numpy as np
import solve as S  # noqa: E402
import warp as wp  # noqa: E402

wp.config.log_level = wp.LOG_WARNING
import flash_chord  # noqa: E402
from flash_chord.lifecycle import reset as _reset  # noqa: E402,F401  (runs the patch hooks)

W = int(os.environ.get('W', '16'))
env, labels = S.build_env(sys.argv[1], W, planner=False)
out = dict(pkg=os.path.dirname(flash_chord.__file__), dr_installed=int('flash_chord.lifecycle.v2d_dr' in sys.modules),
           immediate_patched=int('_V2D_IMMEDIATE' in open(_reset.__file__).read()))
jq = lambda: env.state_0.joint_q.numpy().reshape(W, -1).copy()  # noqa: E731
pol = lambda: env.reset_policy  # noqa: E731
with S.on(env):
    t = env.reset_table
    out.update(obj_q=t.object_root_q_ids.numpy(), finger_q=t.finger_q_ids.numpy(), voc_decay=int(pol().config.voc_decay_steps))
    if os.environ.get('MODE') == 'evalseq':
        env.reset(); env.reset(frame_id=0); out['ev'] = jq()
        for k in range(5):
            env.step(None)
        out['ev5'] = jq()
        np.savez(sys.argv[2], **{k: np.asarray(v) for k, v in out.items()}); print('saved', sys.argv[2], 'evalseq'); sys.exit(0)
    for i in (1, 2):
        env.reset()                                                # a sampled (training-style) reset
        out[f'r{i}'] = jq(); out[f'frame{i}'] = pol().reset_frame.numpy().copy(); out[f'finger{i}'] = pol().finger_scale.numpy().copy()
        out[f'ssr{i}'] = pol().steps_since_reset.numpy().copy()
        if i == 1:
            for k in range(40):
                env.step(None)
    if out['dr_installed']:
        from flash_chord.lifecycle import v2d_dr as V
        out['flag'] = V.arrays(W, env.device)[0].numpy().copy(); out['count'] = V.arrays(W, env.device)[1].numpy().copy()
        out['skips'] = V.skips(W, env.device).numpy().copy()
np.savez(sys.argv[2], **{k: np.asarray(v) for k, v in out.items()}); print('saved', sys.argv[2])
