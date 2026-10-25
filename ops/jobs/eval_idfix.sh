#!/bin/bash
# Eval episode with the board identity repair (pre-registered 2026-10-25 ~14:55 UTC in docs/work-log.md; rule R1 of
# docs/research/approaches-2026-10-25/approach1-motion-constrained-meshes.md §2.6, GT-free). The stored eval-25 track
# has the two boards' names swapped and one board turned 180 deg, so its reference and policies chase the wrong boards.
#   1. perception as in eval_both.sh (Grounding DINO on, today's defaults);
#   2. pipeline/identity_fix.py repairs poses.npz in place (knob darkness in the video; keeps *_as_tracked.npz);
#   3. ops/jobs/eval_both.sh on the same episode: pipeline_ep.sh finds poses.npz and skips perception, so the reference,
#      both learners and the GT-free choice use the repaired track.
# Usage: ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'EP=25 bash ops/jobs/eval_idfix.sh'
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; EP=${EP:?EP missing}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "eval_idfix code $(git -C $REPO_DIR rev-parse --short HEAD), episode $EP, LIB $LIB" >> $J
label "eval_idfix ep$EP: perception"
ensure_gdino $J
( SPLIT=eval PERC=perc2 STEPS=0 STOP_AFTER=perception bash $REPO_DIR/pipeline/pipeline_ep.sh $EP ) > /content/perc_ep$EP.log 2>&1 \
  || { log "eval_idfix ep$EP: perception FAILED ($(tail -3 /content/perc_ep$EP.log | tr '\n' ' ' | cut -c1-300))" >> $J; exit 1; }
python $REPO_DIR/pipeline/identity_fix.py /content/t3/eval/v/ep${EP}_c.mp4 /content/t3/calib.json /content/perc2/ep$EP \
  $LIB/wooden_piece_1.glb $LIB/wooden_piece_2.glb >> $J 2>&1 || { log "eval_idfix ep$EP: identity_fix FAILED" >> $J; exit 1; }
log "eval_idfix ep$EP: $(tr -d '\n ' < /content/perc2/ep$EP/identity_fix.json | cut -c1-300)" >> $J
EPS=$EP LIB=$LIB bash $REPO_DIR/ops/jobs/eval_both.sh
