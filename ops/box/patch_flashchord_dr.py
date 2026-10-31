"""Start-state randomization for FlashCHORD training (2026-10-31; recipe screen arm D, docs/research/physics-2026-10-30/
physics-solver.md section 8). Idempotent. INERT unless FC_DR_RESET is set in the training process: with it unset the
hook imports nothing and wraps nothing, so the patched tree runs the upstream code. No config field is added, so the
checkpoint's resolved config is the control's and the evaluator (which rebuilds the env from that config) replays
nothing of it; explicit resets (every evaluation, tools/trace_rollout.py, the official evaluator) are never perturbed.

Why: repeated official draws of one checkpoint differ by ~10 um in frames 1-11, 5 mm by frames 5-25 and split by 2 cm
at contact events, and the 10-draw AUC sd of ep2 checkpoints is ~0.19-0.24 [M]. Training resets onto the reference
exactly (sampled frame, partly opened fingers), so the policy never sees the small start differences that the scored
draws then amplify. Hypothesis [H-dr]: small reset perturbations in training make the policy less sensitive to them
(cf. domain randomization of initial states, Tobin et al. 2017; OpenAI et al. 2019 "Solving Rubik's Cube").

FC_DR_RESET = "pos_mm,rot_rad,joint_rad" (commas or spaces; "1" = the defaults 1.5,0.015,0.01): at every SAMPLED
training reset (ReferenceReset.sample: the initial reset and every auto-reset) each object's root free joint gets a
uniform position offset in [-pos_mm, pos_mm] mm per world axis and a world-frame rotation by a rotation vector with
each component uniform in [-rot_rad, rot_rad] (angle <= sqrt(3) rot_rad), and every finger joint of both hands
(the reset table's finger_q_ids) gets a uniform offset in [-joint_rad, joint_rad] rad, clamped to its joint limits.
The floating wrists, the reference timestep, the finger opening and the settling hold are as upstream. The noise is
applied after the reset state is written (reset_kernel; with the state-bank patch also after a banked state is
loaded) and before forward kinematics and the first step. FC_DR_SEED (default 0; the job passes the training seed)
seeds a per-world stream of its own (Warp rand_init(seed', world + count * 104729)), so the upstream reset draws
(frames, finger openings, bank draws) are unchanged.
Mechanics (appended hook in lifecycle/reset.py, like patch_flashchord_voc.py's): ReferenceReset.sample marks the sampled
worlds, ReferenceReset.prepare_explicit clears the mark, reset_worlds perturbs marked worlds of its reset mask (and
clears the mark), then repeats newton.eval_fk; flags and counters are allocated in ReferenceResetTable.build (before
any graph capture). Combines with patch_flashchord_states.py in either order (no shared anchor).
FC_DR_SKIP_IMMEDIATE=1 (2026-10-31, opt-in; pack 10's standard-learner D cells): leave the deployment-exact starts of
ops/box/patch_flashchord.py's FC_IMMEDIATE_FIRST_FRAME unperturbed. Those starts are drawn inside ReferenceReset.sample
(frame 0, finger factor 1, no hold, curriculum assist), so without the flag DR marks and perturbs them like every other
sampled reset. A world counts as such a start iff, right after the upstream sample, reset_frame == 0, finger_scale ==
1.0 and steps_since_reset == voc_decay_steps (an upstream sampled reset always has finger_scale = U(0,1) x openness < 1
and steps_since_reset = 0; only the FC_IMMEDIATE_FIRST_FRAME branch writes that triple). Its mark is cleared, so the
world is reset exactly as without DR; a per-world counter of skipped starts is kept for tests. Unset: as before.
Usage: python patch_flashchord_dr.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
pkg = os.path.join(fc, 'src/flash_chord')
TAG = '# v2d patch: FC_DR_RESET'

open(os.path.join(pkg, 'lifecycle/v2d_dr.py'), 'w').write('''"""v2d patch: FC_DR_RESET (ops/box/patch_flashchord_dr.py): training-only start-state randomization of sampled
resets. Imported by lifecycle/reset.py only while FC_DR_RESET is set."""
import inspect
import math
import os

import warp as wp

DEFAULTS = (1.5, 0.015, 0.01)


def parse(text):
    """'pos_mm,rot_rad,joint_rad' (commas or spaces) or '1' (defaults) -> (pos_mm, rot_rad, joint_rad)."""
    text = (text or "").strip()
    if text in ("", "0"):
        return None
    if text == "1":
        return DEFAULTS
    values = tuple(float(x) for x in text.replace(",", " ").split())
    if len(values) != 3 or any(not math.isfinite(v) or v < 0.0 for v in values):
        raise ValueError(f"FC_DR_RESET must be '1' or three non-negative numbers pos_mm,rot_rad,joint_rad, got {text!r}")
    return values


BOUNDS = parse(os.environ.get("FC_DR_RESET", ""))
ON = BOUNDS is not None
SEED = int(os.environ.get("FC_DR_SEED", "0") or 0)
SKIP_IMMEDIATE = os.environ.get("FC_DR_SKIP_IMMEDIATE", "").strip() not in ("", "0")
_CACHE = {}
_SKIPS = {}


def skips(world_count, device, create=False):
    """int32 [W]: deployment-exact starts left unperturbed so far (FC_DR_SKIP_IMMEDIATE)."""
    key = (int(world_count), str(wp.get_device(device)))
    if key not in _SKIPS:
        if not create:
            raise RuntimeError("v2d_dr.skips: not allocated; ReferenceResetTable.build allocates it before capture")
        _SKIPS[key] = wp.zeros(int(world_count), dtype=wp.int32, device=device)
    return _SKIPS[key]


def arrays(world_count, device, create=False):
    """(flag int32 [W]: 1 = sampled since the last reset_worlds, count int32 [W]: perturbed resets so far)."""
    key = (int(world_count), str(wp.get_device(device)))
    if key not in _CACHE:
        if not create:
            raise RuntimeError("v2d_dr.arrays: not allocated; ReferenceResetTable.build allocates them before capture")
        _CACHE[key] = (wp.zeros(int(world_count), dtype=wp.int32, device=device),
                       wp.zeros(int(world_count), dtype=wp.int32, device=device))
    return _CACHE[key]


@wp.kernel
def mark_kernel(reset_mask: wp.array(dtype=wp.int32), value: int, flag: wp.array(dtype=wp.int32)) -> None:
    w = wp.tid()
    if reset_mask[w] != 0:
        flag[w] = value


@wp.kernel
def skip_immediate_kernel(
    reset_mask: wp.array(dtype=wp.int32),
    reset_frame: wp.array(dtype=wp.int32),
    finger_scale: wp.array(dtype=wp.float32),
    steps_since_reset: wp.array(dtype=wp.int32),
    voc_decay_steps: int,
    flag: wp.array(dtype=wp.int32),
    skipped: wp.array(dtype=wp.int32),
) -> None:
    w = wp.tid()
    if reset_mask[w] == 0:
        return
    if reset_frame[w] == 0 and finger_scale[w] == 1.0 and steps_since_reset[w] == voc_decay_steps:
        flag[w] = 0
        skipped[w] = skipped[w] + 1


@wp.kernel
def dr_kernel(
    joint_q: wp.array(dtype=wp.float32),
    per_world_q: int,
    reset_mask: wp.array(dtype=wp.int32),
    flag: wp.array(dtype=wp.int32),
    count: wp.array(dtype=wp.int32),
    object_root_q_ids: wp.array(dtype=wp.int32),
    num_objects: int,
    finger_q_ids: wp.array(dtype=wp.int32),
    finger_lower: wp.array(dtype=wp.float32),
    finger_upper: wp.array(dtype=wp.float32),
    num_fingers: int,
    seed: int,
    pos_m: float,
    rot_rad: float,
    joint_rad: float,
) -> None:
    w = wp.tid()
    if reset_mask[w] == 0:
        return
    if flag[w] == 0:
        return
    flag[w] = 0
    rng = wp.rand_init(seed, w + count[w] * 104729)
    count[w] = count[w] + 1
    base = w * per_world_q
    for o in range(num_objects):
        q = base + object_root_q_ids[o]
        joint_q[q] = joint_q[q] + pos_m * (2.0 * wp.randf(rng) - 1.0)
        joint_q[q + 1] = joint_q[q + 1] + pos_m * (2.0 * wp.randf(rng) - 1.0)
        joint_q[q + 2] = joint_q[q + 2] + pos_m * (2.0 * wp.randf(rng) - 1.0)
        rx = rot_rad * (2.0 * wp.randf(rng) - 1.0)
        ry = rot_rad * (2.0 * wp.randf(rng) - 1.0)
        rz = rot_rad * (2.0 * wp.randf(rng) - 1.0)
        rv = wp.vec3(rx, ry, rz)
        angle = wp.length(rv)
        if angle > 0.0:
            dq = wp.quat_from_axis_angle(rv / angle, angle)
            cur = wp.quat(joint_q[q + 3], joint_q[q + 4], joint_q[q + 5], joint_q[q + 6])
            nq = wp.normalize(dq * cur)
            joint_q[q + 3] = nq[0]
            joint_q[q + 4] = nq[1]
            joint_q[q + 5] = nq[2]
            joint_q[q + 6] = nq[3]
    for f in range(num_fingers):
        i = base + finger_q_ids[f]
        joint_q[i] = wp.clamp(joint_q[i] + joint_rad * (2.0 * wp.randf(rng) - 1.0), finger_lower[f], finger_upper[f])


def install(ns):
    """Wrap lifecycle/reset.py's ReferenceResetTable.build, ReferenceReset.sample / prepare_explicit and reset_worlds."""
    table_cls, policy_cls, reset_worlds0, newton = ns["ReferenceResetTable"], ns["ReferenceReset"], ns["reset_worlds"], ns["newton"]
    pos_m, rot_rad, joint_rad = BOUNDS[0] * 1.0e-3, BOUNDS[1], BOUNDS[2]
    seed = 7919 * SEED + 1000003                         # its own stream; never the reset config's seed itself
    build0 = table_cls.build.__func__

    def build(cls, scene, reference, device=None):
        table = build0(cls, scene, reference, device=device)
        for binding in scene.objects:                    # the kernel assumes [x y z qx qy qz qw] per free joint
            ids = tuple(int(i) for i in binding.root.free_q_ids)
            if ids != tuple(range(ids[0], ids[0] + 7)):
                raise ValueError(f"FC_DR_RESET: object {binding.name!r} free joint coords {ids} are not 7 contiguous")
        arrays(table.world_count, table.reset_frame.device, create=True)
        skips(table.world_count, table.reset_frame.device, create=True)
        print(f"v2d FC_DR_RESET: sampled resets perturbed by +-{BOUNDS[0]} mm, +-{rot_rad} rad (rotation vector per "
              f"axis), fingers +-{joint_rad} rad; {table.num_objects} objects, {table.finger_q_ids.shape[0]} finger joints, "
              f"{table.world_count} worlds, seed {SEED}"
              + ("; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-exact starts not perturbed)" if SKIP_IMMEDIATE else ""),
              flush=True)
        return table

    table_cls.build = classmethod(build)
    sample0, explicit0 = policy_cls.sample, policy_cls.prepare_explicit

    def sample(self, reset_mask, curriculum_voc_scale):
        sample0(self, reset_mask, curriculum_voc_scale)
        flag = arrays(self.world_count, self.reset_frame.device)[0]
        wp.launch(mark_kernel, dim=self.world_count, inputs=[reset_mask, 1], outputs=[flag])
        if SKIP_IMMEDIATE:                               # the FC_IMMEDIATE_FIRST_FRAME starts keep their exact state
            wp.launch(skip_immediate_kernel, dim=self.world_count,
                      inputs=[reset_mask, self.reset_frame, self.finger_scale, self.steps_since_reset, self.config.voc_decay_steps],
                      outputs=[flag, skips(self.world_count, self.reset_frame.device)])

    def prepare_explicit(self, reset_mask, curriculum_voc_scale):
        explicit0(self, reset_mask, curriculum_voc_scale)
        flag = arrays(self.world_count, self.reset_frame.device)[0]
        wp.launch(mark_kernel, dim=self.world_count, inputs=[reset_mask, 0], outputs=[flag])

    policy_cls.sample, policy_cls.prepare_explicit = sample, prepare_explicit
    signature = inspect.signature(reset_worlds0)

    def reset_worlds(*args, **kwargs):
        reset_worlds0(*args, **kwargs)
        bound = signature.bind(*args, **kwargs)
        model, table, state = bound.arguments["model"], bound.arguments["table"], bound.arguments["state"]
        mask = bound.arguments.get("reset_mask")
        flag, count = arrays(table.world_count, table.reset_frame.device)
        wp.launch(dr_kernel, dim=table.world_count, inputs=[
            state.joint_q, table.per_world_q, table.all_reset_mask if mask is None else mask, flag, count,
            table.object_root_q_ids, table.num_objects, table.finger_q_ids, table.finger_lower, table.finger_upper,
            table.finger_q_ids.shape[0], seed, pos_m, rot_rad, joint_rad])
        newton.eval_fk(model, state.joint_q, state.joint_qd, state)

    reset_worlds.__doc__ = reset_worlds0.__doc__
    ns["reset_worlds"] = reset_worlds
''')
print('installed:', os.path.join(pkg, 'lifecycle/v2d_dr.py'))

p = os.path.join(pkg, 'lifecycle/reset.py')
s = open(p).read()
if TAG in s:
    print('already patched:', p)
else:
    for name in ('class ReferenceResetTable:', 'class ReferenceReset:', 'def reset_worlds(', '    def sample(self, reset_mask',
                 '    def prepare_explicit(self, reset_mask', 'import newton\n'):
        if name not in s:
            sys.exit(f'{name!r} not found in {p}: FlashCHORD changed, patch not applied')
    s += f'''

{TAG} (ops/box/patch_flashchord_dr.py); inert unless FC_DR_RESET is set in the process
def _v2d_dr_hook() -> None:
    import os

    if os.environ.get("FC_DR_RESET", "").strip() not in ("", "0"):
        from flash_chord.lifecycle import v2d_dr

        v2d_dr.install(globals())


_v2d_dr_hook()
'''
    open(p, 'w').write(s)
    print('patched:', p)
