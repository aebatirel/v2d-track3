#!/bin/bash
# verify_timing: score stored rollouts' simulated paths (exported by vt_sim.py) with the OFFICIAL scorer, one at a time.
# Usage: bash run_sim.sh JOBFILE   (lines: EP ROLLOUT_PARQUET VARIANT LIB TAG)
SP=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
W=$SP/work/verify_timing/sim; mkdir -p $W
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_timing
source $SP/venv/bin/activate
while read EP F VAR LIB TAG; do
  [ -z "$EP" ] && continue
  OUT=$W/ep${EP}_${TAG}
  [ -f $OUT.json ] && continue
  python -I $D/vt_sim.py $F $EP $VAR $OUT.npz > /dev/null
  python -I /home/user/v2d-track3/pipeline/score_registered.py $EP $OUT.npz --meshes /home/user/v2d-track3/meshes/$LIB \
     --t3 $SP/t3 --kit $SP/kit/v2d_submission_kit --out $OUT.json > $OUT.log 2>&1
  echo "$(date -u +%H:%M:%S) ep$EP $TAG $VAR rc=$? AUC=$(python -I -c "import json;d=json.load(open('$OUT.json'));print(d['perception']['AUC'], d['perception']['per_obj_AUC'])" 2>/dev/null)"
done < $1
