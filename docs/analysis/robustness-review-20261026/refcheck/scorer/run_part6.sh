#!/bin/bash
# Part 6 (27 Oct): at Kaggle's FIXED eval seed, how does the registration of our submitted mesh depend on the (unknown)
# resolution of the hidden scan? Host = public scan, welded + decimated to many face counts. GT-free. Waits for part 5.
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p4; P=$W/progress.txt
until grep -q "PART5 ALL" $P; do sleep 20; done
source $R/venv/bin/activate; cd $W; mkdir -p $D/reghosts
H="0 50000 30000 20000 16000 12000 8192 6000 4096 3000 2000"
for x in "library_v3 mini_sweeper 30000090 ev30s0" "library_v3 mini_sweeper 19000057 ev19s0" \
         "library_v3 wooden_piece_1 25000075 ev25s0" "library_v3 wooden_piece_2 25000176 ev25s1" \
         "library_v3 water_pitcher 20000161 ev20s1" "library_v3p water_pitcher 20000161 ev20s1"; do
  set -- $x
  python -I $D/reg_seeds.py $R/t3 $KIT $M/$1/$2.glb $2 $D/reghosts/${2}_$1_$4.json 1 $3 $H > $W/reghosts_${2}_$1_$4.log 2>&1
  echo "reghosts $2 $1 $4 done $(date -u +%H:%M:%S)" >> $P
done
echo "PART6 ALL done $(date -u +%H:%M:%S)" >> $P
