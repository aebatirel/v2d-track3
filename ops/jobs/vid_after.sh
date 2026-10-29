#!/bin/bash
# Video material for the owner after a glock_public.sh episode (2026-10-23; reporting only, no ground truth): the chosen
# checkpoint played like the official evaluator, recorded as a body-pose trace (tools/trace_rollout.py policy, for the
# local 3-D / sim-vs-real videos) and rendered by FlashCHORD's viewer in the same pass (view.mp4), plus the rest check
# of that rollout. Run on the box while a HOLD keeps it up; then push-run and release the hold.
# Usage: vid_after.sh EP      output /content/results/glock_public/epEP/vid/
. /content/v2d-track3/ops/box/lib.sh
EP=$1; O=/content/results/glock_public/ep$EP; V=$O/vid; FC=/content/v2d/robotic_grounding/flash_chord; mkdir -p $V
CK=$(python -c "import json; print(json.load(open('$O/best/summary.json'))['checkpoint'])")
[ -s "$CK" ] || CK=$O/best/policy.safetensors                    # a pulled run keeps only every 10th checkpoint
REF=$(ls /content/refs/glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet | head -1)
N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$REF').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
OV="evaluation.checkpoint=$CK reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
# the viewer must be the headless mp4 backend (as tools/render_eval.sh), or view_policy serves an interactive viewer
OV="$OV viewer.backend=mp4 viewer.headless=true viewer.realtime=false viewer.output_path=$V/view.mp4 viewer.num_frames=$N"
OV="$OV viewer.width=960 viewer.height=540 markers.keypoints=false markers.contacts=false"
( cd $FC && DEV=cuda PYGLET_HEADLESS=1 MUJOCO_GL=egl timeout 1200 .venv/bin/python $REPO_DIR/tools/trace_rollout.py policy $V/policy_trace.npz $OV \
    "viewer.camera_position=[0.55,-0.45,1.05]" "viewer.camera_target=[0.0,0.0,0.65]" ) > $V/trace.log 2>&1
python $REPO_DIR/tools/rest_check.py $V/policy_trace.npz $REF > $V/rest_check_policy.json 2>&1
echo "vid_after ep$EP: checkpoint $(basename $CK), $(ls $V | tr '\n' ' ')"
