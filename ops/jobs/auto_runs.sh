#!/bin/bash
# Episodes through pipeline/auto_ep.sh (automatic QA + retries), route A (our meshes for tracking, simulator and
# scoring registration), CONCURRENT at a time. Written 2026-10-21. Public episodes are scored against mocap
# afterwards (evaluation only: score_sim.py and score_registered.py with our meshes); eval episodes are not scored.
#   ops/vast.sh create ... 'EPS="18 24" RETRIES=1 bash ops/jobs/auto_runs.sh'          (public validation)
#   ops/vast.sh create ... 'SPLIT=eval EPS="1 3" bash ops/jobs/auto_runs.sh'           (eval; RESUME_FROM optional)
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log; C=${CONCURRENT:-2}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v1} ASSETS=/content/assets SPLIT=${SPLIT:-public} PERC=perc2
pip install -q fast_simplification >> $J 2>&1 || true            # kit budget_mesh (score_registered --meshes)
python $P/make_assets.py $MESH_DIR $ASSETS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
DONE=$ST/auto_done_$$
(while sleep 60; do                                   # keep a HOLD while the GPU works (box started by hand)
   [ -e $DONE ] && break
   u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | sort -n | tail -1)
   [ "${u:-0}" -ge 10 ] && [ -e $ST/held_exit ] && echo $(( $(date +%s) + 1800 )) > /content/HOLD
 done) &
label "auto ($SPLIT): $EPS"
one() {
  ep=$1
  [ $SPLIT = public ] && bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1
  PDIR=/content/perc2m/ep$ep BV=m RETRIES=${RETRIES:-2} bash $P/auto_ep.sh $ep > /content/auto_ep$ep.log 2>&1
  log "auto ep$ep rc=$? $(tail -1 /content/auto_ep$ep.log)" >> $J
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
pgrep -f '[p]ipeline_ep.sh' > /dev/null || { [ -e $ST/held_exit ] && rm -f /content/HOLD; }
exit 0
