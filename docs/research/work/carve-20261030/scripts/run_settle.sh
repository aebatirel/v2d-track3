#!/bin/bash
# settle_at2.py for one case: run_settle.sh TAG ASSETS FRAMES NAME   (2 s, hands parked, no drive)
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve
export FLASH_CHORD_CACHE_DIR=$S/fccache FC=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/src/video_to_data/robotic_grounding/flash_chord
tag=$1; assets=$2; frames=$3; name=$4
read _ tree _ < <(grep "^$tag " $S/cases.txt)
( time $S/fcvenv/bin/python $S/scripts/settle_at2.py --tree $tree --assets $assets --frames $frames --steps 40 --out $S/settle/$name.json ) > $S/blogs/settle_$name.log 2>&1
echo "$name settle exit $? $(grep real $S/blogs/settle_$name.log)"
