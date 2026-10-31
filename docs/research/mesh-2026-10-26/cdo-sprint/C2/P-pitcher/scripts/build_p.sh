#!/bin/bash
# C2/P candidate builds (PREREG.md section 3). GT-free: our C0b observed points only.
# Steps:
#   1. merged points (ep21 + ep22 pass-B files concatenated: c0b_prep.py merge, as C0b's merged blue cup);
#   2. sigma (gmg A.2 via c0b_prep.py sigma) per episode file; merged sigma = median of the two;
#      thickness rows (gmg thickness.py via c0b_prep.py thick) per episode file;
#   3. params_p.py: app_d = 3 sigma; t_fallback = thickness chain (C0b PREREG 3.3 steps 2-4);
#   4. lathe_obs.py with the C0b lathe arguments (--tie 1.0 --floor base_t --t_fallback T --tmax 0.008 --tmin 0.0015
#      --app_d 3 sigma), variants g1 (appendages 1) and g0 (--appendages 0), per source ep21, ep22, merged.
# Usage: build_p.sh [prep|build|all]
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
MR=$R/docs/research/mesh-2026-10-26
PREP=$MR/cdo-sprint/C0b/jobs/c0b_prep.py
HERE=$MR/cdo-sprint/C2/P-pitcher/scripts
W=$S/cdo_c2/P
PY="$S/venv/bin/python -I -W ignore"
SLOT=blue_cup,water_pitcher
mkdir -p $W/sigma $W/thick $W/cand $W/logs/build $W/pts/M
what=${1:-all}
if [ "$what" = prep ] || [ "$what" = all ]; then
  $PY $PREP merge $W/pts/M/merged_water_pitcher.npz $W/pts/B/ep21_water_pitcher.npz $W/pts/B/ep22_water_pitcher.npz \
    > $W/logs/build/merge.log 2>&1 || echo "FAIL merge"
  for e in 21 22; do
    f=$W/pts/B/ep${e}_water_pitcher.npz
    nice -n 5 $PY $PREP sigma $f $S/data/sweep/ep$e/poses.npz water_pitcher $SLOT $W/sigma/ep${e}_water_pitcher.json \
      > $W/logs/build/sigma_ep$e.log 2>&1 || echo "FAIL sigma ep$e" &
    nice -n 5 $PY $PREP thick $f $W/thick/ep${e}_water_pitcher.json > $W/logs/build/thick_ep$e.log 2>&1 || echo "FAIL thick ep$e" &
  done
  wait
  $PY $HERE/params_p.py $W > $W/logs/build/params.log 2>&1 || echo "FAIL params"
  cat $W/logs/build/params.log
fi
if [ "$what" = build ] || [ "$what" = all ]; then
  for src in ep21 ep22 merged; do
    args=$($S/venv/bin/python -I -c "import json; d=json.load(open('$W/params_p.json'))['targets']['$src']; print(' '.join(d['lathe_args']), d['obs'])")
    set -- $args
    obs=${@: -1}; largs=("${@:1:$#-1}")
    for v in g1 g0; do
      extra=(); [ $v = g0 ] && extra=(--appendages 0)
      ( t=$(date +%s); nice -n 5 $PY $MR/scripts/lathe_obs.py $obs $W/cand/${src}_water_pitcher_$v.glb "${largs[@]}" "${extra[@]}" \
          > $W/logs/build/${src}_$v.log 2>&1 && echo "OK $src $v $(( $(date +%s) - t ))s" || echo "FAIL $src $v (see logs/build/${src}_$v.log)" ) &
    done
  done
  wait
fi
