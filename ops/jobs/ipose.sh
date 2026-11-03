#!/bin/bash
# Instance-pose PoC (3 Nov 2026; docs/analysis/ipose-20261103/PREREG.md): pot network, arms R (rendered only) and R+M
# (+ train-episode mocap labels from docs/analysis/ipose-20261103/labels_rm/train_labels.npz, made off-box).
# Inference reads frames, cached stereo depth and the CONTROL track only; scoring is done off-box by the agent.
#   ops/vast.sh create <offer> <run> 'bash ops/jobs/ipose.sh'
# Outputs /content/results/ipose/{synth_preview,R,RM,real_preview}/ (checkpoints, logs, poses_world_vo_*.npz per test
# episode). Synth shards stay in /content/ipose_data (regenerable, not pushed).
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline/ipose; J=${J:-/content/job.log}; O=/content/results/ipose; W=/content/ipose_data
mkdir -p $O $W
TRAIN=${TRAIN:-"0 26 41 42 43"}; TEST=${TEST:-"2 27 44 45"}
NSYN=${NSYN:-15000}; EPR=${EPR:-40}; EPRM=${EPRM:-10}; ARMS=${ARMS:-"R RM"}
log "ipose code $(git -C $REPO_DIR rev-parse --short HEAD) train [$TRAIN] test [$TEST] nsyn $NSYN arms [$ARMS]" >> $J
python -c "import torchvision, trimesh, cv2; print('deps ok', torchvision.__version__)" >> $J 2>&1 || pip install -q torchvision trimesh >> $J 2>&1
# depth prefetch: one hf_hub_download per file (see perc_vos.sh)
python - $TRAIN $TEST << 'PYEOF' >> $J 2>&1
import os, sys
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
def get(e):
    try:
        f = hf_hub_download(os.environ.get('HF_STORE', 'aebatirel/v2d-store'), f'cache/depth/public/ep{e}/depths_fs0.5.npy',
                            repo_type='dataset', local_dir='/content/hfstore', token=os.environ.get('HF_TOKEN'))
        os.makedirs(f'/content/cache/depth/ep{e}', exist_ok=True)
        d = f'/content/cache/depth/ep{e}/depths_fs0.5.npy'
        if not os.path.exists(d): os.symlink(f, d)
        return f'ep{e} ok'
    except Exception as x:
        return f'ep{e} FAILED {x!r}'[:200]
with ThreadPoolExecutor(5) as ex:
    print('prefetch:', list(ex.map(get, sys.argv[1:])))
PYEOF
label "ipose synth"
if ! ls $W/synth_*.json > /dev/null 2>&1; then
  per=$(( NSYN / 3 ))
  for s in 0 1 2; do python $P/gen_synth.py $W $per --seed $s > $O/gen_synth_$s.log 2>&1 & done; wait
  mkdir -p $O/synth_preview; cp $W/preview_*.jpg $W/synth_*.json $O/synth_preview/ 2> /dev/null
fi
log "synth: $(ls $W/synth_*.npz | wc -l) shards; $(tail -1 $O/gen_synth_0.log)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
infer() {  # $1 arm
  for e in $TEST; do
    label "ipose infer $1 ep$e"
    python $P/infer.py $e $O/$1/ckpt.pt $O/$1/ep$e > $O/$1/infer_ep$e.log 2>&1
    log "infer $1 ep$e rc=$?: $(tail -1 $O/$1/infer_ep$e.log | cut -c1-300)" >> $J
  done
}
if [[ " $ARMS " == *" R "* ]]; then
  mkdir -p $O/R; label "ipose train R"
  [ -s $O/R/done ] || { python $P/train.py $O/R --synth "$W/synth_*.npz" --epochs $EPR > $O/R/train.log 2>&1 && touch $O/R/done; }
  log "train R: $(tail -2 $O/R/train.log | tr '\n' ' ' | cut -c1-300)" >> $J
  infer R
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
fi
if [[ " $ARMS " == *" RM "* ]]; then
  mkdir -p $O/RM $O/real_preview; label "ipose real crops"
  [ -s $W/real_ep43.npz ] || python $P/make_real.py $REPO_DIR/docs/analysis/ipose-20261103/labels_rm/train_labels.npz $W \
      --eps $(echo $TRAIN | tr ' ' ',') > $O/RM/make_real.log 2>&1
  cp $W/preview_real_*.jpg $O/real_preview/ 2> /dev/null
  log "real: $(grep -a '^ep' $O/RM/make_real.log | tr '\n' ' ')" >> $J
  label "ipose train RM"
  [ -s $O/RM/done ] || { python $P/train.py $O/RM --synth "$W/synth_*.npz" --real "$W/real_*.npz" --init $O/R/ckpt.pt \
      --epochs $EPRM > $O/RM/train.log 2>&1 && touch $O/RM/done; }
  log "train RM: $(tail -2 $O/RM/train.log | tr '\n' ' ' | cut -c1-300)" >> $J
  infer RM
fi
log "ipose done" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
