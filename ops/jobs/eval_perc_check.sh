#!/bin/bash
# Perception-only rerun of eval episodes with today's perception defaults (2026-10-25: on-table rule, gated
# re-proposal, TRACK_GUARD), to see which eval references a validated perception change actually alters before any
# training is spent. No ground truth exists for eval episodes; nothing is scored. Per episode: perc2 (SPLIT=eval,
# tracking seeds LIB) into /content/results/evalperc/ep<N>/ (poses.npz, log.txt, masks_f0.jpg, det_f0.npz,
# track_guard.json); the summary lists the frame-0 choice and the guard's interventions per object.
#   ops/vast.sh create <offer> <run> 'EPS="1 3 5 ..." bash ops/jobs/eval_perc_check.sh'     [LIB=..., extra perc2 env]
# (A separate file: ops/jobs/eval_perc.sh is the 21 Oct job that runs the full pipeline_ep.sh perception stage.)
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/evalperc; mkdir -p $O
EPS=${EPS:-"1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "eval_perc code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], LIB $LIB" >> $J
ensure_gdino $J
for ep in $EPS; do
  D=$O/ep$ep; mkdir -p $D
  bash $OPS/store.sh pull-depth $ep eval > /dev/null 2>&1 || log "eval_perc ep$ep: no cached depth (computed here)" >> $J
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] && ln -sf /content/cache/depth/ep$ep/depths_fs0.5.npy $D/
  label "eval_perc ep$ep"
  KF_MIN=120 EP=$ep OUT=$D SPLIT=eval MESH_DIR=$LIB python $P/perc2.py > $D/log.txt 2>&1
  log "eval_perc ep$ep rc=$?: $(grep -a 'assignment' $D/log.txt | cut -c1-160) guard $(tr -d '\n ' < $D/track_guard.json 2>/dev/null | cut -c1-300)" >> $J
  rm -f $D/depths_fs0.5.npy
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
done
log "eval_perc done" >> $J
