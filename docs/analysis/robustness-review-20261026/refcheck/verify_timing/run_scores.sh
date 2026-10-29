#!/bin/bash
# verify_timing: make variants with vt_shift.py and score each with the OFFICIAL pipeline/score_registered.py,
# strictly one scorer process at a time. Usage: bash run_scores.sh JOBFILE   (lines: EP SRC VARIANT LIB TAG)
SP=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
W=$SP/work/verify_timing/scores; mkdir -p $W
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_timing
source $SP/venv/bin/activate
while read EP SRC VAR LIB TAG; do
  [ -z "$EP" ] && continue
  OUT=$W/ep${EP}_${SRC}_${TAG}
  [ -f $OUT.json ] && { echo "skip $OUT"; continue; }
  python -I $D/vt_shift.py $EP $SRC $VAR $OUT.npz
  t0=$(date +%s)
  python -I /home/user/v2d-track3/pipeline/score_registered.py $EP $OUT.npz --meshes /home/user/v2d-track3/meshes/$LIB \
     --t3 $SP/t3 --kit $SP/kit/v2d_submission_kit --out $OUT.json --per_frame $OUT.pf.npz > $OUT.log 2>&1
  rc=$?
  echo "$(date -u +%H:%M:%S) ep$EP $SRC $VAR $LIB rc=$rc $(( $(date +%s)-t0 ))s AUC=$(python -I -c "import json;d=json.load(open('$OUT.json'));print(d['perception']['AUC'], d['perception']['per_obj_AUC'])" 2>/dev/null)"
done < $1
