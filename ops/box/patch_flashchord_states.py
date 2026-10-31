"""Reset-state bank for FlashCHORD training (2026-10-31; solver<->RL loop, docs/research/physics-2026-10-30/
physics-solver.md section 6.1). Idempotent; INERT unless FC_STATE_RESET names a bank file in the training process (no
config field is added, so checkpoints stay loadable by the unpatched evaluator, and explicit resets - every evaluation,
tools/trace_rollout.py, the official evaluator - never draw from the bank).

Why: FlashCHORD resets every training episode onto its reference (a uniformly drawn frame, fingers partly opened, a
20-step hold with the object assist on). The states where the trained policy actually fails - a slipping cup in a grip
that the reference never shows - are only reached from the beginning of an episode. With a bank, a share of the
resets start from those states instead (cf. DAgger / Guided Policy Search: the learner's own states, labelled by the
planner whose targets are merged into the reference for the following frames; PHC's fail-state recovery).
FC_STATE_RESET = path of an npz from tools/physics_solve/merge_ref.py (jq (K, per-world joint_q), jqd (K, per-world
joint_qd), frame (K,) reference frame of each state); FC_STATE_RESET_P = share of sampled resets drawn from the bank
(default 0.25); FC_STATE_RESET_VOC = only while the curriculum's object assist is <= this (default 1.0 = always).
A bank reset sets the world's joint_q / joint_qd to the stored state (object root offsets of the world added, as for
reference resets), its reference timestep to the stored frame, fingers as stored (no opening), and skips the
settling hold (no assist beyond the curriculum's own scale). Rewards, terminations and observations are unchanged.
1. writes flash_chord/lifecycle/v2d_states.py (the bank on the device, a per-world flag; allocated in the reset
   table's builder, i.e. before any graph capture);
2. patches lifecycle/reset.py: reset_kernel (load a banked state), sample_reference_reset (draw from the bank; no
   extra random draws while no bank is loaded, so the inert patch reproduces upstream resets exactly),
   prepare_explicit_reset (explicit resets clear the flag), reset_worlds / ReferenceReset.sample / prepare_explicit
   (the new arguments), ReferenceResetTable.build (allocation).
Not combinable with patch_flashchord_drop.py in the same tree (both edit the same kernels; the anchors check it).
Usage: python patch_flashchord_states.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
pkg = os.path.join(fc, 'src/flash_chord')
TAG = '# v2d patch: FC_STATE_RESET'

open(os.path.join(pkg, 'lifecycle/v2d_states.py'), 'w').write('''"""v2d patch: FC_STATE_RESET (ops/box/patch_flashchord_states.py): a reset-state bank on the device and a per-world
flag (bank index + 1, 0 = a reference reset), shared by lifecycle/reset.py. Inert while FC_STATE_RESET is unset."""
import os

import numpy as np
import warp as wp

PATH = os.environ.get("FC_STATE_RESET", "")
P = float(os.environ.get("FC_STATE_RESET_P", "0.25"))
VOC = float(os.environ.get("FC_STATE_RESET_VOC", "1.0"))
_CACHE = {}


def arrays(world_count, device=None, per_world_q=None, per_world_dof=None, num_frames=None):
    """(flag int32 [W], bank_jq float32 [K, q], bank_jqd float32 [K, dof], bank_frame int32 [K], count): allocated once
    per (world count, device), on the first call, which passes the per-world sizes (the reset table's builder)."""
    key = (int(world_count), str(wp.get_device(device)))
    if key not in _CACHE:
        if per_world_q is None:
            raise RuntimeError("v2d_states.arrays: first call must come from the reset table builder")
        jq = np.zeros((1, per_world_q), np.float32); jqd = np.zeros((1, per_world_dof), np.float32)
        fr = np.zeros(1, np.int32); count = 0
        if PATH:
            z = np.load(PATH)
            jq, jqd, fr = z["jq"].astype(np.float32), z["jqd"].astype(np.float32), z["frame"].astype(np.int32)
            if jq.ndim != 2 or jq.shape[1] != per_world_q or jqd.shape[1] != per_world_dof or len(fr) != len(jq):
                raise ValueError(f"FC_STATE_RESET bank {PATH}: jq {jq.shape} / jqd {jqd.shape} / frame {fr.shape} do not "
                                 f"match this scene (per-world q {per_world_q}, dof {per_world_dof})")
            if num_frames is not None and (fr.min() < 0 or fr.max() >= num_frames - 1):
                raise ValueError(f"FC_STATE_RESET bank {PATH}: frames {fr.min()}..{fr.max()} outside 0..{num_frames - 2}")
            count = len(jq)
            print(f"v2d FC_STATE_RESET: {count} banked states from {PATH}, share {P}, while assist <= {VOC}", flush=True)
        _CACHE[key] = (wp.zeros(int(world_count), dtype=wp.int32, device=device),
                       wp.array(jq, dtype=wp.float32, device=device), wp.array(jqd, dtype=wp.float32, device=device),
                       wp.array(fr, dtype=wp.int32, device=device), count)
    return _CACHE[key]
''')
print('installed:', os.path.join(pkg, 'lifecycle/v2d_states.py'))


def patch(path, edits):
    s = open(path).read()
    if TAG in s:
        print('already patched:', path); return
    if '# v2d patch: FC_DROP_START' in s:
        sys.exit(f'{path} carries the FC_DROP_START patch; the two patches edit the same kernels: not applied')
    for a, b in edits:
        if s.count(a) != 1:
            sys.exit(f'anchor not found once in {path} ({s.count(a)}x): {a[:80]!r}; FlashCHORD changed, patch not applied')
        s = s.replace(a, b)
    open(path, 'w').write(s); print('patched:', path)


patch(os.path.join(pkg, 'lifecycle/reset.py'), [
    ('from flash_chord.data.reference import Reference\n', f'''from flash_chord.data.reference import Reference
from flash_chord.lifecycle import v2d_states as _v2d_states  {TAG}
'''),
    # reset_kernel: load a banked state
    ('''    object_root_position_offsets_w: wp.array(dtype=wp.vec3),
    num_objects: int,
) -> None:
    """Reset selected worlds to a reference pose, optional open fingers, and zero velocity."""
    w = wp.tid()
    if reset_mask[w] == 0:
        return
    f = reset_frame[w]
    base = w * per_world_q
