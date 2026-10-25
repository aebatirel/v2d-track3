#!/bin/bash
# Video of ONE eval policy that is not a glock_public "best" (2026-10-25; owner: "where are the robot hands?" for eval
# 25's standard learner; reporting only: no ground truth, nothing is chosen from it). Pulls RUN, sets FlashCHORD up as
# eval_videos.sh does, then plays the checkpoint like the official evaluator (frame 0 to the end, no assist, no
# termination) with FlashCHORD's own headless renderer (view.mp4: hands and objects) while tools/trace_rollout.py
# records every body pose (policy_trace.npz). A fresh rollout of the same checkpoint: GPU physics is not repeatable, so
# it may land in either of the policy's outcome modes.
# Usage: RUN=<run> EP=<n> CK=<path under /content, e.g. results/final_eval/ep25/policy.safetensors> REFV=<perc2mcks>
#        bash ops/jobs/vid_policy.sh        Output: /content/results/vid_policy/ep<EP>/{view.mp4,policy_trace.npz,trace.log}
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; FC=/content/v2d/robotic_grounding/flash_chord; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
O=/content/results/vid_policy/ep${EP:?EP missing}; mkdir -p $O
for inc in "runs/${RUN:?RUN missing}/refs/${REFV:?REFV missing}/ep$EP/*" "runs/$RUN/${CK:?CK missing}"; do   # only what is needed
  hf download "$HF_STORE" --repo-type dataset --include "$inc" --local-dir /content/hfstore >> $J 2>&1 \
    || { log "vid_policy: download $inc FAILED" >> $J; exit 1; }        # (a whole-run pull stalled 55 min on HTTP 429)
done
mkdir -p /content/refs /content/results && cp -rn /content/hfstore/runs/$RUN/refs/. /content/refs/ && cp -rn /content/hfstore/runs/$RUN/results/. /content/results/
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
python $REPO_DIR/pipeline/make_assets.py $LIB /content/assets >> $J 2>&1 || { log "vid_policy: make_assets FAILED" >> $J; exit 1; }
fc_patches $J || exit 1
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml; [ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E
mkdir -p /workspace && { [ -e /workspace/refs ] || ln -s /content/refs /workspace/refs; }   # the checkpoint's task path
REF=$(ls /content/refs/${REFV:?REFV missing}/ep$EP/processed/*/*/*.parquet | head -1)
N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$REF').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
OV="evaluation.checkpoint=/content/${CK:?CK missing} task.parquet='$REF' reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
OV="$OV viewer.backend=mp4 viewer.headless=true viewer.realtime=false viewer.output_path=$O/view.mp4 viewer.num_frames=$N"
OV="$OV viewer.width=960 viewer.height=540 markers.keypoints=false markers.contacts=false"
log "vid_policy ep$EP: run $RUN, checkpoint $CK, reference $REF, $N frames" >> $J
( cd $FC && DEV=cuda PYGLET_HEADLESS=1 MUJOCO_GL=egl timeout 1200 .venv/bin/python $REPO_DIR/tools/trace_rollout.py policy $O/policy_trace.npz $OV \
    "viewer.camera_position=[0.55,-0.45,1.05]" "viewer.camera_target=[0.0,0.0,0.65]" ) > $O/trace.log 2>&1
( cd $FC && KIT=/content/kit/v2d_submission_kit python $REPO_DIR/tools/trace_score.py $REF $O/policy_trace.npz:replay ) > $O/score.txt 2>&1
log "vid_policy ep$EP: $(ls $O | tr '\n' ' '); $(tail -1 $O/score.txt)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
