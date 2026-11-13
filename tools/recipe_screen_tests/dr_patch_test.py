"""CPU test of ops/box/patch_flashchord_dr.py (recipe screen arm D; physics-solver.md section 8). One configuration per
process (the patches read their variables at import). Run from a FlashCHORD dir with its venv, EMB=sharpa_hands_mid:
  USE_COPY=<patched flash_chord dir or empty for the installed package> [FC_DR_RESET=...] [FC_STATE_RESET=bank.npz] \
    python dr_patch_test.py REF.parquet OUT.npz
Records, for W worlds of an RLEnv built like tools/trace_rollout.py zero (VOC 0 target, no termination, no auto-reset):
  r1   joint_q right after a sampled (training-style) reset, then h20 / h40 after 20 / 40 (+EXTRA) zero-action steps
       (the 20-step settling hold runs at VOC 1), r2 after a second sampled reset, ex after an explicit reset to frame
       0 and ex5 five steps later; the reset frames, finger openings and reset-table layout.
  MODE=evalseq: the official evaluator's sequence instead (harness.evaluate_checkpoint: env.reset() sampled, then
       env.reset(frame_id=0) explicit, then the rollout): ev after the explicit reset, ev5 five steps later.
Compared by dr_compare.py.
No ground truth is read (our reference parquet only)."""
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

W = int(os.environ.get('W', '8'))
env, labels = S.build_env(sys.argv[1], W, planner=False)
out = dict(pkg=os.path.dirname(flash_chord.__file__), dr_installed=int('flash_chord.lifecycle.v2d_dr' in sys.modules))
jq = lambda: env.state_0.joint_q.numpy().reshape(W, -1).copy()  # noqa: E731
with S.on(env):
    t = env.reset_table
    out.update(per_world_q=t.per_world_q, num_frames=t.num_frames, obj_q=t.object_root_q_ids.numpy(),
               finger_q=t.finger_q_ids.numpy(), finger_lo=t.finger_lower.numpy(), finger_hi=t.finger_upper.numpy(),
               ref_q=t.ref_joint_q.numpy(), obj_off=t.object_root_position_offsets_w.numpy())
    if os.environ.get('MODE') == 'evalseq':
        env.reset(); env.reset(frame_id=0); out['ev'] = jq()
        for k in range(5):
            env.step(None)
        out['ev5'] = jq(); out['finite'] = int(np.isfinite(env.state_0.body_q.numpy()).all())
        np.savez(sys.argv[2], **{k: np.asarray(v) for k, v in out.items()}); print('saved', sys.argv[2], 'evalseq'); sys.exit(0)
    env.reset()                                                    # sampled reset (the training path)
    out.update(r1=jq(), frame1=env.reset_policy.reset_frame.numpy().copy(), finger1=env.reset_policy.finger_scale.numpy().copy(),
               ts1=env.timestep.numpy().copy())
    if 'flash_chord.lifecycle.v2d_states' in sys.modules and os.environ.get('FC_STATE_RESET'):
        from flash_chord.lifecycle import v2d_states as B
        out['bank_flag1'] = B.arrays(W, env.device)[0].numpy().copy()
    for k in range(40):
        env.step(None)
        if k == 19:
            out['h20'] = jq(); out['ts20'] = env.timestep.numpy().copy()
    out['h40'] = jq(); out['ts40'] = env.timestep.numpy().copy()
    for k in range(int(os.environ.get('EXTRA', '0'))):            # history control: extra steps before the next resets
        env.step(None)
    env.reset()                                                    # a second sampled reset: new frames, new noise
    out.update(r2=jq(), frame2=env.reset_policy.reset_frame.numpy().copy(), finger2=env.reset_policy.finger_scale.numpy().copy())
    env.reset(frame_id=0)                                          # explicit reset: the evaluator's path
    out['ex'] = jq()
    for k in range(5):
        env.step(None)
    out['ex5'] = jq()
    out['finite'] = int(np.isfinite(env.state_0.body_q.numpy()).all())
    if 'flash_chord.lifecycle.v2d_dr' in sys.modules:
        from flash_chord.lifecycle import v2d_dr as V
        flag, count = V.arrays(W, env.device)
        out.update(dr_flag_after_explicit=flag.numpy().copy(), dr_count=count.numpy().copy())
    if 'flash_chord.lifecycle.v2d_states' in sys.modules and os.environ.get('FC_STATE_RESET'):
        out['bank_flag_after_explicit'] = B.arrays(W, env.device)[0].numpy().copy()
np.savez(sys.argv[2], **{k: np.asarray(v) for k, v in out.items()})
print('saved', sys.argv[2], 'pkg', out['pkg'], 'dr module loaded', out['dr_installed'])
