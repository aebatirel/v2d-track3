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
