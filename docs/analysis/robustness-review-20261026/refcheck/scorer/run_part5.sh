#!/bin/bash
# Part 5 (27 Oct): GT-free registration-seed spread of the two eval-20 pitcher meshes (library_v3 submitted in packs 4 and 6,
# library_v3p in pack 5), 30 seeds from Kaggle's eval-20 pitcher seed 1_000_003*20 + 101*1, host = public scan at
# full / 20000 / 4096 faces. Waits for run_part4.sh (one heavy process at a time).
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p4; P=$W/progress.txt
until grep -q "PART4 ALL" $P; do sleep 20; done
source $R/venv/bin/activate; cd $W; mkdir -p $D/regseeds
for lib in library_v3 library_v3p; do
  python -I $D/reg_seeds.py $R/t3 $KIT $M/$lib/water_pitcher.glb water_pitcher $D/regseeds/water_pitcher_$lib.json 30 20000161 \
    0 20000 4096 > $W/regseeds_$lib.log 2>&1
  echo "regseeds $lib done $(date -u +%H:%M:%S)" >> $P
done
echo "PART5 ALL done $(date -u +%H:%M:%S)" >> $P
