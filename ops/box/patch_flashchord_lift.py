"""Contact-moment training starts for FlashCHORD (2026-11-02, perfect-following lane; docs/research/work/pf-lift-20261102/
PREREG.md). Idempotent. INERT unless FC_LIFT_WINDOWS is set in the training process: with it unset the hook imports
nothing and wraps nothing, so the patched tree runs the upstream code. No config field is added, so the checkpoint's
resolved config is the control's and the evaluator (which rebuilds the env from that config and resets explicitly) never
replays it.

Why [M, H5p7]: the remaining deterministic losses of the eval policies start ~10 frames after a grasp begins (the lift):
eval 25 pieces f41 / f173 (holds from f31 / f163), eval 30 sweeper f36-52 (hold from f42), eval 3 pot f66-68 (hold from
f57), eval 14 (after the bridge repair) f27-31. FlashCHORD draws training reset frames uniformly over the episode, so a
grasp-and-lift window of ~20 frames gets ~20 / T of the starts. Hypothesis [H-lift]: drawing a share of the sampled
resets from those windows gives the policy more practice at grasp / lift and lowers the lift loss.

FC_LIFT_WINDOWS = "a-b,c-d,..." inclusive reference-frame windows (tools/lift_windows.py derives them from our reference's
hold phases: [start - 5, start + 15]; GT-free); FC_LIFT_P = share of sampled resets redrawn uniformly from the windows'
frames (default 0.3); FC_LIFT_SEED seeds its own per-world stream (default 0). Only ReferenceReset.sample (training
auto-resets and the initial reset) is wrapped: after the upstream sample, a kernel redraws reset_frame for a share P of the
masked worlds; frame-0 starts drawn by the first-frame probability are left alone. Finger opening, the settling hold and
the curriculum assist are as upstream. Explicit resets (every evaluation) are never touched.
Usage: python patch_flashchord_lift.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
pkg = os.path.join(fc, 'src/flash_chord')
TAG = '# v2d patch: FC_LIFT_WINDOWS'

open(os.path.join(pkg, 'lifecycle/v2d_lift.py'), 'w').write('''"""v2d patch: FC_LIFT_WINDOWS (ops/box/patch_flashchord_lift.py): training-only extra reset starts in grasp / lift
windows. Imported by lifecycle/reset.py only while FC_LIFT_WINDOWS is set."""
import os

import numpy as np
import warp as wp


def parse(text):
    frames = []
    for part in (text or "").replace(" ", "").split(","):
        if not part:
            continue
        a, b = (int(x) for x in part.split("-"))
        if b < a:
            raise ValueError(f"FC_LIFT_WINDOWS: bad window {part!r}")
        frames.extend(range(a, b + 1))
    return sorted(set(frames))


FRAMES = parse(os.environ.get("FC_LIFT_WINDOWS", ""))
P = float(os.environ.get("FC_LIFT_P", "0.3"))
SEED = int(os.environ.get("FC_LIFT_SEED", "0") or 0)
_CACHE = {}


@wp.kernel
def lift_kernel(
    reset_mask: wp.array(dtype=wp.int32),
    reset_frame: wp.array(dtype=wp.int32),
    frames: wp.array(dtype=wp.int32),
    n_frames: int,
    p: float,
    seed: int,
    count: wp.array(dtype=wp.int32),
    redrawn: wp.array(dtype=wp.int32),
) -> None:
    w = wp.tid()
    if reset_mask[w] == 0:
        return
    rng = wp.rand_init(seed, w + count[w] * 104729)
    count[w] = count[w] + 1
    if reset_frame[w] == 0:                              # keep the first-frame starts of the upstream sampler
        return
    if wp.randf(rng) < p:
        i = wp.min(int(wp.randf(rng) * float(n_frames)), n_frames - 1)
        reset_frame[w] = frames[i]
        redrawn[w] = redrawn[w] + 1


def install(ns):
    policy_cls = ns["ReferenceReset"]
    build0, sample0 = policy_cls.build.__func__, policy_cls.sample
    seed = 104723 * SEED + 7

    def build(cls, world_count, num_frames, config=None, device=None):
        pol = build0(cls, world_count, num_frames, config=config, device=device)
        fr = [f for f in FRAMES if 0 < f < num_frames - 1]
        if not fr:
            raise ValueError(f"FC_LIFT_WINDOWS: no window frame inside 1..{num_frames - 2}")
        _CACHE[id(pol)] = (wp.array(np.asarray(fr, np.int32), dtype=wp.int32, device=device), len(fr),
                           wp.zeros(world_count, dtype=wp.int32, device=device), wp.zeros(world_count, dtype=wp.int32, device=device))
        print(f"v2d FC_LIFT_WINDOWS: {len(fr)} window frames ({fr[0]}..{fr[-1]}), share {P}, seed {SEED}, {world_count} worlds", flush=True)
        return pol

    def sample(self, reset_mask, curriculum_voc_scale):
        sample0(self, reset_mask, curriculum_voc_scale)
        frames, n, count, redrawn = _CACHE[id(self)]
        wp.launch(lift_kernel, dim=self.world_count, inputs=[reset_mask, self.reset_frame, frames, n, P, seed, count, redrawn])

    policy_cls.build = classmethod(build)
    policy_cls.sample = sample
''')
print('installed:', os.path.join(pkg, 'lifecycle/v2d_lift.py'))

p = os.path.join(pkg, 'lifecycle/reset.py')
s = open(p).read()
if TAG in s:
    print('already patched:', p)
else:
    for name in ('class ReferenceReset:', '    def sample(self, reset_mask', '    def build(\n        cls,\n        world_count: int,'):
        if name not in s:
            sys.exit(f'{name!r} not found in {p}: FlashCHORD changed, patch not applied')
    s += f'''

{TAG} (ops/box/patch_flashchord_lift.py); inert unless FC_LIFT_WINDOWS is set in the process
def _v2d_lift_hook() -> None:
    import os

    if os.environ.get("FC_LIFT_WINDOWS", "").strip():
        from flash_chord.lifecycle import v2d_lift

        v2d_lift.install(globals())


_v2d_lift_hook()
'''
    open(p, 'w').write(s)
    print('patched:', p)
