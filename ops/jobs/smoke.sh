#!/bin/bash
# Box 0: plumbing smoke test on the cheapest GPU offer (launch with SETUP=none; ~10-15 min, well under $0.10).
# Checks what every unattended run depends on, except the GPU software stack: env-var injection, repo checkout,
# HF public download speed, HF store write, instance label; then run_job.sh saves and self-destroys (the destroy
# test). The agent tries SSH from its own session during the hold at the end. Written 2026-10-20, not yet run.
. /content/v2d-track3/ops/box/lib.sh
have=""; miss=""
for v in HF_TOKEN GH_TOKEN HF_STORE CONTAINER_ID CONTAINER_API_KEY RUN_ID V2D_COMMIT V2D_IMAGE; do
  [ -n "${!v:-}" ] && have="$have $v" || miss="$miss $v"
done
log "env present:$have"; log "env MISSING:${miss:- none}"
log "commit $(git -C $REPO_DIR rev-parse HEAD); python $(python3 -V 2>&1); hf $(command -v hf || echo MISSING)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; nproc; free -g | head -2; df -h /workspace
label "smoke: label set from the box"
t=$(date +%s)
hf download nvidia/video_to_data_challenge --repo-type dataset --include 'track_3/evaluation/*' \
  --local-dir /content/hfds_smoke > /dev/null && log "HF public download of 0.69 GB took $(( $(date +%s) - t )) s"
mkdir -p /content/results/smoke && date -u > /content/results/smoke/hello.txt
bash $OPS/store.sh push-run && log "HF-WRITE-OK"
log "holding ${SMOKE_HOLD_MIN:-8} min for the agent's SSH test (create /content/HOLD with an epoch time to keep the box)"
sleep $(( ${SMOKE_HOLD_MIN:-8} * 60 ))
log "smoke done; run_job.sh now saves and self-destroys"
