#!/bin/bash
# Part 2: stand-in sensitivity of the registered score on sweep-base perception tracks (library_v2 = their tracking
# templates). One process at a time (shared 4-core box).
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
W=$R/work/scorer/sens; mkdir -p $W $D/sens
source $R/venv/bin/activate; cd $W
COMMON="--variant base --variant n4000:n_points=4000 --variant bbox:anchor=bbox --variant vtx500:points=vertex,n_points=500 --variant seed1:reg_seed_offset=1 --variant seed2:reg_seed_offset=2"
CUPS="--variant axisz:axis=z --variant axisfit:axis=fit"
for ep in 2 11 13 18 22 24 31; do
  extra=; case $ep in 11|13|22) extra=$CUPS;; esac
  python -I $D/score_variants.py $ep $R/store/runs/20261025-sweep-a894083/results/sweep/base/ep$ep/poses_world_vo.npz \
    --meshes /home/user/v2d-track3/meshes/library_v2 --t3 $R/t3 --kit $R/kit/v2d_submission_kit \
    --out $D/sens/ep$ep.json $COMMON $extra > $W/ep$ep.log 2>&1
  echo "ep$ep done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
