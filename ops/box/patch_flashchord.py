"""Opt-in FlashCHORD patches for experiments (2026-10-22). Idempotent; each patch is inert unless its env var is set
in the training process, so an unset variable reproduces upstream behaviour exactly.

FC_OBJECT_KEYPOINT_SCALE: FlashCHORD's object-keypoint reward uses the object frame's six unit axis vectors (keypoints
1 m from the object origin) with exp(-error / 0.1) per keypoint, so a 3 deg wobble costs as much as 5 cm of position
error and errors past ~20 deg give almost no signal. The pose scorers (ADD-AUC, SP/MP) measure surface points of
10-60 cm objects. The variable scales the six vectors (e.g. 0.15 = keypoints 15 cm out). Training reward only:
observations, terminations and the evaluator do not use them.
FC_IMMEDIATE_FIRST_FRAME (probability p): FlashCHORD's Sharpa reset (ReferenceReset) always opens the fingers (finger
angles x U(0, 0.7)) and holds the reset frame with full object assist for 20 steps, while the official evaluation
(reset_mode=explicit) starts at frame 0 with exact fingers, no hold and no assist: a start the policy never trains on.
NVIDIA's ReconBody reset has "deployment-exact" immediate starts for this (25 % then 50 % in its final stages); the
Sharpa reset does not. With p > 0, once the curriculum assist is below first_frame_voc_threshold (0.1, the late
stages), a fraction p of resets become explicit-like: frame 0, finger factor 1, no hold, curriculum assist.
Usage: python patch_flashchord.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
p = os.path.join(fc, 'src/flash_chord/objectives/keypoints.py')
s = open(p).read()
tag = '# v2d patch: FC_OBJECT_KEYPOINT_SCALE'
anchor = """KEYPOINT_VECS_NP = np.array(
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]],
    dtype=np.float32,
)
"""
if tag in s:
    print('already patched:', p)
elif s.count(anchor) != 1:
    sys.exit(f'anchor not found in {p}: FlashCHORD changed, patch not applied')
else:
    s = s.replace(anchor, anchor + "KEYPOINT_VECS_NP = KEYPOINT_VECS_NP * np.float32(__import__('os').environ.get('FC_OBJECT_KEYPOINT_SCALE', '1'))  "
                  + tag + "\n")
    open(p, 'w').write(s)
    print('patched:', p)

# FC_IMMEDIATE_FIRST_FRAME
p = os.path.join(fc, 'src/flash_chord/lifecycle/reset.py')
s = open(p).read()
tag = '# v2d patch: FC_IMMEDIATE_FIRST_FRAME'
if tag in s:
    print('already patched:', p)
    sys.exit(0)
a1 = "import warp as wp\n"
a2 = """    reset_frame[world] = frame
    finger_scale[world] = wp.randf(rng) * reset_finger_openness
    steps_since_reset[world] = 0
    if voc_decay_steps == 0:
        applied_voc_scale[world] = curriculum_voc_scale[0]
    else:
        applied_voc_scale[world] = 1.0
    reset_count[world] += 1
"""
if s.count(a1) < 1 or s.count(a2) != 1:
    sys.exit(f'anchor not found in {p}: FlashCHORD changed, patch not applied')
s = s.replace(a1, a1 + "_V2D_IMMEDIATE = wp.constant(float(__import__('os').environ.get('FC_IMMEDIATE_FIRST_FRAME', '0')))  " + tag + "\n", 1)
s = s.replace(a2, a2.replace("    reset_count[world] += 1\n", """    if _V2D_IMMEDIATE > 0.0 and curriculum_voc_scale[0] < first_frame_voc_threshold:  # v2d: deployment-exact start
        if wp.randf(rng) < _V2D_IMMEDIATE:
            reset_frame[world] = 0
            finger_scale[world] = 1.0
            steps_since_reset[world] = voc_decay_steps
            applied_voc_scale[world] = curriculum_voc_scale[0]
    reset_count[world] += 1
"""))
open(p, 'w').write(s)
print('patched:', p)
