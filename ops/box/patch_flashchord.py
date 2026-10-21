"""Opt-in FlashCHORD patches for experiments (2026-10-22). Idempotent; each patch is inert unless its env var is set
in the training process, so an unset variable reproduces upstream behaviour exactly.

FC_OBJECT_KEYPOINT_SCALE: FlashCHORD's object-keypoint reward uses the object frame's six unit axis vectors (keypoints
1 m from the object origin) with exp(-error / 0.1) per keypoint, so a 3 deg wobble costs as much as 5 cm of position
error and errors past ~20 deg give almost no signal. The pose scorers (ADD-AUC, SP/MP) measure surface points of
10-60 cm objects. The variable scales the six vectors (e.g. 0.15 = keypoints 15 cm out). Training reward only:
observations, terminations and the evaluator do not use them.
Usage: python patch_flashchord.py <flash_chord dir>
"""
import os, sys

fc = sys.argv[1]
p = os.path.join(fc, 'src/flash_chord/objectives/keypoints.py')
s = open(p).read()
tag = '# v2d patch: FC_OBJECT_KEYPOINT_SCALE'
if tag in s:
    print('already patched:', p)
    sys.exit(0)
anchor = """KEYPOINT_VECS_NP = np.array(
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]],
    dtype=np.float32,
)
"""
if s.count(anchor) != 1:
    sys.exit(f'anchor not found in {p}: FlashCHORD changed, patch not applied')
s = s.replace(anchor, anchor + "KEYPOINT_VECS_NP = KEYPOINT_VECS_NP * np.float32(__import__('os').environ.get('FC_OBJECT_KEYPOINT_SCALE', '1'))  "
              + tag + "\n")
open(p, 'w').write(s)
print('patched:', p)
