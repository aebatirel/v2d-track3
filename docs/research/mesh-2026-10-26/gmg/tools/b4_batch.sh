#!/bin/bash
# B4 batch: for each public episode, stream its depth from the HF store, run the clean extraction (M1 hands, M2, M3
# per episode, M4) under the strace audit, then the B.3 ROI-swap validation (dev process), then delete the depth cache
# and the owner-label aux file. One episode at a time per stream (local disk).
# Resumable: an episode whose done marker (<DATA>/gmg/b4/logs/<run>/ep<N>.done) exists is skipped; an episode whose
# clean manifest exists but whose B.3 record does not gets the B.3 step only; any other episode is (re)run from
# scratch after its partial outputs (a killed process) are removed from the run folder.
# Usage: b4_batch.sh CLEAN_RUN DEV_RUN EP [EP ...]      (DATA = the session scratchpad)
set -u
RUN=$1; DEVRUN=$2; shift 2
REPO=$(cd "$(dirname "$0")/../../../../.." && pwd)
MR=$REPO/docs/research/mesh-2026-10-26
DATA=${GMG_DATA_ROOT:-/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad}
V=$DATA/venv/bin/python
AUD=$DATA/gmg/audit
TAG=$(basename "$RUN")
LOGD=$DATA/gmg/b4/logs/$TAG
mkdir -p "$AUD" "$LOGD"
cd "$MR" || exit 1
for ep in "$@"; do
  if [ -f "$LOGD/ep$ep.done" ]; then echo "ep$ep skip (done: $(cat "$LOGD/ep$ep.done"))"; continue; fi
  T0=$(date +%s)
  DEP=$DATA/cache/depth/public/ep$ep/depths_fs0.5.npy
  MAN=$RUN/manifests/public-ep$ep.json
  B3=$DEVRUN/b3/public-ep$ep.json
  if [ ! -f "$DEP" ]; then
    for i in 1 2 3 4; do
      (cd /tmp && "$V" -I -c "from huggingface_hub import hf_hub_download as h; h('aebatirel/v2d-store', 'cache/depth/public/ep$ep/depths_fs0.5.npy', repo_type='dataset', local_dir='$DATA')") && break
      sleep $((2 ** i))
    done
  fi
  [ -f "$DEP" ] || { echo "ep$ep: depth download failed"; continue; }
  T1=$(date +%s)
  RC=0
  if [ -f "$MAN" ] && [ -f "$RUN/aux/public/ep$ep/owners.npz" ]; then
    echo "ep$ep: manifest exists, B.3 only"
  else
    rm -rf "$RUN/bundle/public/ep$ep" "$RUN/hands/public/ep$ep" "$RUN/aux/public/ep$ep" "$RUN/logs/public-ep$ep.log" "$MAN"
    GMG_MODE=clean "$V" -W ignore gmg/tools/strace_audit.py run --log "$AUD/b4-$TAG-ep$ep.strace" \
      --manifest "$MAN" --allow "$DATA/mpvenv/**" -- \
      "$V" -W ignore gmg/tools/b4_extract.py --run "$RUN" --ep "$ep" > "$LOGD/extract-ep$ep.log" 2>&1
    RC=$?
  fi
  T2=$(date +%s)
  RC3=-1
  if [ "$RC" = 0 ]; then
    GMG_MODE=dev "$V" -W ignore gmg/tools/b4_roi_swap.py --clean-run "$RUN" --run "$DEVRUN" --ep "$ep" \
      > "$LOGD/roi-ep$ep.log" 2>&1
    RC3=$?
  fi
  T3=$(date +%s)
  rm -f "$DEP" "$RUN/aux/public/ep$ep/owners.npz"
  gzip -f "$AUD/b4-$TAG-ep$ep.strace" 2> /dev/null
  LINE="ep$ep extract_rc=$RC roi_rc=$RC3 download_s=$((T1 - T0)) extract_s=$((T2 - T1)) roi_s=$((T3 - T2)) $(date -u +%H:%M:%S)"
  echo "$LINE"
  echo "$LINE" > "$LOGD/ep$ep.done"
done
echo BATCH_DONE
