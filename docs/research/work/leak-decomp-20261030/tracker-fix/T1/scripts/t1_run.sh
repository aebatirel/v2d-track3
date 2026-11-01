#!/bin/bash
# T1 reference part, INFERENCE side (tracker-fix PLAN §3 T1): pipeline/refine.py --steps S2 vs --steps S6,S2 on the 20
# public episodes, two input arms:
#   refineP  the 25 Oct tracks (refine/in/ep<N>/: poses, hands, frame-0 depth), as in the refine study;
#   Po       the Phase-1 P_o tracks (our templates, library_v3), with refine/in's frame-0 depth and hands (same depth
#            cache, camera within 0.08 cm: phase1/RESULTS.md checks). Linked into $W/in_Po/ep<N>/.
# Nothing here reads mocap; refine.assert_inference_input checks every input. Scoring: t1_score.py (oracle side).
# Usage: t1_run.sh  -> $W/runs/<arm>/<variant>/ep<N>/, logs, $W/runs/refine_sha256.txt
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/leak/t1; R=$S/refine/in; P1=$S/leak/p1/runs
PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
declare -A RUN=([0]=a [2]=a [11]=b [12]=c [13]=a [18]=c [21]=b [22]=b [23]=b [24]=c [26]=a [27]=c [31]=b [39]=b [40]=c
                [41]=a [42]=b [43]=c [44]=a [45]=a)
for e in $EPS; do                                   # P_o input dirs (symlinks only)
  d=$W/in_Po/ep$e; mkdir -p $d
  src=$P1/20261030-orcP1${RUN[$e]}-87fc869/results/leak_p1/ep$e/perc2
  ln -sfn $src/poses.npz $d/poses.npz; ln -sfn $src/poses_world_vo.npz $d/poses_world_vo.npz
  ln -sfn $R/ep$e/depth0.npy $d/depth0.npy; ln -sfn $(readlink -f $R/ep$e/hands_refined.npz) $d/hands_refined.npz
done
mkdir -p $W/runs; sha256sum $REPO/pipeline/refine.py > $W/runs/refine_sha256.txt
(cd $REPO && git rev-parse HEAD && git status --short pipeline/refine.py) >> $W/runs/refine_sha256.txt
J=$W/runs/jobs.txt; : > $J
for arm in refineP Po; do
  for v in S2 S6S2; do
    mkdir -p $W/runs/$arm/$v/logs
    st=S2; [ $v = S6S2 ] && st=S6,S2
    for e in $EPS; do
      inp=$R/ep$e; [ $arm = Po ] && inp=$W/in_Po/ep$e
      echo "$PY -I $REPO/pipeline/refine.py --in $inp --out $W/runs/$arm/$v/ep$e --steps $st > $W/runs/$arm/$v/logs/ep$e.log 2>&1 || echo FAIL $arm $v ep$e" >> $J
    done
  done
done
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J
grep -l "Traceback" $W/runs/*/*/logs/*.log || echo "no tracebacks"
