#!/bin/bash
# Run pipeline/refine.py (INFERENCE side; reads only refine/in/ep<N>/) for every arm x public episode.
# Usage: run_refine_arms.sh   -> refine/arms/<arm>/ep<N>/, refine/arms/<arm>/logs/ep<N>.refine.log, refine/arms/refine_jobs.txt
set -u
R=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine
PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
declare -A ARGS=( [none]="--steps none" [S1]="--steps S1" [S2]="--steps S2" [S2h0]="--steps S2 --s2_hold_f0 1"
                  [S3]="--steps S3" [S4]="--steps S4" [ALL]="--steps S1,S3,S4,S2" )
J=$R/arms/refine_jobs.txt; : > $J
for arm in none S1 S2 S2h0 S3 S4 ALL; do
  mkdir -p $R/arms/$arm/logs
  for e in $EPS; do
    echo "$PY -I $REPO/pipeline/refine.py --in $R/in/ep$e --out $R/arms/$arm/ep$e ${ARGS[$arm]} > $R/arms/$arm/logs/ep$e.refine.log 2>&1 || echo FAIL $arm ep$e" >> $J
  done
done
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J
