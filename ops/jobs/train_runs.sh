#!/bin/bash
# Run several pipeline_ep.sh trainings on one box, CONCURRENT at a time (default 2 per GPU), each a spec
# "EP:PERC[:VARIANT[:PDIR[:HANDS_ARGS]]]" in RUNS, e.g. RUNS="12:perc2:v 27:perc2". Written 2026-10-20 night.
# As a job: ops/vast.sh create ... 'RUNS="12:perc2:v 27:perc2" bash ops/jobs/train_runs.sh'. Started by hand on a box
# whose job already ended (run_job.sh exited on HOLD), it refreshes a 30-min HOLD while the GPU is busy and removes
# it at the end, so the watchdog saves and destroys the box.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log; C=${CONCURRENT:-2}
DONE=$ST/runs_done_$$                                                  # one marker per invocation (several may run)
(while sleep 60; do
   [ -e $DONE ] && break
   u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
   [ "${u:-0}" -ge 10 ] && [ -e $ST/held_exit ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD
 done) &
[ -e $ST/held_exit ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD     # before the first refresh (no race)
one() {
  IFS=: read -r ep perc var pdir hargs <<< "$1"
  local tag=${perc}${var}_ep$ep targs=""
  # a variant containing "w" trains the mid-stiffness wrist (flashchord_conf/embodiment/sharpa_hands_mid.yaml)
  case $var in *w*) targs="hydra.searchpath=[file://$REPO_DIR/flashchord_conf] embodiment=sharpa_hands_mid" ;; esac
  # a variant containing "c" raises the E2S wrist IK cost to 3.0 (mkref --wrist_cost; removes the wrist jumps)
  local margs=""; case $var in *c*) margs="--wrist_cost 3.0" ;; esac
  log "run $tag: start, commit $(git -C $REPO_DIR rev-parse --short HEAD) ${targs:+($targs)} ${margs:+($margs)}" >> $J
  VARIANT=$var PDIR=$pdir HANDS_ARGS=$hargs TRAIN_ARGS=$targs MKREF_ARGS=$margs PERC=$perc bash $P/pipeline_ep.sh $ep \
    > /content/pipe_$tag.log 2>&1
  log "run $tag: rc=$? $(grep -aE 'DONE|FAILED' /content/pipe_$tag.log | tail -1)" >> $J
}
label "train runs: $RUNS"
n=0
for spec in $RUNS; do
  one "$spec" &
  n=$((n + 1)); [ $((n % C)) -eq 0 ] && wait
  sleep 120                                                             # stagger the JIT compiles
done
wait
touch $DONE
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
# release the hold only if no other pipeline still runs on this box
pgrep -f '[p]ipeline_ep.sh' > /dev/null || { [ -e $ST/held_exit ] && rm -f /content/HOLD; }
exit 0
