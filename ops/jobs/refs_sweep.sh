#!/bin/bash
# Reference health sweep (2026-10-20 night): perception -> hands -> mkref on public episodes, no training, then
# pipeline/ref_report.py. Finds pipeline bugs (like box 1's floor-as-table) before paying for trainings. Two episode
# streams share the GPU. Depth caches go to the HF store for later boxes. Job: 'bash ops/jobs/refs_sweep.sh'.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log
A=${EPS_A:-"12 0 2 11 13 18 21 22 23 24"}
B=${EPS_B:-"27 26 31 39 40 41 42 43 44 45"}
stream() {
  for ep in $*; do
    label "refs sweep: ep$ep"
    PERC=perc2 STOP_AFTER=reference bash $P/pipeline_ep.sh $ep > /content/sweep_ep$ep.log 2>&1
    log "ep$ep rc=$? $(grep -aE 'FAILED|reference:' /content/sweep_ep$ep.log | tail -1 | cut -c1-160)" >> $J
    [ -s /content/perc2/ep$ep/depths_fs0.5.npy ] && (bash $OPS/store.sh push-depth $ep public > /dev/null 2>&1 &)
  done
}
stream $A &
sleep 60
stream $B &
wait
python $P/ref_report.py perc2 > /content/results/ref_report_perc2.txt 2>&1
cat /content/results/ref_report_perc2.txt >> $J
log "refs sweep done" >> $J
