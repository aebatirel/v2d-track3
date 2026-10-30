#!/bin/bash
# overlap_frames.py on every case in cases.txt (stride 2), 2 at a time
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; C=$S/carve
export FLASH_CHORD_CACHE_DIR=$C/fccache; mkdir -p $C/overlap
run() { local tag=$1 tree=$2 assets=$3; local p=$(find $tree/processed -name "*.parquet" | head -1)
  ( time $C/fcvenv/bin/python -I $C/scripts/overlap_frames.py "$p" $assets/mesh $C/overlap/$tag.json --stride 2 ) > $C/logs/overlap_$tag.log 2>&1; echo "$tag done $(grep real $C/logs/overlap_$tag.log)"; }
while read tag tree assets; do run $tag $tree $assets & [ $(jobs -r | wc -l) -ge 2 ] && wait -n; done < $C/cases.txt; wait
