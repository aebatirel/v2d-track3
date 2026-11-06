#!/bin/bash
# C2/P reported-only rest check (PREREG section 8): rest_check.py for every built candidate and library_v3 at the
# pitcher's observed resting poses on ep21 and ep22 (our sweep track, our depth's frame-0 table plane). GT-free.
# Usage: rest_all.sh
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
HERE=$R/docs/research/mesh-2026-10-26/cdo-sprint/C2/P-pitcher/scripts
W=$S/cdo_c2/P
specs=(library_v3=$R/meshes/library_v3/water_pitcher.glb)
for f in $W/cand/*.glb; do b=$(basename $f .glb); specs+=(${b%_water_pitcher_*}_${b##*_}=$f); done
for e in 21 22; do
  nice -n 5 $S/venv/bin/python -I $HERE/rest_check.py $W/diag/rest_ep$e.json $S/data/sweep/ep$e/poses.npz \
    $W/diag/table_ep$e.json water_pitcher "${specs[@]}" > $W/logs/rest_ep$e.log 2>&1 || echo "FAIL rest ep$e"
  grep -E "STANDS|UNSTABLE|NO RESTING" $W/logs/rest_ep$e.log | cut -c1-140
done
