#!/bin/bash
# Train, evaluate and score one public episode twice on one GPU: PERC=perc2 (our perception) and PERC=oracle
# (evaluation-only mocap objects), each through pipeline_ep.sh. Written 2026-10-20 for box 1's rerun after the
# support-plane fix; usable as a job (`ops/vast.sh create ... 'EP=12 bash ops/jobs/train_pair.sh'`) or started by
# hand on a box that already finished its job. On such a box (run_job.sh exited on HOLD) it refreshes a 30-min HOLD
# while the GPU is busy and removes it at the end, so the watchdog saves and destroys the box when the pair is done.
. /content/v2d-track3/ops/box/lib.sh
EP=${EP:-12}; P=$REPO_DIR/pipeline; J=/content/job.log
(while sleep 300; do
   [ -e $ST/pair_done ] && break
   u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
   [ "${u:-0}" -ge 10 ] && [ -e $ST/held_exit ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD
 done) &
label "pair ep$EP: perc2 + oracle"
log "pair ep$EP: start, commit $(git -C $REPO_DIR rev-parse --short HEAD)" >> $J
PERC=perc2  bash $P/pipeline_ep.sh $EP > /content/pipe_perc2_ep$EP.log 2>&1 &
sleep 120                                                              # stagger the JIT compiles
PERC=oracle bash $P/pipeline_ep.sh $EP > /content/pipe_oracle_ep$EP.log 2>&1 &
wait
for r in perc2 oracle; do
  log "pair ep$EP $r: $(grep -aE 'DONE|FAILED' /content/pipe_${r}_ep$EP.log | tail -1)" >> $J
done
touch $ST/pair_done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
[ -e $ST/held_exit ] && rm -f /content/HOLD                           # the watchdog now saves and destroys
exit 0
