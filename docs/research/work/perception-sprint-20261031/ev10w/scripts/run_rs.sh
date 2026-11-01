#!/bin/bash
# rigid_shift.py over f100-160, stride 2 (PREREG allows every second frame), 3 processes. Usage: run_rs.sh CARVE_DIR TAG REF SUMMARY
W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w
FPY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve/fcvenv/bin/python
C=$1; TAG=$2; REF=$3; SUM=$4
for rg in 100:118:2 120:138:2 140:160:2; do t=${rg//:/_}
  ( cd $W && $FPY -I $W/scripts/rigid_shift.py $REF $C $W/prof/blue_cup_profile.npz $rg $W/out/rs_${TAG}_$t.json $SUM > $W/logs/rs_${TAG}_$t.log 2>&1 ) &
done; wait
