#!/bin/bash
# Host-scan resolution (welded + decimated scan used for registration; the kit's 16 MB host-geometry limit rules out
# full-resolution scans). Replaces the invalid first attempt in sens2_INVALID_unwelded_decimation/ (no weld).
R=/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck
D=/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/scorer
S=$R/store; KIT=$R/kit/v2d_submission_kit; M=/home/user/v2d-track3/meshes; W=$R/work/scorer/p3; mkdir -p $D/sens3
source $R/venv/bin/activate; cd $W
for ep in 2 18 24 31 22 13; do
  python -I $D/score_variants.py $ep $S/runs/20261025-sweep-a894083/results/sweep/base/ep$ep/poses_world_vo.npz \
    --meshes $M/library_v2 --t3 $R/t3 --kit $KIT --out $D/sens3/ep$ep.json --variant base \
    --variant scan50000:scan_faces=50000 --variant scan20000:scan_faces=20000 --variant scan4096:scan_faces=4096 > $W/sens3_ep$ep.log 2>&1
  echo "sens3 ep$ep done $(date -u +%H:%M:%S)" >> $W/progress.txt
done
echo "SENS3 ALL done $(date -u +%H:%M:%S)" >> $W/progress.txt
