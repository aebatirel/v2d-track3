# Shared helpers for the GPU-box scripts (source this file). Written 2026-10-20, not yet run on Vast.
. /etc/v2d_env 2> /dev/null || true
[ -f /venv/main/bin/activate ] && . /venv/main/bin/activate      # vastai/pytorch images keep python here
export REPO_DIR=/content/v2d-track3 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
OPS=$REPO_DIR/ops/box; ST=/content/run_state; mkdir -p $ST
VI=https://console.vast.ai/api/v0/instances/${CONTAINER_ID:-0}/
AH="Authorization: Bearer ${CONTAINER_API_KEY:-}"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

label() {  # show the stage in the Vast instance list, so the agent can follow without SSH
  curl -s -m 20 -X PUT -H "$AH" -H 'Content-Type: application/json' \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"label": sys.argv[1][:120]}))' "${RUN_ID:-?} $*")" $VI > /dev/null || true
}

held() {  # /content/HOLD holds an epoch time; until then nothing self-destroys (interactive debugging)
  [ -f /content/HOLD ] && [ "$(cat /content/HOLD 2> /dev/null || echo 0)" -gt "$(date +%s)" ]
}

self_destroy() {  # $1 = reason. Save what exists first (CLAUDE.md), then destroy this instance.
  mkdir $ST/destroying 2> /dev/null || { log "self-destroy already in progress"; return 0; }   # one at a time
  log "self-destroy: $1"; label "saving, then destroy: $1"
  if ! bash $OPS/store.sh push-run; then
    label "PUSH-FAILED, destroying in 60 min unless HOLD: $1"; log "push failed; waiting 60 min for the agent"
    sleep 3600; held && { rmdir $ST/destroying; return 0; }
    bash $OPS/store.sh push-run || log "push failed again; destroying anyway"
  fi
  for i in 1 2 3; do
    curl -sf -m 30 -X DELETE -H "$AH" $VI && { log "destroy requested"; return 0; }
    sleep 10
  done
  label "DESTROY-FAILED: $1"; log "DESTROY FAILED: the agent must destroy instance ${CONTAINER_ID:-?}"
}

# FlashDexRetarget-style training rewards (2026-10-23 A/B, results/e2e/fdr_20261023: four-run mean 0.830 vs 0.753).
# FDR=1 (the default since the owner's decision, 2026-10-23; FDR=0 for stock FlashCHORD) sets the reward flags and the
# training overrides; fc_patches applies the opt-in FlashCHORD patches that the
# environment asks for (ops/box/patch_flashchord.py, ops/box/patch_flashchord_fdr.py). $1 = job log.
FDR_TRAIN_ARGS="curriculum=tracking_250m_mixed_reset_v2d objective.force_closure.enabled=true objective.force_closure.weight=6 objective.contact_wrench_support.weight=3 objective.unintended_contact.weight=-2"
fc_patches() {
  local J=$1 FCD=/content/v2d/robotic_grounding/flash_chord
  if [ "${FDR:-1}" = 1 ]; then                              # default since 2026-10-23 (owner); FDR=0 = stock rewards
    export FC_FDR_OBJ=${FC_FDR_OBJ:-1} FC_FDR_TIPS=${FC_FDR_TIPS:-1} TRAIN_ARGS="$FDR_TRAIN_ARGS ${TRAIN_ARGS:-}"
  fi
  if [ -n "${FC_OBJECT_KEYPOINT_SCALE:-}${FC_IMMEDIATE_FIRST_FRAME:-}" ]; then
    python $REPO_DIR/ops/box/patch_flashchord.py $FCD >> $J 2>&1 || { log "FlashCHORD patch FAILED" >> $J; return 1; }
    log "patched FlashCHORD: object keypoints ${FC_OBJECT_KEYPOINT_SCALE:-1} m, deployment-exact starts p ${FC_IMMEDIATE_FIRST_FRAME:-0}" >> $J
  fi
  if [ -n "${FC_FDR_OBJ:-}${FC_FDR_TIPS:-}" ]; then
    python $REPO_DIR/ops/box/patch_flashchord_fdr.py $FCD >> $J 2>&1 || { log "FlashCHORD FDR patch FAILED" >> $J; return 1; }
    export FC_FDR_OBJ FC_FDR_TIPS TRAIN_ARGS
    log "patched FlashCHORD (FDR rewards): object points ${FC_FDR_OBJ:-0}, fingertip bound ${FC_FDR_TIPS:-0}; TRAIN_ARGS [${TRAIN_ARGS:-}]" >> $J
  fi
}
