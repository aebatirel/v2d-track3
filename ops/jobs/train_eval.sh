#!/bin/bash
# Train + evaluate eval-episode policies on references built by own_eval.sh (route A). Launch with
# RESUME_FROM=<own_eval run id> (restores /content/perc2m and /content/refs/perc2m) and e.g.
#   'SPLIT=eval RUNS="1:perc2:m:/content/perc2m/ep1 3:perc2:m:/content/perc2m/ep3" bash ops/jobs/train_eval.sh'
# The references store absolute paths of our simulator assets, so they are rebuilt first at the same place.
. /content/v2d-track3/ops/box/lib.sh
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v1} ASSETS=/content/assets SPLIT=${SPLIT:-eval}
python $REPO_DIR/pipeline/make_assets.py $MESH_DIR $ASSETS >> /content/job.log 2>&1 || { log "make_assets FAILED"; exit 1; }
exec bash $REPO_DIR/ops/jobs/train_runs.sh
