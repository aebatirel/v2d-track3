#!/bin/bash
# Eval perception with SAM2 video masks (2026-11-02, tracking-perception session): only to obtain vos_masks.npz for the
# GT-free placement fit (docs/analysis/ptrk-20261102/PREREG_posemesh.md, Part 2) of eval episodes. Same perc2 defaults
# as the eval pipeline (library_v3 templates, TRACK_GUARD), TRACK_VOS=1 with every VOS use off, cached eval depth.
# Nothing is scored (no ground truth exists). Output /content/results/evos/ep<N>/.
#   ops/vast.sh create <offer> <run> 'EPS="20" bash ops/jobs/eval_vos.sh'
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/evos; mkdir -p $O
EPS=${EPS:?EPS missing}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
log "eval_vos code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS]" >> $J
ensure_gdino $J
for ep in $EPS; do
  python - $ep << 'PYEOF' >> $J 2>&1 || true
import os, sys
from huggingface_hub import hf_hub_download
e = sys.argv[1]
f = hf_hub_download(os.environ.get('HF_STORE', 'aebatirel/v2d-store'), f'cache/depth/eval/ep{e}/depths_fs0.5.npy', repo_type='dataset',
                    local_dir='/content/hfstore', token=os.environ.get('HF_TOKEN'))
print('prefetch eval ep', e, f)
PYEOF
  D=$O/ep$ep; mkdir -p $D
  F=/content/hfstore/cache/depth/eval/ep$ep/depths_fs0.5.npy; [ -s $F ] && ln -sf $F $D/depths_fs0.5.npy
  label "eval_vos ep$ep"
  TRACK_VOS=1 KF_MIN=120 EP=$ep OUT=$D SPLIT=eval MESH_DIR=$LIB python $P/perc2.py > $D/log.txt 2>&1
  log "eval_vos ep$ep rc=$? $(grep -a 'vos: propagated\|DONE' $D/log.txt | tail -2 | tr '\n' ' ' | cut -c1-200)" >> $J
  rm -f $D/depths_fs*.npy
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
done
log "eval_vos done" >> $J
