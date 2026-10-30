#!/bin/bash
# Batch-2 generative probe (2026-10-29): the box's own job is a BOUNDED idle shell; installs and runs are driven
# through `ops/vast.sh exec` (box_setup.sh, gen_*.py). Run with SETUP=none.
#  - makes sure the hf CLI exists (tunnel.sh publishes the exec access record with it) and republishes the record if
#    tunnel.sh could not;
#  - then waits until /content/STOP exists or IDLE_MIN minutes have passed (default 240), and exits 0 either way, so
#    run_job.sh pushes /content/results to the HF store and self-destroys at once (no failure hold).
. /content/v2d-track3/ops/box/lib.sh
command -v hf > /dev/null || pip install -q "huggingface_hub>=0.34" > /dev/null 2>&1
log "hf: $(command -v hf || echo MISSING)"
for i in $(seq 90); do
  grep -q TUNNEL-OK /content/tunnel.log 2> /dev/null && break
  grep -q "access upload FAILED" /content/tunnel.log 2> /dev/null && break
  sleep 2
done
if ! grep -q TUNNEL-OK /content/tunnel.log 2> /dev/null && [ -s /root/rexec_access.json ]; then
  hf upload "$HF_STORE" /root/rexec_access.json access/${RUN_ID}.json --repo-type dataset \
    --commit-message "access $RUN_ID" > /dev/null && log "access record republished" || log "access record upload FAILED"
fi
mkdir -p /content/results/gen
log "idle shell: until /content/STOP or ${IDLE_MIN:-240} min"
timeout $(( ${IDLE_MIN:-240} * 60 )) bash -c 'while [ ! -f /content/STOP ]; do date -u +%FT%TZ; sleep 120; done' || true
log "box job ends (STOP or the idle limit)"
