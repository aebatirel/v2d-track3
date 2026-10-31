#!/bin/bash
# B4 batch: for each public episode, stream its depth from the HF store, run the clean extraction (M1 hands, M2, M3
# per episode, M4) under the strace audit, then the B.3 ROI-swap validation (dev process), then delete the depth cache
# and the owner-label aux file. One episode at a time (local disk ~14 GB).
# Usage: b4_batch.sh CLEAN_RUN DEV_RUN EP [EP ...]      (from the repo root; DATA = the session scratchpad)
set -u
RUN=$1; DEVRUN=$2; shift 2
REPO=$(cd "$(dirname "$0")/../../../../.." && pwd)
MR=$REPO/docs/research/mesh-2026-10-26
DATA=${GMG_DATA_ROOT:-/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad}
V=$DATA/venv/bin/python
AUD=$DATA/gmg/audit
mkdir -p "$AUD" "$DATA/gmg/b4/logs"
cd "$MR" || exit 1
for ep in "$@"; do
  T0=$(date +%s)
  DEP=$DATA/cache/depth/public/ep$ep/depths_fs0.5.npy
  if [ ! -f "$DEP" ]; then
    for i in 1 2 3 4; do
      (cd /tmp && "$V" -I -c "from huggingface_hub import hf_hub_download as h; h('aebatirel/v2d-store', 'cache/depth/public/ep$ep/depths_fs0.5.npy', repo_type='dataset', local_dir='$DATA')") && break
      sleep $((2 ** i))
    done
  fi
  [ -f "$DEP" ] || { echo "ep$ep: depth download failed"; continue; }
  T1=$(date +%s)
  TAG=$(basename "$RUN")
  GMG_MODE=clean "$V" -W ignore gmg/tools/strace_audit.py run --log "$AUD/b4-$TAG-ep$ep.strace" \
    --manifest "$RUN/manifests/public-ep$ep.json" --allow "$DATA/mpvenv/**" -- \
    "$V" -W ignore gmg/tools/b4_extract.py --run "$RUN" --ep "$ep" > "$DATA/gmg/b4/logs/extract-ep$ep.log" 2>&1
  RC=$?
  T2=$(date +%s)
  GMG_MODE=dev "$V" -W ignore gmg/tools/b4_roi_swap.py --clean-run "$RUN" --run "$DEVRUN" --ep "$ep" \
    > "$DATA/gmg/b4/logs/roi-ep$ep.log" 2>&1
  RC3=$?
  T3=$(date +%s)
  rm -f "$DEP" "$RUN/aux/public/ep$ep/owners.npz"
  gzip -f "$AUD/b4-$TAG-ep$ep.strace" 2> /dev/null
  echo "ep$ep extract_rc=$RC roi_rc=$RC3 download_s=$((T1 - T0)) extract_s=$((T2 - T1)) roi_s=$((T3 - T2)) $(date -u +%H:%M:%S)"
done
echo BATCH_DONE
