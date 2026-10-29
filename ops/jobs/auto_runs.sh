#!/bin/bash
# Episodes through pipeline/auto_ep.sh (automatic QA + retries), route A (our meshes for tracking, simulator and
# scoring registration), CONCURRENT at a time. Written 2026-10-21. Public episodes are scored against mocap
# afterwards (evaluation only: score_sim.py and score_registered.py with our meshes); eval episodes are not scored.
#   ops/vast.sh create ... 'EPS="18 24" RETRIES=1 bash ops/jobs/auto_runs.sh'          (public validation)
#   ops/vast.sh create ... 'SPLIT=eval EPS="1 3" bash ops/jobs/auto_runs.sh'           (eval; RESUME_FROM optional)
#   FDR (default 1 since 2026-10-23, owner): FlashDexRetarget-style training rewards (ops/box/lib.sh fc_patches); FDR=0 stock
# A second job on a box that is already running one (2026-10-21: ep18 redone with library_v2 while ep24 trained):
# check the new commit out in its own worktree and give it its own assets, perception folder and variant, e.g.
#   git -C /content/v2d-track3 worktree add /content/v2d-2 <commit>
#   SELF_HOLD=1 J=/content/job2.log ASSETS=/content/assets2 PROOT=/content/perc2m/lib2 BV=n LIB=/content/v2d-2/meshes/library_v2 \
#     EPS=18 RETRIES=1 setsid nohup bash /content/v2d-2/ops/jobs/auto_runs.sh > /dev/null 2>&1 < /dev/null &
. /content/v2d-track3/ops/box/lib.sh
export REPO_DIR=$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)    # this script's checkout (lib.sh fixes the main one)
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; C=${CONCURRENT:-2}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} ASSETS=${ASSETS:-/content/assets} SPLIT=${SPLIT:-public} PERC=perc2
PROOT=${PROOT:-/content/perc2m}; BV=${BV:-m}
# trainings take turns on the GPU (pipeline_ep.sh TRAIN_LOCK): 2026-10-22 spoon box, two concurrent 250M trainings on one
# Max-Q ran 0.62M steps/min each (1.25M/min together) vs 1.8M/min for one alone; perception and evaluations still overlap
export TRAIN_LOCK=${TRAIN_LOCK:-/content/train.lock}
log "auto_runs code $(git -C $REPO_DIR rev-parse --short HEAD), meshes $MESH_DIR" >> $J
pip install -q fast_simplification >> $J 2>&1 || true            # kit budget_mesh (score_registered --meshes)
python $P/make_assets.py $MESH_DIR $ASSETS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
ensure_gdino $J                                                  # detection grounding term (pipeline/det_rules.py)
fc_patches $J || exit 1                                          # FDR=1 / FC_* opt-in patches (ops/box/lib.sh)
DONE=$ST/auto_done_$$
(while sleep 60; do
   [ -e $DONE ] && break
   if [ "${SELF_HOLD:-0}" = 1 ]; then
     # second job: run_job.sh does not wait for it, so keep the box held while it makes progress (a log or checkpoint
     # written in the last 30 min); when it stalls the hold lapses and the watchdog saves and destroys (CLAUDE.md)
     [ -n "$(find /content/auto_*.log /content/runs -type f -mmin -30 2>/dev/null | head -1)" ] \
       && echo $(( $(date +%s) + 1800 )) > /content/HOLD
   else                                               # keep a HOLD while the GPU works (box started by hand)
     u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
     [ "${u:-0}" -ge 10 ] && [ -e $ST/held_exit ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD
   fi
 done) &
label "auto ($SPLIT): $EPS"
one() {
  ep=$1
  bash $OPS/store.sh pull-depth $ep $SPLIT > /dev/null 2>&1           # eval caches exist once own_eval.sh pushed them
  PDIR=$PROOT/ep$ep BV=$BV RETRIES=${RETRIES:-2} bash $P/auto_ep.sh $ep > /content/auto_ep$ep$BV.log 2>&1
  log "auto ep$ep rc=$? $(tail -1 /content/auto_ep$ep$BV.log)" >> $J
  F=/content/results/final/ep$ep
  if [ $SPLIT = public ] && [ -s $F/episode_$(printf %06d $ep).parquet ]; then
    python $P/score_sim.py $ep $F > $F/score_sim.log 2>&1
    python $P/score_registered.py $ep $F --meshes $MESH_DIR > /dev/null 2>&1
    log "auto ep$ep scored vs mocap: $(python -c "
import json; a = json.load(open('$F/score_ep$ep.json'))['sim_vs_mocap']; b = json.load(open('$F/score_registered_ep$ep.json'))['sim']
print('old AUC', a['AUC'], 'registered (our meshes) AUC', b['AUC'], 'SP', b['SP_SR'], 'MP', b['MP_SR'])" 2>&1 | tail -1)" >> $J
  fi
}
pids=()
for ep in $EPS; do
  one $ep & pids+=($!)
  [ ${#pids[@]} -ge $C ] && { wait "${pids[@]}"; pids=(); }
  sleep 120                                             # stagger the JIT compiles
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
touch $DONE
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
if [ "${SELF_HOLD:-0}" = 1 ] && [ ! -e $ST/done ]; then
  rm -f /content/HOLD                                   # run_job.sh's own job still runs; it saves and destroys at its end
else
  pgrep -f '[p]ipeline_ep.sh' > /dev/null || { [ -e $ST/held_exit ] && rm -f /content/HOLD; }
fi
exit 0
