set -u
# Container reproduce on one Vast box (Imitation.Tech, Track 3 pack 13h). Runs from the repo root via run_job.sh.
# Inputs: HF store runs/$RUN_ID/input/{submission_tree.tar.zst, install_runtime.sh, SHA256SUMS}.
O=/content/results/container_repro; I=/content/ctin; mkdir -p $O
log() { echo "[$(date -u +%FT%TZ)] ctrepro: $*"; }
log "start; gpu $(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1); cpus $(nproc)"
nvidia-smi > $O/nvidia-smi.txt 2>&1
hf download "$HF_STORE" --repo-type dataset --include "runs/$RUN_ID/input/*" --local-dir $I > /dev/null 2>&1 \
  || { log "input download FAILED"; exit 1; }
D=$I/runs/$RUN_ID/input
(cd $D && sha256sum -c SHA256SUMS) > $O/input_sha.txt 2>&1 || { log "input sha256 FAILED"; exit 1; }
zstd -q -dc $D/submission_tree.tar.zst | tar -x -C / || { log "untar FAILED"; exit 1; }
log "tree ok: $(cat $O/input_sha.txt | tr '\n' ' ')"
env -u VIRTUAL_ENV PATH=/opt/instance-tools/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  PREFIX=/opt bash $D/install_runtime.sh > $O/install_runtime.log 2>&1 || { log "install FAILED: $(tail -5 $O/install_runtime.log | tr '\n' ' ')"; exit 1; }
log "runtime ok: $(grep eval_code_sha256 $O/install_runtime.log | tail -1)"
cp /opt/flash_chord.venv.freeze.txt /opt/kit-venv.freeze.txt $O/ 2> /dev/null
/submission/run.sh verify --report $O/verify_box.json > $O/verify_box.log 2>&1; log "verify rc $? ($(tail -1 $O/verify_box.log))"
t0=$(date +%s)
/submission/run.sh reproduce --label track3_13h --output $O/out --parallel 4 > $O/reproduce.log 2>&1; rc=$?
log "reproduce rc $rc after $(( ($(date +%s) - t0) / 60 )) min"
/submission/run.sh verify --reproduced track3_13h=$O/out/track3_13h/track3_submission.parquet \
  --report $O/verify_repro_box.json > $O/verify_repro_box.log 2>&1
log "verify --reproduced rc $? ($(tail -1 $O/verify_repro_box.log))"
rm -rf $O/out/track3_13h/flash_chord_cache
exit $rc
