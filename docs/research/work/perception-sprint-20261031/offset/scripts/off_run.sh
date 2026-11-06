#!/bin/bash
# offset experiment, INFERENCE side: pipeline/refine.py --steps S2 (baseline) vs S11,S2 (V1 mf/whole, V2 f0/whole,
# V3 f0/prefix) on the 20 public episodes, two input arms (README §0):
#   refineP  the 25 Oct tracks, refine/in/ep<N>/ (poses, hands, depth0, det_f0)
#   Po       the Phase-1 P_o tracks, T1's links $S/leak/t1/in_Po/ep<N>/ (poses, depth0, hands), with refine/in's det_f0
# Depth grid (mf): $S/offset/depth/ep<N>/depth_grid.npz (fetch_depth.py; our stereo depth, frame 0 = depth0.npy).
# Nothing here reads mocap; refine.assert_inference_input checks every input. Scoring: off_score.py (oracle side).
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/offset; R=$S/refine/in; PO=$S/leak/t1/in_Po
PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
EPS="${EPS:-0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45}"
VARS="${VARS:-S2 V1 V2 V3}"
mkdir -p $W/runs
{ sha256sum $REPO/pipeline/refine.py $REPO/pipeline/offsetfix.py; (cd $REPO && git rev-parse HEAD && git status --short pipeline/); } > $W/runs/code_sha256.txt
J=$W/runs/jobs.txt; : > $J
for arm in refineP Po; do
  for v in $VARS; do
    mkdir -p $W/runs/$arm/$v/logs
    case $v in
      S2) st="--steps S2";;
      V1) st="--steps S11,S2 --s11_mode mf --s11_apply whole";;
      V2) st="--steps S11,S2 --s11_mode f0 --s11_apply whole";;
      V3) st="--steps S11,S2 --s11_mode f0 --s11_apply prefix";;
    esac
    for e in $EPS; do
      inp=$R/ep$e; extra=""
      [ $arm = Po ] && inp=$PO/ep$e && extra="--s11_det $R/ep$e/det_f0.npz"
      [ $v = V1 ] && extra="$extra --s11_depth $W/depth/ep$e/depth_grid.npz"
      echo "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $PY -I $REPO/pipeline/refine.py --in $inp --out $W/runs/$arm/$v/ep$e $st $extra --force > $W/runs/$arm/$v/logs/ep$e.log 2>&1 || echo FAIL $arm $v ep$e" >> $J
    done
  done
done
# V1 jobs first (slowest), then the rest
(grep " V1/\|/V1/" $J; grep -v "/V1/" $J) > $J.ordered
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J.ordered
grep -l "Traceback" $W/runs/*/*/logs/*.log || echo "no tracebacks"
