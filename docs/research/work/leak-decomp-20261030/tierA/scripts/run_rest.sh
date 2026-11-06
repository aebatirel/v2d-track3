#!/bin/bash
# A3 rest settle (leak_settle.py rest) per episode: one scene and its hull SDFs for the 4 arms. Usage: run_rest.sh LOG EP...
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
export FLASH_CHORD_CACHE_DIR=$S/carve/fccache FC=$S/src/video_to_data/robotic_grounding/flash_chord OMP_NUM_THREADS=1
TPL=$(ls $S/carve/refs/store/runs/20261024-e3-e49e83d/refs/perc2mck/ep2/processed/*/*/*.parquet); A=$S/leak/oracle_tierA/a3
log=$1; shift; cd $FC
for e in "$@"; do
  $S/carve/fcvenv/bin/python /home/user/v2d-track3/tools/leak_settle.py rest --template $TPL --assets $S/leak/oracle_tierA/a7/assets/lib \
    $A/ep$e/P_base.npz $A/ep$e/P_S2.npz $A/ep$e/O_base.npz $A/ep$e/O_S2.npz 2>&1 | grep -E "rest_settle|Error|Traceback" || echo "FAIL ep$e"
done >> $log 2>&1
echo "DONE $(date -u +%T)" >> $log