''', '''    object_root_position_offsets_w: wp.array(dtype=wp.vec3),
    num_objects: int,
    state_flag: wp.array(dtype=wp.int32),
    bank_jq: wp.array(dtype=wp.float32, ndim=2),
    bank_jqd: wp.array(dtype=wp.float32, ndim=2),
) -> None:
    """Reset selected worlds to a reference pose, optional open fingers, and zero velocity."""
    w = wp.tid()
    if reset_mask[w] == 0:
        return
    f = reset_frame[w]
    base = w * per_world_q
    k = state_flag[w]
    if k > 0:  # v2d: reset into a banked simulator state (FC_STATE_RESET)
        for c in range(per_world_q):
            joint_q[base + c] = bank_jq[k - 1, c]
        for object_id in range(num_objects):
            root_q = base + object_root_q_ids[object_id]
            offset = object_root_position_offsets_w[w * num_objects + object_id]
            joint_q[root_q] = joint_q[root_q] + offset[0]
            joint_q[root_q + 1] = joint_q[root_q + 1] + offset[1]
            joint_q[root_q + 2] = joint_q[root_q + 2] + offset[2]
        dof_base_bank = w * per_world_dof
        for dof in range(per_world_dof):
            joint_qd[dof_base_bank + dof] = bank_jqd[k - 1, dof]
        return
'''),
    ('''            table.object_root_position_offsets_w,
            table.num_objects,
        ],
    )
    newton.eval_fk(model, state.joint_q, state.joint_qd, state)''', '''            table.object_root_position_offsets_w,
            table.num_objects,
            *_v2d_states.arrays(table.world_count, table.reset_frame.device)[:3],
        ],
    )
    newton.eval_fk(model, state.joint_q, state.joint_qd, state)'''),
    ('''        table = build_reference_joint_q(scene, reference)
''', '''        table = build_reference_joint_q(scene, reference)
        _v2d_states.arrays(scene.world_count, device, table.shape[1], scene.model.joint_dof_count // scene.world_count,
                           table.shape[0])  # v2d: the bank is allocated before any graph capture
'''),
    # sampling: draw from the bank (no random draws while no bank is loaded)
    ('''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
) -> None:
    """Sample one reference reset frame and finger factor for each selected world."""''',
     '''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
    state_flag: wp.array(dtype=wp.int32),
    bank_frame: wp.array(dtype=wp.int32),
    bank_count: int,
    bank_p: float,
    bank_voc: float,
) -> None:
    """Sample one reference reset frame and finger factor for each selected world."""'''),
    ('''    reset_count[world] += 1


@wp.kernel
def prepare_explicit_reset(''', '''    state_flag[world] = 0
    if bank_count > 0:  # v2d: FC_STATE_RESET
        if curriculum_voc_scale[0] <= bank_voc:
            if wp.randf(rng) < bank_p:
                k = wp.min(int(wp.randf(rng) * float(bank_count)), bank_count - 1)
                state_flag[world] = k + 1
                reset_frame[world] = bank_frame[k]
                finger_scale[world] = 1.0
                steps_since_reset[world] = voc_decay_steps
                applied_voc_scale[world] = curriculum_voc_scale[0]
    reset_count[world] += 1


@wp.kernel
def prepare_explicit_reset('''),
    ('''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
) -> None:
    """Preserve the exact-pose semantics of an explicitly indexed reset."""''',
     '''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
    state_flag: wp.array(dtype=wp.int32),
) -> None:
    """Preserve the exact-pose semantics of an explicitly indexed reset."""'''),
    ('''    applied_voc_scale[world] = curriculum_voc_scale[0]


@wp.kernel
def advance_reference_reset(''', '''    applied_voc_scale[world] = curriculum_voc_scale[0]
    state_flag[world] = 0


@wp.kernel
def advance_reference_reset('''),
    ('''                self.steps_since_reset,
                self.applied_voc_scale,
            ],
        )

    def prepare_explicit(self, reset_mask: wp.array, curriculum_voc_scale: wp.array) -> None:''', '''                self.steps_since_reset,
                self.applied_voc_scale,
                _v2d_states.arrays(self.world_count, self.reset_frame.device)[0],
                _v2d_states.arrays(self.world_count, self.reset_frame.device)[3],
                _v2d_states.arrays(self.world_count, self.reset_frame.device)[4],
                _v2d_states.P,
                _v2d_states.VOC,
            ],
        )

    def prepare_explicit(self, reset_mask: wp.array, curriculum_voc_scale: wp.array) -> None:'''),
    ('''            inputs=[reset_mask, self.config.voc_decay_steps, curriculum_voc_scale],
            outputs=[self.finger_scale, self.steps_since_reset, self.applied_voc_scale],
        )

    def advance(''', '''            inputs=[reset_mask, self.config.voc_decay_steps, curriculum_voc_scale],
            outputs=[self.finger_scale, self.steps_since_reset, self.applied_voc_scale,
                     _v2d_states.arrays(self.world_count, self.reset_frame.device)[0]],
        )

    def advance('''),
])
