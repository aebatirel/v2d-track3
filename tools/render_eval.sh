#!/bin/bash
# Render a checkpoint the way the official evaluator runs it: frame 0 to the end, no early termination, no auto-reset,
# VOC 0 (view_policy default), no reset assist. Usage: render_eval.sh <checkpoint> <out_dir> <num_frames>
CK=$1; OUT=$2; NF=$3; FC=/content/v2d/robotic_grounding/flash_chord; mkdir -p $OUT
T="wrist_position object_position object_orientation"
OV=""; for t in $T; do OV="$OV termination.$t.enabled=false"; done
cd $FC && PYGLET_HEADLESS=1 MUJOCO_GL=egl .venv/bin/python scripts/view_policy.py evaluation.checkpoint=$CK \
  viewer.backend=mp4 viewer.headless=true viewer.realtime=false viewer.output_path=$OUT/view.mp4 viewer.num_frames=$NF \
  viewer.width=960 viewer.height=540 markers.keypoints=false markers.contacts=false \
  "viewer.camera_position=[0.55,-0.45,1.05]" "viewer.camera_target=[0.0,0.0,0.65]" \
  reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true $OV > $OUT/view.log 2>&1
echo "rc=$?" >> $OUT/view.log
