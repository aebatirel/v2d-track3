#!/bin/bash
# Public leave-out (PREREG (b)): recompose control C with fold-map cameras, score control and variant with
# score_registered.py (mocap read only here, after inference). Usage: bash public_gate.sh WORK STORE T3 KIT MESHES
set -u
WORK=$1; STORE=$2; T3=$3; KIT=$4; M=$5; HERE=$(cd "$(dirname "$0")/../../../.." && pwd)
for e in 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45; do
  C=$(ls -d $STORE/runs/20261102-ptrk[AB]-7fbc3215/results/ptrk/C/ep$e 2>/dev/null | while read d; do [ -s $d/poses.npz ] && echo $d; done | head -1)
  [ -n "$C" ] && [ -s $C/poses.npz ] || { echo "ep$e: no control"; continue; }
  O=$WORK/compose/public/ep$e; mkdir -p $O
  [ -s $O/score_C.json ] || python3 $HERE/pipeline/score_registered.py $e $C/poses_world_vo.npz --meshes $M --t3 $T3 --kit $KIT --out $O/score_C.json > /dev/null 2>&1
  [ -s $WORK/reloc/public_lo/ep$e.npz ] || { echo "ep$e: no reloc yet"; continue; }
  [ -s $O/drift.json ] || python3 $HERE/pipeline/roommap_compose.py $C/poses.npz $WORK/reloc/public_lo/ep$e.npz $O --meshes $M --t3 $T3 --kit $KIT > /dev/null 2>&1
  [ -s $O/score_map.json ] || python3 $HERE/pipeline/score_registered.py $e $O/poses_world_map.npz --meshes $M --t3 $T3 --kit $KIT --out $O/score_map.json > /dev/null 2>&1
  echo "ep$e done"
done
