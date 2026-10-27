#!/bin/bash
# Frame-0 transient test on the public rollouts with the largest first-step gaps (frame0_gaps_public.txt): the 'sim'
# trajectory scored as is (base) and with its frame 0 replaced by its reference's frame 0 (f0ref). Runs after run_part3.sh.
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
S=$R/store; KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p3
source $R/venv/bin/activate; cd $W
for x in "31 runs/20261024-ev30rp-07eef1a/results/glock_public/ep31/best library_v3" \
         "27 runs/20261024-ev2-2c1e4dd/results/glock_public/ep27/best library_v3" \
         "24 runs/20261024-ev3-2c1e4dd/results/glock_public/ep24/best library_v3" \
         "12 runs/20261024-ev2-2c1e4dd/results/glock_public/ep12/best library_v3" \
         "26 runs/20261024-w1-37cc551/results/glock_public/ep26/best library_v3"; do
  set -- $x
  for r in r1 r2 r3; do
    python -I $D/score_variants.py $1 $S/$2/$r --meshes $M/$3 --t3 $R/t3 --kit $KIT --out $D/f0/ep$1_$r.json --trajs sim \
      --variant base --variant f0ref:f0_from_ref=1 > $W/f0_ep$1_$r.log 2>&1
  done
  echo "f0 ep$1 done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
echo "F0 ALL done $(date -u +%H:%M:%S)" >> $W/progress.txt
