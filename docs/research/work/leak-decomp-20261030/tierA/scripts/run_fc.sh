#!/bin/bash
# FlashCHORD-side Tier A runs (leak_settle.py) in the fcvenv: MODE=rest (A3 rest settle) or MODE=settle (A7), on a list of npz.
# Usage: run_fc.sh MODE LOG NPZ...
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
export FLASH_CHORD_CACHE_DIR=$S/carve/fccache FC=$S/src/video_to_data/robotic_grounding/flash_chord
TPL=$(ls $S/carve/refs/store/runs/20261024-e3-e49e83d/refs/perc2mck/ep2/processed/*/*/*.parquet)
mode=$1; log=$2; shift 2
cd $FC
for f in "$@"; do
  if [ $mode = rest ]; then
    $S/carve/fcvenv/bin/python /home/user/v2d-track3/tools/leak_settle.py rest --template $TPL --assets $S/leak/oracle_tierA/a7/assets/lib $f
  else
    $S/carve/fcvenv/bin/python /home/user/v2d-track3/tools/leak_settle.py settle --template $TPL $f
  fi 2>&1 | grep -E "rest_settle|: \{| f[0-9]+:|Error|Traceback|error" || echo "FAIL $f"
done >> $log 2>&1
echo "DONE $mode $(date -u +%T)" >> $log
