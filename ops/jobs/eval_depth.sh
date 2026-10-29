#!/bin/bash
# Eval depth cache for the mesh work (2026-10-29, owner go-ahead "batch 1"): the eval_perc_check.sh perception rerun
# (SPLIT=eval, tracking seeds LIB, today's perception defaults; no ground truth exists for eval, nothing is scored),
# plus one step it lacked: each episode's FoundationStereo depth is pushed to the store (cache/depth/eval/ep<N>/
# depths_fs0.5.npy) before the local copy is deleted, so obs_points.py / autokit can build per-eval-episode meshes on
# CPU (owner decision 22 Oct: each eval mesh is rebuilt from that episode's own video). Tracks, masks and det dumps go
# to /content/results/evalperc/ep<N>/ as in eval_perc_check.sh.
#   ops/vast.sh create <offer> <run> 'EPS="1 3 5 ..." bash ops/jobs/eval_depth.sh'     [LIB=..., extra perc2 env]
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/evalperc; mkdir -p $O
EPS=${EPS:-"1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "eval_depth code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], LIB $LIB" >> $J
ensure_gdino $J
for ep in $EPS; do
  D=$O/ep$ep; mkdir -p $D
  bash $OPS/store.sh pull-depth $ep eval > /dev/null 2>&1 || log "eval_depth ep$ep: no cached depth (computed here)" >> $J
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] && ln -sf /content/cache/depth/ep$ep/depths_fs0.5.npy $D/
  label "eval_depth ep$ep"
  KF_MIN=120 EP=$ep OUT=$D SPLIT=eval MESH_DIR=$LIB python $P/perc2.py > $D/log.txt 2>&1
  rc=$?
  log "eval_depth ep$ep rc=$rc: $(grep -a 'assignment' $D/log.txt | cut -c1-160)" >> $J
  if [ -s $D/depths_fs0.5.npy ]; then
    bash $OPS/store.sh push-depth $ep eval $O > /dev/null 2>&1 && log "eval_depth ep$ep: depth pushed" >> $J \
      || log "eval_depth ep$ep: depth NOT pushed" >> $J
  else
    log "eval_depth ep$ep: no depth file" >> $J
  fi
  rm -f $D/depths_fs0.5.npy
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
done
log "eval_depth done" >> $J
