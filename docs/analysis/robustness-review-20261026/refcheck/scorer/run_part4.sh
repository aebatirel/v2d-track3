#!/bin/bash
# Part 4 (27 Oct, after the 26 Oct session ended mid-run). One heavy process at a time, in this order:
#  (0) f0 transient on ep21 r1 (validates the 27 Oct f0_from_ref fix of score_variants.py);
#  (1) pitcher swap (library_v3 -> library_v3p) on the ep21 twin under registration seeds, Kaggle's eval-20 seed
#      (offset -1_000_003: 1_000_003*20 + 101*slot), decimated host scans and the alternative anchor / points.
#      Kaggle measured the swap at -0.0045 Track 3 AUC (pack 5 -> 6), i.e. about -0.09 on eval 20; the twin said +0.098;
#  (2) GT-free registration of every submitted mesh at Kaggle's eval seeds, host = public scan, full / 20000 / 4096 faces;
#  (3) f0 transient on the other public rollouts with large first-step gaps;
#  (4) welded host-scan decimation on perception tracks (replaces the invalid sens2 decimation columns).
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
S=$R/store; KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p4
mkdir -p $W $D/f0 $D/meshswap_seeds $D/sens3 $D/regflip
source $R/venv/bin/activate; cd $W
P=$W/progress.txt
f0() {  # ep results_dir lib tag
  python -I $D/score_variants.py $1 $S/$2 --meshes $M/$3 --t3 $R/t3 --kit $KIT --out $D/f0/ep$1_$4.json --trajs sim \
    --variant base --variant f0ref:f0_from_ref=1 > $W/f0_ep$1_$4.log 2>&1
  echo "f0 ep$1 $4 done $(date -u +%H:%M:%S)" >> $P
}
f0 21 runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/r1 library_v3 r1

V="--variant seed0:reg_seed_offset=0 --variant seed1:reg_seed_offset=1 --variant seed2:reg_seed_offset=2"
V="$V --variant seed3:reg_seed_offset=3 --variant seed4:reg_seed_offset=4"
V="$V --variant evalseed:reg_seed_offset=-1000003 --variant evalseed_h20000:reg_seed_offset=-1000003,scan_faces=20000"
V="$V --variant h20000:scan_faces=20000 --variant bbox:anchor=bbox --variant vtx500:points=vertex,n_points=500"
for r in r1 r2; do
  for lib in library_v3 library_v3p; do
    python -I $D/score_variants.py 21 $S/runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/$r --meshes $M/$lib \
      --t3 $R/t3 --kit $KIT --out $D/meshswap_seeds/ep21_${r}_$lib.json --trajs sim $V > $W/ms_${r}_$lib.log 2>&1
    echo "meshswap $r $lib done $(date -u +%H:%M:%S)" >> $P
  done
done

python -I $D/reg_flip.py $R/t3 $KIT /home/user/v2d-track3 $D/regflip/reg_flip.json 0 20000 4096 > $W/regflip.log 2>&1
echo "regflip done $(date -u +%H:%M:%S)" >> $P

f0 21 runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/r2 library_v3 r2
for r in r1 r2 r3; do f0 31 runs/20261024-ev30rp-07eef1a/results/glock_public/ep31/best/$r library_v3 $r; done
f0 27 runs/20261024-ev2-2c1e4dd/results/glock_public/ep27/best/r1 library_v3 r1
f0 24 runs/20261024-ev3-2c1e4dd/results/glock_public/ep24/best/r1 library_v3 r1
f0 12 runs/20261024-ev2-2c1e4dd/results/glock_public/ep12/best/r1 library_v3 r1
f0 26 runs/20261024-w1-37cc551/results/glock_public/ep26/best/r1 library_v3 r1
f0 11 runs/20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best/r1 library_v3x r1
f0 2 runs/20261024-e3-e49e83d/results/glock_public/ep2/best/r1 library_v3 r1

for ep in 2 18 24 31 22 13; do
  python -I $D/score_variants.py $ep $S/runs/20261025-sweep-a894083/results/sweep/base/ep$ep/poses_world_vo.npz \
    --meshes $M/library_v2 --t3 $R/t3 --kit $KIT --out $D/sens3/ep$ep.json --variant base \
    --variant h50000:scan_faces=50000 --variant h20000:scan_faces=20000 --variant h4096:scan_faces=4096 > $W/sens3_ep$ep.log 2>&1
  echo "sens3 ep$ep done $(date -u +%H:%M:%S)" >> $P
done
echo "PART4 ALL done $(date -u +%H:%M:%S)" >> $P
