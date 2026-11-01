#!/bin/bash
# heldpose, EVAL side, GT-free estimate only (README §0 "Reported"): refine --steps S2 and S2,S10 (modes g / r / t) on
# the stored eval perception behind packs 6/7 (sources as tracker-fix/screen/scripts/eval_screen.py: poses.npz from the
# depth-audit pulls, hands_refined.npz from the screen pulls). Outputs go to the scratchpad only; no eval reference is
# written or changed, nothing is tuned, and eval has no ground truth. Eval 8 uses library_v3x's beige cup (as its
# perception did), via a scratch mesh dir of symlinks.
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/heldpose/eval; PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
P6=20261026-pack6-5203d42
declare -A SRC=([8]=20261025-evb0810-ee7ba8e [14]=20261025-evb1420-ee7ba8e [25]=20261026-c25s42-feb0407
                [30]=20261025-std30-ee7ba8e [32]=20261026-fr32s46b-5e0e100 [33]=20261026-fr3233s43-6a8a0e2)
EPS="1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"
mkdir -p $W/in $W/meshes_ep8
for f in $REPO/meshes/library_v3/*.glb; do ln -sfn $f $W/meshes_ep8/$(basename $f); done
ln -sfn $REPO/meshes/library_v3x/beige_cup.glb $W/meshes_ep8/beige_cup.glb
for e in $EPS; do
  r=${SRC[$e]:-$P6}; d=$W/in/ep$e; mkdir -p $d
  if [ -n "${SRC[$e]:-}" ]; then pp=$S/daudit/dl_evsrc/runs/$r/perc2/ep$e/poses.npz; else pp=$S/daudit/dl_evposes/runs/$P6/perc2/ep$e/poses.npz; fi
  ln -sfn $pp $d/poses.npz
  ln -sfn $S/screen/dl/runs/$r/refs/perc2mck/ep$e/hands_refined.npz $d/hands_refined.npz
  echo "ep$e $r $(sha256sum $pp | cut -c1-16) $(sha256sum $d/hands_refined.npz | cut -c1-16)" >> $W/inputs.txt
done
{ sha256sum $REPO/pipeline/refine.py $REPO/pipeline/heldpose.py; (cd $REPO && git rev-parse HEAD); } > $W/code_version.txt
J=$W/jobs.txt; : > $J
for v in S2 S10g S10r S10t; do
  mkdir -p $W/runs/$v/logs
  case $v in S2) st="--steps S2";; S10g) st="--steps S2,S10 --s10_mode gate";; S10r) st="--steps S2,S10 --s10_mode replace";;
             S10t) st="--steps S2,S10 --s10_mode trans";; esac
  for e in $EPS; do
    m=$REPO/meshes/library_v3; [ $e = 8 ] && m=$W/meshes_ep8
    echo "$PY -I $REPO/pipeline/refine.py --in $W/in/ep$e --out $W/runs/$v/ep$e --meshes $m $st --force > $W/runs/$v/logs/ep$e.log 2>&1 || echo FAIL $v ep$e" >> $J
  done
done
cd /tmp && xargs -P 3 -I{} bash -c '{}' < $J
grep -l "Traceback" $W/runs/*/logs/*.log || echo "no tracebacks"
