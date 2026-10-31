#!/bin/bash
# Learning curve of one training run (2026-10-23): one official evaluation per saved checkpoint (policy_*.safetensors),
# scored against OUR reference (pipeline/qa.py sim_vs_ref, no ground truth) plus object lift / hold statistics
# (tools/ckpt_curve_summary.py). Runs PAR evaluations at a time; safe next to a training (GPU shared).
# REP=n (2026-10-24): n official evaluations per checkpoint (in <ckpt>/r1..rn); qa_policy.json then holds their MEAN
# sim_vs_ref (rep list kept) and r1's rollout files are copied up for the summary. One evaluation is too noisy to choose
# a checkpoint (public ep21: 0.831 in the curve, 0.27 mean of 5 repeats).
# Usage: bash ckpt_curve.sh <run_dir> <out_dir> <episode> [PAR=4] [EVERY=1] [REP=1]
# EVAL_TIMEOUT=<s> (2026-10-31, opt-in): cut an evaluation that runs longer (that checkpoint/repeat is then unscored);
# timeout -k 60 (one that ignores SIGTERM is killed 60 s later); each evaluation folder gets eval_rc.txt (exit code:
# 124 cut, 137 killed after the grace) so the cuts can be counted (tools/mass_verify.py).
RUN=$1; OUT=$2; EP=$3; PAR=${PAR:-4}; EVERY=${EVERY:-1}; REP=${REP:-1}; FC=/content/v2d/robotic_grounding/flash_chord
S=${REPO_DIR:-/content/v2d-track3}/pipeline; E6=$(printf %06d $EP); mkdir -p $OUT; pids=(); i=0
for ck in $(ls -v $RUN/policy_*.safetensors); do
  i=$((i + 1)); [ $(( (i - 1) % EVERY )) -ne 0 ] && continue
  d=$OUT/$(basename $ck .safetensors); [ -s $d/qa_policy.json ] && continue; mkdir -p $d
  for r in $(seq 1 $REP); do
    e=$d; [ $REP -gt 1 ] && e=$d/r$r; mkdir -p $e
    ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false ${EVAL_TIMEOUT:+timeout -k 60 $EVAL_TIMEOUT} .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$e/episode_$E6.json evaluation.object_trajectories_output=$e/episode_$E6.parquet \
        hydra.run.dir=$e/hydra logging.mode=disabled > $e/eval.log 2>&1
      rc_=$?; [ -n "${EVAL_TIMEOUT:-}" ] && echo $rc_ > $e/eval_rc.txt
      [ $rc_ = 0 ] && python $S/qa.py policy $e $EP > /dev/null 2>&1 ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
if [ $REP -gt 1 ]; then                                             # the mean over the repeats -> <ckpt>/qa_policy.json
  for d in $OUT/policy_*/; do
    { [ -d $d/r1 ] && [ ! -s $d/qa_policy.json ]; } || continue
    cp $d/r1/episode_$E6.* $d/ 2> /dev/null
    python -c "
import glob, json, sys
d = sys.argv[1]; rows = [json.load(open(f)) for f in sorted(glob.glob(d + '/r*/qa_policy.json'))]
if rows:
    out = dict(rows[0]); v = [r['sim_vs_ref'] for r in rows]
    out.update(sim_vs_ref=round(sum(v) / len(v), 4), rep=v, rep_n=len(v)); json.dump(out, open(d + '/qa_policy.json', 'w'), indent=1)
" $d
  done
fi
echo "curve done: $(ls -d $OUT/policy_* | wc -l) checkpoints"
