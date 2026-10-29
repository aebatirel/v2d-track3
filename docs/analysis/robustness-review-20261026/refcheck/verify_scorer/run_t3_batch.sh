#!/bin/bash
# verify_scorer: GT-free registration at Kaggle eval seeds (1_000_003*eval + 101*slot) for the anchor-type objects the
# scorer check declared flip-free on only 3 hosts. One process at a time.
source /tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/venv/bin/activate
V=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer
W=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/verify_scorer
cd $W
for x in "wooden_piece_1 25000075 ev25s0" "wooden_piece_2 25000176 ev25s1" "mini_dust_pan 38000114 ev38s0" \
         "plastic_dish_rack 14000143 ev14s1" "white_pot 1000003 ev1s0" "mini_dust_pan 19000158 ev19s1"; do
  set -- $x
  python -I $V/t3_evalreg.py library_v3 $1 $2 $V/t3/${1}_v3_$3.json 20 > $W/t3_${1}_$3.log 2>&1
  echo "$1 $3 done $(date -u +%H:%M:%S)" >> $W/t3_batch_progress.txt
done
echo "ALL done $(date -u +%H:%M:%S)" >> $W/t3_batch_progress.txt
