#!/bin/bash
# GPU batch G0 (module M18 of SPEC section 7; build step B3; PREREG B.12; SPEC section 18): SAM 3D Objects with our
# metric depth as the pointmap on the ep2 lid and pot views that gmg/tools/g0_inputs.py prepared on the CPU (B.11
# passed there on the clean ep2 bundle before any input was written), seeds 0 and 1, plus the report-only contact-frame
# controls. Started by ops/box/run_job.sh with SETUP=none (run_job.sh gives the stall watchdog, the push of
# /content/results to the HF store runs/<RUN_ID>/ and the self-destroy; ops/box/lib.sh). Steps:
#   1. hf CLI; inputs from the store runs/<RUN_ID>/inputs/ (uploaded by the agent before the launch), sha256 check
#   2. env C + weights (gmg/jobs/g0_setup.sh)
#   3. gmg/jobs/g0_sam3d.py -> /content/results/g0/sam3d/
#   4. exit 0 when every job and seed has an ok record, else 1 (run_job.sh then holds FAIL_HOLD_MIN for debugging)
# Inputs never include scans, mocap, parquet poses or library meshes; the box only sees our RGB frames, masks and
# depth pointmaps. Usage (box job): bash docs/research/mesh-2026-10-26/gmg/jobs/gmg_g0.sh
. /content/v2d-track3/ops/box/lib.sh
set -u
G=$REPO_DIR/docs/research/mesh-2026-10-26/gmg/jobs
R=/content/results/g0; IN=/content/g0in; mkdir -p $R $IN
J=$R/g0_job.log
exec >> $J 2>&1
log "G0 job start: run ${RUN_ID:-?} commit $(git -C $REPO_DIR rev-parse HEAD)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
command -v hf > /dev/null || /venv/main/bin/python -m pip install -q "huggingface_hub>=0.34"
export PATH=/venv/main/bin:$PATH HF_HUB_DISABLE_PROGRESS_BARS=1
# the exec tunnel (ops/box/tunnel.sh) publishes its access record with the hf CLI, which this image may lack at that
# moment: republish it once hf exists (as gen/box_job.sh did), so `ops/vast.sh exec` works for debugging
for i in $(seq 90); do
  grep -q -e TUNNEL-OK -e "access upload FAILED" -e "no quick-tunnel" /content/tunnel.log 2> /dev/null && break; sleep 2
done
if ! grep -q TUNNEL-OK /content/tunnel.log 2> /dev/null && [ -s /root/rexec_access.json ]; then
  hf upload "$HF_STORE" /root/rexec_access.json access/${RUN_ID}.json --repo-type dataset \
    --commit-message "access $RUN_ID" > /dev/null && log "access record republished" || log "access record upload FAILED"
fi
label "G0: inputs"
# python allow_patterns, not the CLI's --include (the 29 Oct probe saw the CLI drop its first --include pattern; a
# dropped pattern here would mean the whole store)
for i in 1 2 3 4; do
  /venv/main/bin/python -c "import sys; from huggingface_hub import snapshot_download as s
s(sys.argv[1], repo_type='dataset', local_dir=sys.argv[2], allow_patterns=[f'runs/{sys.argv[3]}/inputs/*'])" \
    "$HF_STORE" $IN "$RUN_ID" > /dev/null 2>&1 && break
  log "inputs download retry $i"; sleep $((i * 15))
done
D=$IN/runs/$RUN_ID/inputs
[ -s $D/jobs.json ] || { log "G0-INPUTS-FAIL: no jobs.json"; exit 1; }
(cd $D && sha256sum -c --quiet SHA256SUMS) && log "G0-INPUTS-OK $(ls $D | wc -l) files" || { log "G0-INPUTS-SHA-FAIL"; exit 1; }
cp $D/jobs.json $D/SHA256SUMS $R/
label "G0: setup env C"
bash $G/g0_setup.sh $R/setup.log || { log "G0-SETUP-FAIL: $(grep -aoE 'C-[A-Z0-9-]+(FAIL|INCOMPLETE)[^ ]*' $R/setup.log | sort -u | tr '\n' ' ')"; exit 1; }
log "G0-SETUP-OK: $(grep -aoE 'C-[A-Z0-9-]+-(OK|FAIL)' $R/setup.log | sort -u | tr '\n' ' ')"
label "G0: SAM 3D runs"
CK=/content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
# third-party code runs without the store token, the GitHub token or the instance key (subshell only)
(unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
 cd /content/ext/sam-3d-objects && /content/genv3/bin/python $G/g0_sam3d.py --ckpt $CK/pipeline.yaml --inputs $D \
  --out $R/sam3d) > $R/sam3d.log 2>&1
rc=$?
grep -E '^\{' $R/sam3d.log | tail -20
N=$(python3 -c "import json; print(sum(len(j['seeds']) for j in json.load(open('$D/jobs.json'))))")
OK=$(grep -c '"ok": true' $R/sam3d/gen_log.jsonl 2> /dev/null || echo 0)
log "G0 SAM 3D: rc $rc, ok records $OK of $N"
[ "$OK" -ge "$N" ] && { log "G0-DONE"; exit 0; }
log "G0-INCOMPLETE"; exit 1
