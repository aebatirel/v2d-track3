#!/bin/bash
# Route A on one box (2026-10-21; owner: "own meshes only"): our reconstructed meshes replace the public scans in
# detection, tracking and the simulator on the eval episodes.
#   1) simulator assets from the mesh library (pipeline/make_assets.py) -> /content/assets (env ASSETS for mkref)
#   2) H2 check on public episodes H2_EPS: perception tracking with our meshes, scored afterwards against mocap with
#      the registered scorer and our meshes (pipeline/score_registered.py)
#   3) eval episodes EPS: perception (our meshes) -> hands -> reference (our assets), i.e. ready for training
# Outputs: /content/perc2m/epN, /content/refs/perc2m/epN; eval depth caches go to the store (cache/depth/eval).
# As a job: ops/vast.sh create ... 'bash ops/jobs/own_eval.sh'
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v1} ASSETS=/content/assets
python $P/make_assets.py $MESH_DIR $ASSETS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
H2_EPS=${H2_EPS:-"41 27 23 39 12 21 2 18"}
EPS=${EPS:-"1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"}
label "own meshes: H2 on $H2_EPS, then eval references"
for ep in $H2_EPS; do
  bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || true
  PDIR=/content/perc2m/ep$ep PERC=perc2 STEPS=0 STOP_AFTER=perception bash $P/pipeline_ep.sh $ep \
    > /content/perc_h2_ep$ep.log 2>&1
  python $P/score_registered.py $ep /content/perc2m/ep$ep/poses_world_vo.npz --meshes $MESH_DIR > /dev/null 2>&1
  log "H2 ep$ep (tracked with our meshes; AUC SP MP MPPE per-object): $(python -c "
import json; r = json.load(open('/content/perc2m/ep$ep/poses_world_vo_registered.json'))['perception']
print(r['AUC'], r['SP_SR'], r['MP_SR'], r['MPPE_cm'], r['per_obj_AUC'])" 2>&1 | tail -1)" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
label "own meshes: eval references $EPS"
for ep in $EPS; do
  SPLIT=eval PDIR=/content/perc2m/ep$ep VARIANT=m PERC=perc2 STEPS=0 STOP_AFTER=reference bash $P/pipeline_ep.sh $ep \
    > /content/pipe_eval_ep$ep.log 2>&1
  rc=$?
  log "eval ep$ep rc=$rc $(grep -aE 'reference:|FAILED' /content/pipe_eval_ep$ep.log | tail -1 | cut -c1-150)" >> $J
  [ -s /content/perc2m/ep$ep/depths_fs0.5.npy ] && bash $OPS/store.sh push-depth $ep eval /content/perc2m > /dev/null 2>&1
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true                 # outputs so far (a crash keeps them)
done
exit 0
