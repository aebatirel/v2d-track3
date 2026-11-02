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
# depth prefetch (2026-11-02): one hf_hub_download per file, all episodes in parallel. `store.sh pull-depth` uses
# `hf download --include`, which lists the whole store repo (12-15 min per call on 2 Nov).
python - $EPS << 'PYEOF' >> $J 2>&1 || true
import os, sys
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
def get(e):
    try:
        f = hf_hub_download(os.environ.get('HF_STORE', 'aebatirel/v2d-store'), f'cache/depth/public/ep{e}/depths_fs0.5.npy', repo_type='dataset',
                            local_dir='/content/hfstore', token=os.environ.get('HF_TOKEN'))
        os.makedirs(f'/content/cache/depth/ep{e}', exist_ok=True)
        d = f'/content/cache/depth/ep{e}/depths_fs0.5.npy'
        if not os.path.exists(d): os.symlink(f, d)
        return f'ep{e} ok'
    except Exception as x:
        return f'ep{e} prefetch failed: {x!r}'[:200]
with ThreadPoolExecutor(6) as ex:
    print('prefetch:', list(ex.map(get, sys.argv[1:])))
PYEOF
for ep in $EPS; do
  [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] || bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "ptrk ep$ep: no cached depth (computed here)" >> $J
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
