#!/bin/bash
# V4 (verify_systematics): score every npz written by v4_make_npz.py with pipeline/score_registered.py, one at a time.
# Usage: bash v4_score.sh NPZDIR OUTDIR
RC=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
source $RC/venv/bin/activate
NPZ=$1; OUT=$2; mkdir -p $OUT
lib() { case $1 in 21|39) echo library_v3;; 26) echo library_v4;; *) echo library_v2;; esac; }
for f in $(ls $NPZ/*.npz | sort); do
  b=$(basename $f .npz); ep=${b%%_*}; ep=${ep#ep}
  [ -s $OUT/$b.json ] && continue
  t0=$(date +%s)
  python -I /home/user/v2d-track3/pipeline/score_registered.py $ep $f --meshes /home/user/v2d-track3/meshes/$(lib $ep) \
     --t3 $RC/t3 --kit $RC/kit/v2d_submission_kit --out $OUT/$b.json > /dev/null 2>$OUT/$b.err
  echo "$b $(lib $ep) $(python -c "import json;d=json.load(open('$OUT/$b.json'));print(d['perception']['AUC'], d['perception']['per_obj_AUC'])" 2>/dev/null) $(( $(date +%s) - t0 ))s"
done
