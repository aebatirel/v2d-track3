#!/bin/bash
# Detection dumps for offline rule replay (2026-10-23; tools/det_replay.py, scored by tools/det_score.py): perc2 with
# DET_ONLY=1 on public episodes, our library meshes as templates (as in the pipeline), frames DET_FRAMES (default:
# 0 and the quarter points of each episode, so the rules are judged on ~4x more instances than frame 0 alone). Depth
# only for those frames, no camera track, no tracking. Outputs /content/det/ep<N>/det_f<k>.npz (+ log.txt), pushed
# to the store with the run. Estimate ≈ 1.5–3 min per episode after setup (SAM2 + DINOv2 + templates per frame).
#   ops/vast.sh create <offer> <run_id> 'bash ops/jobs/det_dump.sh'   (or run after another job on a box)
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}
EPS=${EPS:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} SPLIT=public
label "det dumps: $EPS"
for ep in $EPS; do
  O=/content/det/ep$ep; mkdir -p $O
  n=$(python -c "import pyarrow.parquet as pq; print(pq.read_metadata('/content/t3/ep$ep.parquet').num_rows)" 2>/dev/null || echo 4)
  F=${DET_FRAMES:-"0,$((n / 4)),$((n / 2)),$((3 * n / 4))"}
  DET_ONLY=1 DET_VERIFY=${DET_VERIFY:-4} DET_FRAMES=$F EP=$ep OUT=$O python $P/perc2.py > $O/log.txt 2>&1
  log "det_dump ep$ep frames $F rc=$? $(ls $O/det_f*.npz 2>/dev/null | wc -l) dumps $(grep -a 'det dump failed\|Traceback' $O/log.txt | head -1 | cut -c1-120)" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
