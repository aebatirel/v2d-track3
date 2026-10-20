#!/bin/bash
# GPU-box main, started by onstart.sh (log: /workspace/run_job.log). Written 2026-10-20, not yet run on Vast.
#   environment (snapshot restore, else full setup) -> dataset -> job -> save to the HF store -> self-destroy.
# The job command comes base64-encoded in JOB_B64 and runs from the repo root, e.g.
#   'STEPS=250003456 bash pipeline/pipeline_ep.sh 12'
set -u
. /content/v2d-track3/ops/box/lib.sh
JOB=$(echo "${JOB_B64:-}" | base64 -d)
t0=$(date +%s)
log "run ${RUN_ID:-?}: job [$JOB] commit $(git -C $REPO_DIR rev-parse HEAD) instance ${CONTAINER_ID:-?}"
log "gpu: $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1)  cpus: $(nproc)" \
    " ram: $(free -g | awk '/Mem/{print $2}') GB  disk free: $(df -h /workspace | awk 'NR==2{print $4}')"
setsid nohup bash $OPS/watchdog.sh >> /content/watchdog.log 2>&1 < /dev/null &
[ "${REXEC:-1}" = 0 ] || setsid nohup bash $OPS/tunnel.sh >> /content/tunnel.log 2>&1 < /dev/null &   # HTTPS shell

label "setup"
if [ "${SETUP:-}" = none ]; then
  log "SETUP=none: skipping environment and data setup"
elif [ -n "${ENV_SNAPSHOT:-}" ] && bash $OPS/store.sh restore-env "$ENV_SNAPSHOT" >> /content/setup.log 2>&1; then
  log "environment restored from $ENV_SNAPSHOT"
  bash $REPO_DIR/pipeline/fetch_data.sh >> /content/setup.log 2>&1
else
  [ -n "${ENV_SNAPSHOT:-}" ] && log "snapshot restore FAILED; running the full setup"
  bash $REPO_DIR/pipeline/setup.sh >> /content/setup.log 2>&1
fi
log "setup took $(( ($(date +%s) - t0) / 60 )) min: $(grep -aoE '[A-Z0-9]+-(OK|FAIL)' /content/setup.log | sort -u | tr '\n' ' ')"

if [ -n "${RESUME_FROM:-}" ]; then
  bash $OPS/store.sh pull-run "$RESUME_FROM" && log "outputs of $RESUME_FROM restored; finished stages are skipped" \
    || log "pull-run $RESUME_FROM FAILED"
fi
label "job running"
(cd $REPO_DIR && bash -c "$JOB") > /content/job.log 2>&1
rc=$?
echo $rc > $ST/exit_code
log "job exit $rc after $(( ($(date +%s) - t0) / 60 )) min total"
touch $ST/done
if held; then touch $ST/held_exit; label "done rc=$rc, on HOLD"; log "HOLD set: the watchdog destroys when it expires"; exit 0; fi
self_destroy "job finished rc=$rc"
