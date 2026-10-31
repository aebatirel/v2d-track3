#!/bin/bash
# heldpose INFERENCE side (README §0): pipeline/refine.py --steps S2 (baseline) and S2,S10 in three modes on the 20 public
# episodes, two input arms (as T1): refineP = 25 Oct tracks (refine/in), Po = Phase-1 P_o tracks linked by T1 in
# $S/leak/t1/in_Po (poses + refine/in's hands and frame-0 depth). Nothing here reads mocap; refine.assert_inference_input
# checks every input. Scoring: hp_score.py (oracle side), run only after this script.
# Usage: hp_run.sh  -> $W/runs/<arm>/<variant>/ep<N>/ (+ logs), $W/runs/code_version.txt, $W/runs/jobs.txt
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/heldpose; R=$S/refine/in; PO=$S/leak/t1/in_Po
PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
mkdir -p $W/runs
{ sha256sum $REPO/pipeline/refine.py $REPO/pipeline/heldpose.py; (cd $REPO && git rev-parse HEAD && git status --short pipeline/); } > $W/runs/code_version.txt
J=$W/runs/jobs.txt; : > $J
for arm in refineP Po; do
  for v in S2 S10g S10r S10t; do
    mkdir -p $W/runs/$arm/$v/logs
    case $v in S2) st="--steps S2";; S10g) st="--steps S2,S10 --s10_mode gate";; S10r) st="--steps S2,S10 --s10_mode replace";;
               S10t) st="--steps S2,S10 --s10_mode trans";; esac
    for e in $EPS; do
      inp=$R/ep$e; [ $arm = Po ] && inp=$PO/ep$e
      echo "$PY -I $REPO/pipeline/refine.py --in $inp --out $W/runs/$arm/$v/ep$e $st --force > $W/runs/$arm/$v/logs/ep$e.log 2>&1 || echo FAIL $arm $v ep$e" >> $J
    done
  done
done
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J
grep -l "Traceback" $W/runs/*/*/logs/*.log || echo "no tracebacks"
