#!/bin/bash
# Early stopping for a FlashCHORD training run (2026-10-23; owner: "do we have to go through all 250M? can't we stop
# after we achieved enough"). Runs next to the training: every new checkpoint (policy_<steps>.safetensors) gets ES_N
# official evaluations scored against OUR reference (pipeline/qa.py sim_vs_ref; no ground truth), written to
# OUT/policy_<steps>/ (r1/, r2/, es.json with the mean; qa_policy.json = r1, so tools/ckpt_curve.sh skips it).
# The training is stopped (RUN/EARLY_STOPPED holds the reason) when
#   - two consecutive scored checkpoints have mean sim_vs_ref >= ES_TARGET (default 0.9), or
#   - no new best for ES_PATIENCE steps (default 50M),
# counting only checkpoints from ES_MIN steps on (default 30M; earlier ones still trained with object assist).
# Single evaluations scatter by 0.05-0.1 (2026-10-23), hence ES_N >= 2 and two in a row.
# Usage: early_stop.sh RUN OUT EP TRAIN_PID    (env J = job log; ES_EVAL = evaluation command, for tests)
RUN=$1; OUT=$2; EP=$3; TP=$4; J=${J:-/dev/stderr}
ES_TARGET=${ES_TARGET:-0.9}; ES_PATIENCE=${ES_PATIENCE:-50000000}; ES_MIN=${ES_MIN:-30000000}; ES_N=${ES_N:-2}
FC=/content/v2d/robotic_grounding/flash_chord; S=${REPO_DIR:-/content/v2d-track3}/pipeline; E6=$(printf %06d $EP)
mkdir -p $OUT
eval_one() {  # $1 checkpoint, $2 dir: one official evaluation, prints sim_vs_ref
  mkdir -p $2
  ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
      evaluation.checkpoint=$1 evaluation.world_count=1 evaluation.reset_mode=explicit \
      evaluation.metrics_output=$2/episode_$E6.json evaluation.object_trajectories_output=$2/episode_$E6.parquet \
      hydra.run.dir=$2/hydra logging.mode=disabled > $2/eval.log 2>&1 ) && python $S/qa.py policy $2 $EP > /dev/null 2>&1
  python -c "import json; print(json.load(open('$2/qa_policy.json'))['sim_vs_ref'])" 2> /dev/null
}
ES_EVAL=${ES_EVAL:-eval_one}
seen=" "; best=-1; best_step=0; prev=-1
while kill -0 $TP 2> /dev/null; do
  for ck in $(ls -v $RUN/policy_*.safetensors 2> /dev/null); do
    case "$seen" in *" $ck "*) continue;; esac
    s0=$(stat -c %s $ck); sleep 5; [ "$(stat -c %s $ck)" = "$s0" ] || continue      # still being written
    seen="$seen$ck "; step=$(basename $ck .safetensors); step=${step#policy_}
    [ "$step" -lt "$ES_MIN" ] && continue
    d=$OUT/$(basename $ck .safetensors); scores=()
    for i in $(seq 1 $ES_N); do scores+=($($ES_EVAL $ck $d/r$i)); done
    [ -s $d/r1/qa_policy.json ] && cp $d/r1/qa_policy.json $d/qa_policy.json
    m=$(python -c "import sys; v=[float(x) for x in sys.argv[1:]]; print(round(sum(v)/len(v), 4) if v else -1)" "${scores[@]}")
    echo "{\"step\": $step, \"mean\": $m, \"runs\": [$(IFS=,; echo "${scores[*]}")]}" > $d/es.json
    if python -c "import sys; sys.exit(0 if $m > $best else 1)"; then best=$m; best_step=$step; fi
    msg="early stop ep$EP: $(basename $ck) sim_vs_ref mean $m [${scores[*]}] (best $best at $best_step)"
    reason=""
    python -c "import sys; sys.exit(0 if $prev >= $ES_TARGET and $m >= $ES_TARGET else 1)" && reason="two in a row >= $ES_TARGET"
    [ -z "$reason" ] && [ $((step - best_step)) -ge $ES_PATIENCE ] && reason="no new best for $((step - best_step)) steps"
    prev=$m
    if [ -n "$reason" ]; then
      echo "$reason at $step" > $RUN/EARLY_STOPPED; log "$msg -> STOP ($reason)" >> $J 2> /dev/null || echo "$msg -> STOP ($reason)" >> $J
      pkill -f "[o]utput_dir=$RUN " ; pkill -f "[o]utput_dir=$RUN\$"; exit 0
    fi
    log "$msg" >> $J 2> /dev/null || echo "$msg" >> $J
  done
  sleep 20
done
