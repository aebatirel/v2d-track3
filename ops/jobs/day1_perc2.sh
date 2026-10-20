#!/bin/bash
# Box 1 follow-up (2026-10-20): the perc2 ep12 training of day1.sh failed on the pinocchio bug before the fix reached
# the box, while the oracle training started after it and runs. This starts the perc2 pipeline next to it (two jobs
# on one GPU) and doubles as the resume test: kill once a checkpoint >= 10M steps exists, rerun, expect a resume.
# Started by hand through `ops/vast.sh exec` under nohup. Log lines go to /content/job.log.
. /content/v2d-track3/ops/box/lib.sh
EP=${EP:-12}; P=$REPO_DIR/pipeline; RUN=/content/runs/perc2/ep$EP-s42; J=/content/job.log
step() { ls -v $RUN/state_*.safetensors 2> /dev/null | tail -1 | grep -oE '[0-9]+' | tail -1; }
# day1.sh may end first and run_job.sh would then self-destroy: hold the box in 30-min slices while the GPU is busy
# (a hung job stops refreshing the hold, so the watchdog still cleans up).
(while sleep 300; do
   [ -e $ST/perc2_done ] && break
   u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
   [ "${u:-0}" -ge 10 ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD
 done) &
echo $(( $(date +%s) + 1800 )) > /content/HOLD

log "perc2 ep$EP: start (resume test at >= 10M steps)" >> $J
PERC=perc2 bash $P/pipeline_ep.sh $EP > /content/pipe_perc2_ep$EP.log 2>&1 &
A=$!
for i in $(seq 1 360); do                          # up to 60 min (JIT compiles share the GPU with the oracle run)
  [ "$(step || echo 0)" -ge 10000000 ] 2> /dev/null && break
  kill -0 $A 2> /dev/null || break
  sleep 10
done
if [ "$(step || echo 0)" -ge 10000000 ] 2> /dev/null; then
  pkill -f "output_dir=$RUN" && log "resume test: killed perc2 training after checkpoint $(step)" >> $J
  wait $A; sleep 5
  PERC=perc2 bash $P/pipeline_ep.sh $EP > /content/pipe_perc2_ep${EP}_b.log 2>&1
  grep -aq "resuming from" /content/pipe_perc2_ep${EP}_b.log && log "RESUME-OK: $(grep -a 'resuming from' /content/pipe_perc2_ep${EP}_b.log)" >> $J \
    || log "RESUME-FAIL (see pipe_perc2_ep${EP}_b.log, $RUN/train.log)" >> $J
else
  wait $A
  log "RESUME-TEST-SKIPPED: no 10M checkpoint (see pipe_perc2_ep$EP.log)" >> $J
fi
log "perc2 ep$EP: $(tail -3 /content/pipe_perc2_ep${EP}_b.log /content/pipe_perc2_ep$EP.log 2> /dev/null | tr '\n' ' ' | cut -c1-400)" >> $J
touch $ST/perc2_done; rm -f /content/HOLD
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
