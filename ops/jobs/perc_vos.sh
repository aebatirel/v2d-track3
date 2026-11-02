#!/bin/bash
# Tracking-perception batch (2026-11-02, tracking-perception session; rule pre-registered in
# docs/analysis/ptrk-20261102/PREREG.md before any run): perc2 on public episodes once per variant, all with today's
# eval defaults (library_v3 templates, TRACK_GUARD on, detection rules), cached public depth. Scoring against mocap is
# done afterwards by the agent (score_registered.py, 9a+ meshes), not here; perc2's own result.json is diagnostic only.
#   ops/vast.sh create <offer> <run> 'EPS="2 12" VARIANTS="C: MG:TRACK_VOS=1,VOS_DEPTH=1" bash ops/jobs/perc_vos.sh'
# Output /content/results/ptrk/<variant>/ep<N>/ (poses.npz, poses_world_vo.npz, log.txt, track_guard.json,
# track_vos.json, vos_masks.npz).
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/ptrk; mkdir -p $O
EPS=${EPS:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
VARIANTS=${VARIANTS:-"C:"}
LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "perc_vos code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], variants [$VARIANTS], LIB $LIB" >> $J
ensure_gdino $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
for ep in $EPS; do
  bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "ptrk ep$ep: no cached depth (computed here)" >> $J
  for v in $VARIANTS; do
    name=${v%%:*}; envs=${v#*:}; D=$O/$name/ep$ep; mkdir -p $D
    [ -s $D/poses_world_vo.npz ] && continue
    [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] && [ ! -e $D/depths_fs0.5.npy ] && ln -sf /content/cache/depth/ep$ep/depths_fs0.5.npy $D/
    label "ptrk ep$ep $name"
    t0=$(date +%s)
    ( [ -n "$envs" ] && export $(echo "$envs" | tr ',' ' ')
      KF_MIN=120 EP=$ep OUT=$D SPLIT=public MESH_DIR=${MESH_DIR:-$LIB} python $P/perc2.py > $D/log.txt 2>&1 )
    rc=$?
    log "ptrk ep$ep $name rc=$rc $(( $(date +%s) - t0 ))s: $(grep -a 'vos summary\|^\[.*\] vo  ' $D/log.txt | tail -2 | cut -c1-220 | tr '\n' ' ')" >> $J
    [ $rc = 0 ] || tail -5 $D/log.txt >> $J
    rm -f $D/depths_fs*.npy                                   # depth caches never go to the store
  done
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
done
log "perc_vos done" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
