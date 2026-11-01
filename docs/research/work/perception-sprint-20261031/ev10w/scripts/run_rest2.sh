#!/bin/bash
# continuation of run_rest.sh after it was stopped (ev10 s0-s8 done): ev10 s10 + nest, then ev10w (v1 build) all
W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w
FPY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve/fcvenv/bin/python
export FC=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/src/video_to_data/robotic_grounding/flash_chord
export FLASH_CHORD_CACHE_DIR=$W/fccache_fc
TREE=$W/dl/runs/20261026-gl10A2-5e0e100/refs/glockt/ep10; cd $W
one() { $FPY -I /home/user/v2d-track3/tools/carve_fc_test.py --tree $TREE --assets $W/assets/$1 --out $W/out/rest/$2.json --names blue_cup,beige_cup --start $3 --end $4 --free_until 1000 > $W/logs/rest_$2.log 2>&1; }
one ev10 ev10_rest_s10 10 38; one ev10 ev10_nest_s120 120 160
for s in 0 2 4 6 8 10; do one ev10w ev10w_rest_s$s $s 38; done; one ev10w ev10w_nest_s120 120 160
echo done
