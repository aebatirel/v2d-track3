#!/bin/bash
# Parts 3 and 2b, run after run_sensitivity.sh (one heavy process at a time).
#  (a) kit packer + official metric files vs pipeline/score_registered.py on stored public rollouts;
#  (b) scan decimation + more registration seeds on perception tracks;
#  (c) frame-0 transient: sim frame 0 replaced by its reference frame 0.
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
S=$R/store; KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes
W=$R/work/scorer/p3; mkdir -p $W $D/e2e $D/sens2 $D/f0
source $R/venv/bin/activate; cd $W
for x in "21 runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/r1 library_v3" \
         "2 runs/20261024-e3-e49e83d/results/glock_public/ep2/best/r1 library_v3" \
         "11 runs/20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best/r1 library_v3x"; do
  set -- $x
  python -I $D/kit_e2e.py $1 $S/$2 $M/$3 --t3 $R/t3 --kit $KIT --work $W/e2e --out $D/e2e/ep$1_kit.json > $W/e2e_ep$1.log 2>&1
  python -I /home/user/v2d-track3/pipeline/score_registered.py $1 $S/$2 --meshes $M/$3 --t3 $R/t3 --kit $KIT \
    --out $D/e2e/ep$1_score_registered.json > $W/sr_ep$1.log 2>&1
  echo "e2e ep$1 done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
for ep in 2 18 24 31 22; do
  python -I $D/score_variants.py $ep $S/runs/20261025-sweep-a894083/results/sweep/base/ep$ep/poses_world_vo.npz \
    --meshes $M/library_v2 --t3 $R/t3 --kit $KIT --out $D/sens2/ep$ep.json --variant base \
    --variant scan4096:scan_faces=4096 --variant scan20000:scan_faces=20000 --variant seed3:reg_seed_offset=3 \
    --variant seed4:reg_seed_offset=4 --variant seed5:reg_seed_offset=5 --variant seed6:reg_seed_offset=6 > $W/sens2_ep$ep.log 2>&1
  echo "sens2 ep$ep done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
for x in "21 runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best library_v3" \
         "2 runs/20261024-e3-e49e83d/results/glock_public/ep2/best library_v3"; do
  set -- $x
  for r in r1 r2 r3; do
    python -I $D/score_variants.py $1 $S/$2/$r --meshes $M/$3 --t3 $R/t3 --kit $KIT --out $D/f0/ep$1_$r.json --trajs sim \
      --variant base --variant f0ref:f0_from_ref=1 > $W/f0_ep$1_$r.log 2>&1
  done
  echo "f0 ep$1 done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
python -I $D/score_variants.py 11 $S/runs/20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best/r1 --meshes $M/library_v3x \
  --t3 $R/t3 --kit $KIT --out $D/f0/ep11_r1.json --trajs sim --variant base --variant f0ref:f0_from_ref=1 > $W/f0_ep11_r1.log 2>&1
echo "ALL done $(date -u +%H:%M:%S)" >> $W/progress.txt
