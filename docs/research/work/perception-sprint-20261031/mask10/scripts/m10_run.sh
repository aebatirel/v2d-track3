#!/bin/bash
# mask10, INFERENCE side (GT-free): refine S12 variants on the 20 public episodes, two arms (Po = Phase-1 P_o tracks,
# refineP = 25 Oct tracks; inputs as T1: $S/leak/t1/in_Po/ep<N>, $S/refine/in/ep<N>). Nothing here reads mocap;
# refine.assert_inference_input / nest_physics check every input. Scoring: m10_score.py (oracle side, after this).
# Variants (README §0): S2 (baseline), V1, V1h, V2 on every episode; V1d (ep11 only: the only depth grid with a window);
# V3 (S12 -> nest_physics inner -> S2) and V3p (S12 detection -> nest_physics both on the raw track -> S2) on every episode.
# Usage: m10_run.sh  -> $W/runs/<arm>/<variant>/ep<N>/, logs, $W/runs/code_sha256.txt
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/mask10; PY=$S/map/scoring/venv/bin/python; FPY=$S/carve/fcvenv/bin/python; REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
PCS=$REPO/meshes/carve/ev10
GRID=$S/offset/depth/ep11/depth_grid.npz
mkdir -p $W/runs
sha256sum $REPO/pipeline/refine.py $REPO/pipeline/nest.py $REPO/pipeline/offsetfix.py $REPO/tools/nest_physics.py > $W/runs/code_sha256.txt
(cd $REPO && git rev-parse HEAD && git status --short pipeline tools) >> $W/runs/code_sha256.txt
J=$W/runs/jobs.txt; : > $J
RF="$PY -I $REPO/pipeline/refine.py"
for arm in Po refineP; do
  for v in S2 V1 V1h V2 V1d pre preraw V3 V3p; do mkdir -p $W/runs/$arm/$v/logs; done
  for e in $EPS; do
    inp=$S/refine/in/ep$e; [ $arm = Po ] && inp=$S/leak/t1/in_Po/ep$e
    o=$W/runs/$arm; L=logs/ep$e.log; H=$(readlink -f $inp/hands_refined.npz)
    c="$RF --in $inp --out $o/S2/ep$e --steps S2 > $o/S2/$L 2>&1"
    c="$c; $RF --in $inp --out $o/V1/ep$e --steps S12,S2 > $o/V1/$L 2>&1"
    c="$c; $RF --in $inp --out $o/V1h/ep$e --steps S12,S2 --s12_mode height > $o/V1h/$L 2>&1"
    c="$c; $RF --in $inp --out $o/V2/ep$e --steps S12,S2 --s12_inner floor --s12_pieces $PCS > $o/V2/$L 2>&1"
    [ $e = 11 ] && c="$c; $RF --in $inp --out $o/V1d/ep$e --steps S12,S2 --s12_depth $GRID > $o/V1d/$L 2>&1"
    # V3: S12 hold (no S2) -> physics settle of the inner -> S2
    c="$c; $RF --in $inp --out $o/pre/ep$e --steps S12 > $o/pre/$L 2>&1"
    c="$c; $FPY -I $REPO/tools/nest_physics.py --in $o/pre/ep$e --popt $o/pre/ep$e/pose_opt.json --pieces $PCS --hands $H --mode inner --out $o/pre/ep${e}_phys >> $o/pre/$L 2>&1"
    c="$c; $RF --in $o/pre/ep${e}_phys --out $o/V3/ep$e --steps S2 --hands $H --depth $(readlink -f $inp/depth0.npy) > $o/V3/$L 2>&1"
    # V3p: physics only (both cups free) on the raw track, on S12's detected windows (pre/pose_opt.json)
    c="$c; $FPY -I $REPO/tools/nest_physics.py --in $inp --popt $o/pre/ep$e/pose_opt.json --pieces $PCS --hands $H --mode both --out $o/preraw/ep${e}_phys > $o/preraw/$L 2>&1"
    c="$c; $RF --in $o/preraw/ep${e}_phys --out $o/V3p/ep$e --steps S2 --hands $H --depth $(readlink -f $inp/depth0.npy) > $o/V3p/$L 2>&1"
    echo "$c || echo FAIL $arm ep$e" >> $J
  done
done
cd /tmp && xargs -P 3 -I{} bash -c '{}' < $J
grep -l "Traceback" $W/runs/*/*/logs/*.log || echo "no tracebacks"
