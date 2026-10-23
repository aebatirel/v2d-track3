#!/bin/bash
# Video material for the owner after a glock_public.sh episode (2026-10-23; reporting only, no ground truth): the chosen
# checkpoint played like the official evaluator, recorded as a body-pose trace (tools/trace_rollout.py policy, for the
# local 3-D / sim-vs-real videos) and rendered by FlashCHORD's viewer (tools/render_eval.sh), plus the rest check of
# that rollout. Run on the box while a HOLD keeps it up; then push-run and release the hold.
# Usage: vid_after.sh EP      output /content/results/glock_public/epEP/vid/
. /content/v2d-track3/ops/box/lib.sh
EP=$1; O=/content/results/glock_public/ep$EP; V=$O/vid; FC=/content/v2d/robotic_grounding/flash_chord; mkdir -p $V
CK=$(python -c "import json; print(json.load(open('$O/best/summary.json'))['checkpoint'])")
REF=$(ls /content/refs/glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet | head -1)
N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$REF').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
OV="evaluation.checkpoint=$CK reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
( cd $FC && DEV=cuda MUJOCO_GL=egl .venv/bin/python $REPO_DIR/tools/trace_rollout.py policy $V/policy_trace.npz $OV ) > $V/trace.log 2>&1
bash $REPO_DIR/tools/render_eval.sh $CK $V $N
python $REPO_DIR/tools/rest_check.py $V/policy_trace.npz $REF > $V/rest_check_policy.json 2>&1
echo "vid_after ep$EP: checkpoint $(basename $CK), $(ls $V | tr '\n' ' ')"
