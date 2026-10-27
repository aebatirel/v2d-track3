#!/bin/bash
# Is the pack-5 pitcher swap gain (library_v3 -> library_v3p, ep21 twin, docs/analysis/meshswap-20261026: +0.098 at the
# scorer's seed) robust to the registration seed? Same rollouts, 6 registration seeds each. Runs after run_f0.sh.
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
S=$R/store; KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p3; mkdir -p $D/meshswap_seeds
source $R/venv/bin/activate; cd $W
V="--variant seed0:reg_seed_offset=0 --variant seed1:reg_seed_offset=1 --variant seed2:reg_seed_offset=2 --variant seed3:reg_seed_offset=3 --variant seed4:reg_seed_offset=4 --variant seed5:reg_seed_offset=5"
for r in r1 r2; do
  for lib in library_v3 library_v3p; do
    python -I $D/score_variants.py 21 $S/runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/$r --meshes $M/$lib \
      --t3 $R/t3 --kit $KIT --out $D/meshswap_seeds/ep21_${r}_$lib.json --trajs sim $V > $W/ms_${r}_$lib.log 2>&1
  done
done
echo "MS ALL done $(date -u +%H:%M:%S)" >> $W/progress.txt
