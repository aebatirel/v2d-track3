#!/bin/bash
# SCORER SIDE. Score refine arms (lib = meshes/library_v3, scan = public scans) with pipeline/score_registered.py
# (through score_rot.py, which adds the per-frame symmetric rotation error for the flip gate).
# Usage: score_arms.sh "ARM1 ARM2 ..."  -> arms/<arm>/score/ep<N>_{lib,scan}.json, _pf.npz, _rot.npz, logs/
set -u
R=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine
W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring
REPO=/home/user/v2d-track3; LIB=$REPO/meshes/library_v3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
J=$R/arms/score_jobs_$(date +%H%M%S).txt; : > $J
for arm in $1; do
  A=$R/arms/$arm; mkdir -p $A/score/logs
  for e in $EPS; do
    B="$W/venv/bin/python -I $R/evalscripts/score_rot.py"
    C="$e $A/ep$e/poses_world_vo.npz --t3 $W/t3 --kit $W/kit/v2d_submission_kit"
    echo "$B $A/score/ep${e}_lib_rot.npz $C --meshes $LIB --out $A/score/ep${e}_lib.json --per_frame $A/score/ep${e}_lib_pf.npz > $A/score/logs/ep${e}_lib.log 2>&1 || echo FAIL $arm $e lib" >> $J
    echo "$B $A/score/ep${e}_scan_rot.npz $C --out $A/score/ep${e}_scan.json --per_frame $A/score/ep${e}_scan_pf.npz > $A/score/logs/ep${e}_scan.log 2>&1 || echo FAIL $arm $e scan" >> $J
  done
done
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J
echo "jobs: $J"
