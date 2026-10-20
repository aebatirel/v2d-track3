#!/bin/bash
# Render a policy rollout to MP4 (headless) plus a 2x3 frame montage, to see what the robot does (2026-10-20).
# Usage: bash render_rollout.sh <checkpoint> <out_dir> [num_frames]
# Uses FlashCHORD's view_policy.py with the mp4 viewer backend; needs PYGLET_HEADLESS (no X display on the boxes).
# Keypoint and contact markers are off (their kernel fails with this warp version); object and wrist axes stay on.
# It shows the checkpoint's own reference scene from frame 0 with VOC 0, but view_policy reports reset_assist_steps=20,
# so it can differ slightly from the official evaluator: for looking, not for scoring.
set -u
CK=$1; OUT=$2; NF=${3:-181}; FC=/content/v2d/robotic_grounding/flash_chord
mkdir -p $OUT
cd $FC && PYGLET_HEADLESS=1 MUJOCO_GL=egl .venv/bin/python scripts/view_policy.py evaluation.checkpoint=$CK \
  viewer.backend=mp4 viewer.headless=true viewer.realtime=false viewer.output_path=$OUT/view.mp4 viewer.num_frames=$NF \
  viewer.width=960 viewer.height=540 markers.keypoints=false markers.contacts=false \
  "viewer.camera_position=${CAM_POS:-[0.55,-0.45,1.05]}" "viewer.camera_target=${CAM_TGT:-[0.0,0.0,0.65]}" \
  > $OUT/view.log 2>&1 || { echo "render FAILED"; tail -5 $OUT/view.log; exit 1; }
python - "$OUT" <<'EOF'
import sys, cv2, numpy as np
out = sys.argv[1]; cap = cv2.VideoCapture(f'{out}/view.mp4'); fr = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    fr.append(f)
idx = np.linspace(0, len(fr) - 1, 6).astype(int)
tiles = [cv2.putText(fr[i].copy(), f'f{i}', (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2) for i in idx]
m = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
cv2.imwrite(f'{out}/montage.jpg', cv2.resize(m, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(f'rendered {len(fr)} frames -> {out}/view.mp4, montage frames {idx.tolist()}')
EOF
