#!/bin/bash
# PUBLIC TWINS ONLY (diagnostics): overlap_frames.py with mocap GT poses of our meshes (gt_poses.py), our v3 hulls
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; C=$S/carve
export FLASH_CHORD_CACHE_DIR=$C/fccache; mkdir -p $C/gt/overlap
for x in "12 P12gl" "13 P13" "31 P31mck" "0 P0" "2 P2mck" "26 P26mck" "27 P27mc"; do set -- $x; ep=$1; tag=$2
  tree=$(grep "^$tag " $C/cases.txt | cut -d' ' -f2); p=$(find $tree/processed -name "*.parquet" | head -1)
  ( $C/fcvenv/bin/python -I $C/scripts/overlap_frames.py "$p" $C/assets/v3_def/mesh $C/gt/overlap/gt_ep$ep.json --stride 2 --poses $C/gt/gt_ep$ep.npz ) > $C/logs/gtoverlap_ep$ep.log 2>&1 &
  [ $(jobs -r | wc -l) -ge 2 ] && wait -n
done; wait; echo ALLDONE
