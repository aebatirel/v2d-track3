#!/bin/bash
# Learning curve of one training run (2026-10-23): one official evaluation per saved checkpoint (policy_*.safetensors),
# scored against OUR reference (pipeline/qa.py sim_vs_ref, no ground truth) plus object lift / hold statistics
# (tools/ckpt_curve_summary.py). Runs PAR evaluations at a time; safe next to a training (GPU shared).
# Usage: bash ckpt_curve.sh <run_dir> <out_dir> <episode> [PAR=4] [EVERY=1]
RUN=$1; OUT=$2; EP=$3; PAR=${PAR:-4}; EVERY=${EVERY:-1}; FC=/content/v2d/robotic_grounding/flash_chord
S=${REPO_DIR:-/content/v2d-track3}/pipeline; E6=$(printf %06d $EP); mkdir -p $OUT; pids=(); i=0
for ck in $(ls -v $RUN/policy_*.safetensors); do
  i=$((i + 1)); [ $(( (i - 1) % EVERY )) -ne 0 ] && continue
  d=$OUT/$(basename $ck .safetensors); [ -s $d/qa_policy.json ] && continue; mkdir -p $d
  ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
      evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
      evaluation.metrics_output=$d/episode_$E6.json evaluation.object_trajectories_output=$d/episode_$E6.parquet \
      hydra.run.dir=$d/hydra logging.mode=disabled > $d/eval.log 2>&1 && python $S/qa.py policy $d $EP > /dev/null 2>&1 ) & pids+=($!)
  [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
echo "curve done: $(ls -d $OUT/policy_* | wc -l) checkpoints"
