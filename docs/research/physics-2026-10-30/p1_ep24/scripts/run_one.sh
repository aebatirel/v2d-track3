#!/bin/bash
# run_one.sh NAME CONFIG FRAME [extra settle_p1.py args...]   (CONFIG = carved | default | default_inertia)
S=/tmp/claude-0/-home-user-v2d-track3/9bee9e08-a3b0-5c25-ae4f-3db987cc25f2/scratchpad
P=$S/p1ep24
FC=$S/src/video_to_data/robotic_grounding/flash_chord
TREE=$P/store/runs/20261030-physS1-6a814df/refs/glockt/ep24
name=$1; cfg=$2; frame=$3; shift 3
mkdir -p $P/runs $P/logs
cmd="cd $FC && FC=$FC EMB=sharpa_hands_mid FLASH_CHORD_CACHE_DIR=$P/fccache $S/fcvenv/bin/python $P/scripts/settle_p1.py --tree $TREE --assets $P/assets/$cfg --frame $frame --k ${K:-16} --seed 0 --sig_pos 0.0005 --sig_rot 0.005 --steps 40 --host wooden_piece_1 --guest wooden_piece_2 --out $P/runs/$name.json $*"
echo "$(date -u +%FT%TZ) $name: $cmd" >> $P/logs/commands.txt
start=$(date +%s)
( eval "$cmd" ) > $P/logs/$name.log 2>&1
rc=$?
echo "$(date -u +%FT%TZ) $name exit $rc wall $(( $(date +%s) - start )) s overflow_lines $(grep -c -i overflow $P/logs/$name.log)" | tee -a $P/logs/commands.txt
