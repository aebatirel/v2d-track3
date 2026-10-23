"""Recovery training for FlashCHORD (2026-10-23; owner: "the drop shouldn't stop our recipe, it should still go after
the grasp; mid-episode a person may leave an object somewhere, it drops and the other hand must pick it up").
Idempotent; inert unless FC_DROP_START is set in the training process (an unset variable reproduces upstream behaviour
exactly; no config field is added, so the checkpoint's resolved config stays loadable by the unpatched evaluator).

Why: FlashCHORD's training never shows the policy a dropped or misplaced object. Every reset puts the objects exactly
on their reference, and an episode terminates as soon as an object is 10 cm / 0.5 rad off it (or a wrist 15 cm off).
The official evaluation never terminates, so after a drop the policy is in states it never trained on.
With FC_DROP_START = p > 0, once the curriculum assist is below FC_DROP_VOC (default 0.3: from 49M steps of the
stock schedule; our 70M fine-tunes end in the 0.1 stage, so FlashCHORD's own first_frame_voc_threshold 0.1 would never
open), a share p of the sampled resets become DROP STARTS: fingers fully open, no settling hold, no assist for the
whole episode (the virtual object controller would pull the object back onto its reference), and every
object of that world shifted horizontally by FC_DROP_SHIFT = "min,max" m (default 0.03-0.08) in a random direction,
so an object held at that frame falls and one on the table lies off its reference. In those worlds the termination
thresholds are relaxed to FC_DROP_RELAX = "object_pos_m,object_ori_rad,wrist_pos_m" (default 0.35, 3.2, 0.25; the
residual wrist envelope is 0.2 m) for the rest of the episode, so the policy is rewarded for going and getting the
object and carrying it back (the rewards are unchanged). Cf. PHC's fail-state recovery (Luo et al., ICCV 2023).
1. writes flash_chord/lifecycle/v2d_drop.py (the shared per-world drop flag and shift);
2. patches lifecycle/reset.py: sample_reference_reset (drop starts), reset_kernel (the shift), prepare_explicit_reset
   (clears the flag), advance_reference_reset / sync_reference_voc (no assist in drop worlds), the launches and the
   builders (allocation before any graph capture);
3. patches lifecycle/termination.py: termination_kernel (relaxed thresholds where the flag is set).
Apply after patch_flashchord.py (FC_IMMEDIATE_FIRST_FRAME edits the same reset kernel; ops/box/lib.sh fc_patches).
Usage: python patch_flashchord_drop.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
pkg = os.path.join(fc, 'src/flash_chord')
TAG = '# v2d patch: FC_DROP_START'

open(os.path.join(pkg, 'lifecycle/v2d_drop.py'), 'w').write(f'''{TAG} (ops/box/patch_flashchord_drop.py): per-world drop-start flag and object
shift, shared by lifecycle/reset.py and lifecycle/termination.py. Inert while FC_DROP_START is unset.
import os

import warp as wp

P = float(os.environ.get("FC_DROP_START", "0"))
SHIFT = tuple(float(x) for x in os.environ.get("FC_DROP_SHIFT", "0.03,0.08").split(","))
RELAX = tuple(float(x) for x in os.environ.get("FC_DROP_RELAX", "0.35,3.2,0.25").split(","))
VOC = float(os.environ.get("FC_DROP_VOC", "0.3"))
_FLAGS = {{}}


def flags(world_count, device=None):
    """(drop flag int32 [W], object shift vec3 [W]) for this world count and device; allocated once."""
    key = (int(world_count), str(wp.get_device(device)))
    if key not in _FLAGS:
        _FLAGS[key] = (wp.zeros(int(world_count), dtype=wp.int32, device=device),
                       wp.zeros(int(world_count), dtype=wp.vec3, device=device))
    return _FLAGS[key]
'''.replace(f'{TAG} (ops', f'"""{TAG.lstrip("# ")} (ops', 1).replace('Inert while FC_DROP_START is unset.\n', 'Inert while FC_DROP_START is unset."""\n', 1))
print('installed:', os.path.join(pkg, 'lifecycle/v2d_drop.py'))


def patch(path, edits):
    s = open(path).read()
    if TAG in s:
        print('already patched:', path); return
    for a, b in edits:
        if s.count(a) != 1:
            sys.exit(f'anchor not found once in {path} ({s.count(a)}x): {a[:80]!r}; FlashCHORD changed, patch not applied')
        s = s.replace(a, b)
    open(path, 'w').write(s); print('patched:', path)


imp = '''import warp as wp
'''
patch(os.path.join(pkg, 'lifecycle/reset.py'), [
    ('from flash_chord.data.reference import Reference\n', f'''from flash_chord.data.reference import Reference
from flash_chord.lifecycle import v2d_drop as _v2d_drop  {TAG}

_V2D_DROP_P = wp.constant(_v2d_drop.P)
_V2D_SHIFT_MIN = wp.constant(_v2d_drop.SHIFT[0])
_V2D_SHIFT_MAX = wp.constant(_v2d_drop.SHIFT[1])
_V2D_DROP_VOC = wp.constant(_v2d_drop.VOC)
'''),
    ('''    object_root_position_offsets_w: wp.array(dtype=wp.vec3),
    num_objects: int,
) -> None:
    """Reset selected worlds to a reference pose, optional open fingers, and zero velocity."""''',
     '''    object_root_position_offsets_w: wp.array(dtype=wp.vec3),
    num_objects: int,
    drop_flag: wp.array(dtype=wp.int32),
    drop_shift: wp.array(dtype=wp.vec3),
) -> None:
    """Reset selected worlds to a reference pose, optional open fingers, and zero velocity."""'''),
    ('''        joint_q[root_q + 2] = joint_q[root_q + 2] + offset[2]
''', '''        joint_q[root_q + 2] = joint_q[root_q + 2] + offset[2]
        if drop_flag[w] != 0:  # v2d: drop start, the objects lie off their reference
            joint_q[root_q] = joint_q[root_q] + drop_shift[w][0]
            joint_q[root_q + 1] = joint_q[root_q + 1] + drop_shift[w][1]
'''),
    ('''            table.object_root_position_offsets_w,
            table.num_objects,
        ],
    )
    newton.eval_fk(model, state.joint_q, state.joint_qd, state)''', '''            table.object_root_position_offsets_w,
            table.num_objects,
            *_v2d_drop.flags(table.world_count, table.reset_frame.device),
        ],
    )
    newton.eval_fk(model, state.joint_q, state.joint_qd, state)'''),
    ('''        table = build_reference_joint_q(scene, reference)
''', '''        table = build_reference_joint_q(scene, reference)
        _v2d_drop.flags(scene.world_count, device)  # v2d: allocated before any graph capture
'''),
    ('''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
) -> None:
    """Sample one reference reset frame and finger factor for each selected world."""''',
     '''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
    drop_flag: wp.array(dtype=wp.int32),
    drop_shift: wp.array(dtype=wp.vec3),
) -> None:
    """Sample one reference reset frame and finger factor for each selected world."""'''),
    ('''    reset_count[world] += 1


@wp.kernel
def prepare_explicit_reset(''', '''    drop_flag[world] = 0
    if _V2D_DROP_P > 0.0 and curriculum_voc_scale[0] < _V2D_DROP_VOC:  # v2d: drop start
        if wp.randf(rng) < _V2D_DROP_P:
            drop_flag[world] = 1
            finger_scale[world] = 0.0
            steps_since_reset[world] = voc_decay_steps
            applied_voc_scale[world] = 0.0
            ang = wp.randf(rng) * 6.2831853
            rad = _V2D_SHIFT_MIN + wp.randf(rng) * (_V2D_SHIFT_MAX - _V2D_SHIFT_MIN)
            drop_shift[world] = wp.vec3(rad * wp.cos(ang), rad * wp.sin(ang), 0.0)
    reset_count[world] += 1


@wp.kernel
def prepare_explicit_reset('''),
    ('''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
) -> None:
    """Preserve the exact-pose semantics of an explicitly indexed reset."""''',
     '''    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
    drop_flag: wp.array(dtype=wp.int32),
) -> None:
    """Preserve the exact-pose semantics of an explicitly indexed reset."""'''),
    ('''    applied_voc_scale[world] = curriculum_voc_scale[0]


@wp.kernel
def advance_reference_reset(''', '''    applied_voc_scale[world] = curriculum_voc_scale[0]
    drop_flag[world] = 0


@wp.kernel
def advance_reference_reset('''),
    ('''                self.steps_since_reset,
                self.applied_voc_scale,
            ],
        )

    def prepare_explicit(self, reset_mask: wp.array, curriculum_voc_scale: wp.array) -> None:
        wp.launch(
            prepare_explicit_reset,''', '''                self.steps_since_reset,
                self.applied_voc_scale,
                *_v2d_drop.flags(self.world_count, self.reset_frame.device),
            ],
        )

    def prepare_explicit(self, reset_mask: wp.array, curriculum_voc_scale: wp.array) -> None:
        wp.launch(
            prepare_explicit_reset,'''),
    ('''            inputs=[reset_mask, self.config.voc_decay_steps, curriculum_voc_scale],
            outputs=[self.finger_scale, self.steps_since_reset, self.applied_voc_scale],
        )

    def advance(
        self,
        terminated: wp.array,
        truncated: wp.array,
        timestep: wp.array,
        episode_step: wp.array,
        curriculum_voc_scale: wp.array,
    ) -> None:
        wp.launch(
            advance_reference_reset,''', '''            inputs=[reset_mask, self.config.voc_decay_steps, curriculum_voc_scale],
            outputs=[self.finger_scale, self.steps_since_reset, self.applied_voc_scale,
                     _v2d_drop.flags(self.world_count, self.reset_frame.device)[0]],
        )

    def advance(
        self,
        terminated: wp.array,
        truncated: wp.array,
        timestep: wp.array,
        episode_step: wp.array,
        curriculum_voc_scale: wp.array,
    ) -> None:
        wp.launch(
            advance_reference_reset,'''),
    ('''        config = config or ReferenceResetConfig()
''', '''        config = config or ReferenceResetConfig()
        _v2d_drop.flags(world_count, device)  # v2d: allocated before any graph capture
'''),    ('''    timestep: wp.array(dtype=wp.int32),
    episode_step: wp.array(dtype=wp.int32),
) -> None:
    """Hold the reset frame with VOC=1, then advance under the curriculum scale."""''', '''    timestep: wp.array(dtype=wp.int32),
    episode_step: wp.array(dtype=wp.int32),
    drop_flag: wp.array(dtype=wp.int32),
) -> None:
    """Hold the reset frame with VOC=1, then advance under the curriculum scale."""'''),
    ('''    else:
        applied_voc_scale[world] = 1.0


@wp.kernel
def sync_reference_voc(
    voc_decay_steps: int,
    curriculum_voc_scale: wp.array(dtype=wp.float32),
    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
) -> None:
    """Update settled worlds immediately when the global curriculum changes."""
    world = wp.tid()
    if steps_since_reset[world] >= voc_decay_steps:
        applied_voc_scale[world] = curriculum_voc_scale[0]
''', '''    else:
        applied_voc_scale[world] = 1.0
    if drop_flag[world] != 0:  # v2d: no assist in a drop start
        applied_voc_scale[world] = 0.0


@wp.kernel
def sync_reference_voc(
    voc_decay_steps: int,
    curriculum_voc_scale: wp.array(dtype=wp.float32),
    steps_since_reset: wp.array(dtype=wp.int32),
    applied_voc_scale: wp.array(dtype=wp.float32),
    drop_flag: wp.array(dtype=wp.int32),
) -> None:
    """Update settled worlds immediately when the global curriculum changes."""
    world = wp.tid()
    if steps_since_reset[world] >= voc_decay_steps:
        applied_voc_scale[world] = curriculum_voc_scale[0]
    if drop_flag[world] != 0:  # v2d: no assist in a drop start
        applied_voc_scale[world] = 0.0
'''),
    ('''            outputs=[self.steps_since_reset, self.applied_voc_scale, timestep, episode_step],
        )

    def sync_curriculum(self, curriculum_voc_scale: wp.array) -> None:
        wp.launch(
            sync_reference_voc,
            dim=self.world_count,
            inputs=[self.config.voc_decay_steps, curriculum_voc_scale, self.steps_since_reset],
            outputs=[self.applied_voc_scale],
        )''', '''            outputs=[self.steps_since_reset, self.applied_voc_scale, timestep, episode_step,
                     _v2d_drop.flags(self.world_count, self.reset_frame.device)[0]],
        )

    def sync_curriculum(self, curriculum_voc_scale: wp.array) -> None:
        wp.launch(
            sync_reference_voc,
            dim=self.world_count,
            inputs=[self.config.voc_decay_steps, curriculum_voc_scale, self.steps_since_reset],
            outputs=[self.applied_voc_scale, _v2d_drop.flags(self.world_count, self.reset_frame.device)[0]],
        )'''),
])

patch(os.path.join(pkg, 'lifecycle/termination.py'), [
    (imp, imp + f'''
from flash_chord.lifecycle import v2d_drop as _v2d_drop  {TAG}

_V2D_RELAX_OBJ_POS = wp.constant(_v2d_drop.RELAX[0])
_V2D_RELAX_OBJ_ORI = wp.constant(_v2d_drop.RELAX[1])
_V2D_RELAX_WRIST_POS = wp.constant(_v2d_drop.RELAX[2])
'''),
    ('''    diagnostic_width: int,
    wrist_pos_err: wp.array(dtype=wp.float32),  # [W*num_hands] out''', '''    diagnostic_width: int,
    drop_flag: wp.array(dtype=wp.int32),  # [W] v2d: drop-start worlds (relaxed thresholds)
    wrist_pos_err: wp.array(dtype=wp.float32),  # [W*num_hands] out'''),
    ('''    w = wp.tid()
    base = w * bodies_per_world
    frame = timestep[w]''', '''    w = wp.tid()
    base = w * bodies_per_world
    wpt = wrist_pos_thresh
    opt = object_pos_thresh
    oot = object_ori_thresh
    if drop_flag[w] != 0:  # v2d: drop start, the policy must be able to go and get the object
        wpt = wp.max(wrist_pos_thresh, _V2D_RELAX_WRIST_POS)
        opt = wp.max(object_pos_thresh, _V2D_RELAX_OBJ_POS)
        oot = wp.max(object_ori_thresh, _V2D_RELAX_OBJ_ORI)
    frame = timestep[w]'''),
    ('''        if (enable_wrist_pos != 0 and dp > wrist_pos_thresh) or (enable_wrist_ori != 0 and do > wrist_ori_thresh):''',
     '''        if (enable_wrist_pos != 0 and dp > wpt) or (enable_wrist_ori != 0 and do > wrist_ori_thresh):'''),
    ('''        if (enable_object_pos != 0 and dp > object_pos_thresh) or (enable_object_ori != 0 and do > object_ori_thresh):''',
     '''        if (enable_object_pos != 0 and dp > opt) or (enable_object_ori != 0 and do > oot):'''),
    ('''            _TRACKING_DIAGNOSTIC_WIDTH,
        ],
        outputs=[
            buf.wrist_pos_err,''', '''            _TRACKING_DIAGNOSTIC_WIDTH,
            _v2d_drop.flags(buf.world_count, buf.wrist_done.device)[0],
        ],
        outputs=[
            buf.wrist_pos_err,'''),
    ('''        """Bind tracking inputs and allocate completion outputs."""
''', '''        """Bind tracking inputs and allocate completion outputs."""
        _v2d_drop.flags(scene.world_count, device)  # v2d: allocated before any graph capture
'''),
])
