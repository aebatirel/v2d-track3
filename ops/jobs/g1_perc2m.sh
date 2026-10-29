#!/bin/bash
# Mesh v5 G1 (docs/mesh-v5-spec-draft.md section 12, 2026-10-25): perc2m re-tracking of the public episodes that have
# no own-mesh tracks yet, so every object of the v5 library (lid, beige cup and pitcher included) has tracks made with
# our own meshes. perc2 with MESH_DIR=meshes/library_v2 (tier P1: library_v2 is deny-listed and entered only as the
# tracking template; owner decision O1), depth from the store cache, then MediaPipe hands and their refinement;
# STOP_AFTER=hands (mkref would read the scans when no ASSETS is set). Same layout as the 21 Oct perc2m runs
# (ep12/18/27 in 20261021-auto18-966eb96, ep24 in 20261021-auto24-966eb96): poses and the perception score against
# mocap (diagnostic, after inference) in /content/perc2m/ep<N>, hands in /content/refs/perc2m/ep<N>. Today's perc2
# defaults apply (detection rules of 23 Oct; DET_REPROP off).
#   ops/vast.sh create <offer> <run> 'bash ops/jobs/g1_perc2m.sh'      (EPS="..." to override the episode list)
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}
EPS=${EPS:-"0 2 11 13 21 22 23 26 31 39 40 41 42 43 44 45"}
log "g1_perc2m code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS]" >> $J
ensure_gdino $J                                                  # detection grounding term (pipeline/det_rules.py)
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit budget_mesh in score_registered (2026-10-25: missing)
label "G1 perc2m: $EPS"
for ep in $EPS; do
  bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "g1 ep$ep: no cached depth (computed here)" >> $J
  ( export PERC=perc2 VARIANT=m PDIR=/content/perc2m/ep$ep MESH_DIR=$REPO_DIR/meshes/library_v2 STOP_AFTER=hands SPLIT=public STEPS=0
    bash $P/pipeline_ep.sh $ep ) > /content/g1_ep$ep.log 2>&1
  rc=$?
  python $P/score_registered.py $ep /content/perc2m/ep$ep/poses_world_vo.npz --meshes $REPO_DIR/meshes/library_v2 \
    --out /content/perc2m/ep$ep/score_registered.json > /content/perc2m/ep$ep/score_registered.log 2>&1   # [D] after inference
  log "g1 ep$ep rc=$rc: $(grep -a 'perception:\|hands done\|FAILED' /content/g1_ep$ep.log | cut -c1-140 | tr '\n' ' ') | registered $(tail -2 /content/perc2m/ep$ep/score_registered.log | tr '\n' ' ' | cut -c1-200)" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true                # save as we go (the box is disposable)
done
log "g1_perc2m done" >> $J
