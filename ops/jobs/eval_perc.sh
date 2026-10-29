#!/bin/bash
# Perception only on EVAL episodes (SPLIT=eval: eval videos, kit roster names, nothing scored), one after another
# (two perception jobs on one GPU can OOM). Written 2026-10-21. Per episode: /content/perc2/epN (poses.npz,
# poses_world_vo.npz, masks_f0.jpg, vo.json, log) and its depth cache pushed to the store (cache/depth/eval/epN), so
# reconstruction and QA overlays can run on CPU elsewhere. As a job:
#   ops/vast.sh create ... 'EPS="1 3 5" bash ops/jobs/eval_perc.sh'
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log
EPS=${EPS:-"1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"}
label "eval perception: $EPS"
for ep in $EPS; do
  SPLIT=eval PERC=perc2 STEPS=0 STOP_AFTER=perception bash $P/pipeline_ep.sh $ep > /content/perc_eval_ep$ep.log 2>&1
  rc=$?
  log "eval perception ep$ep rc=$rc $(tail -1 /content/perc_eval_ep$ep.log | cut -c1-120)" >> $J
  [ $rc = 0 ] && bash $OPS/store.sh push-depth $ep eval /content/perc2 > /dev/null 2>&1 \
    || log "eval ep$ep: depth not pushed" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true                 # outputs so far (a crash keeps them)
done
exit 0
