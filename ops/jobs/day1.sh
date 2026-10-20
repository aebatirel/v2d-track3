#!/bin/bash
# Box 1 (first RTX PRO 6000): STATUS.md next actions 2-3 in one unattended job. Written 2026-10-20, not yet run.
#   1. mirror the FoundationStereo/FoundationPose weights to the HF store if they came from Google Drive
#   2. perc2 perception on public episode 12; push its depth cache
#   3. environment snapshot to the HF store, in the background (CPU, disk and network only)
#   4. resume test: 15M-step training, killed after the 10M checkpoint, rerun -> must resume, not restart
#   5. two full trainings on the one GPU at once (two-jobs test): ep12 with perc2 objects and with the mocap oracle,
#      each followed by the official evaluator and score_sim.py
# Every stage writes a timestamped line to job.log and its own log; push-run saves everything at the end.
. /content/v2d-track3/ops/box/lib.sh
EP=${EP:-12}; P=$REPO_DIR/pipeline
SNAP=${SNAP_NAME:-pt2.11-cu130-py313-$(date -u +%Y%m%d)}

label "day1: weights"
if [ -n "${HF_STORE:-}" ] && ! grep -aq WEIGHTS-MIRROR-OK /content/setup.log; then
  bash $OPS/store.sh mirror-weights && log "weights mirrored to the store" || log "weight mirror FAILED"
fi

label "day1: perception ep$EP"
PERC=perc2 STEPS=0 STOP_AFTER=perception bash $P/pipeline_ep.sh $EP || { log "perception FAILED"; exit 1; }
cp /content/perc2/ep$EP/result.json /content/results/perc2_ep${EP}_result.json 2> /dev/null
bash $OPS/store.sh push-depth $EP public && log "depth cache pushed"

label "day1: snapshot + resume test"
(bash $OPS/store.sh snapshot-env $SNAP > /content/snapshot.log 2>&1 && log "snapshot env/$SNAP uploaded" \
   || log "snapshot FAILED (see snapshot.log)") &

# resume test: kill the first attempt once a checkpoint at >= 10M steps exists, then rerun the same command
RT="PERC=perc2 SEED=7 STEPS=15007744"            # a multiple of the 4096 worlds
RUN=/content/runs/perc2/ep$EP-s7
(eval "$RT bash $P/pipeline_ep.sh $EP" > /content/resume_a.log 2>&1) &
RA=$!
step() { ls -v $RUN/state_*.safetensors 2> /dev/null | tail -1 | grep -oE '[0-9]+' | tail -1; }
for i in $(seq 1 240); do                         # up to 40 min (setup of the first training includes JIT compiles)
  [ "$(step || echo 0)" -ge 10000000 ] 2> /dev/null && break
  kill -0 $RA 2> /dev/null || break
  sleep 10
done
if [ "$(step || echo 0)" -ge 10000000 ] 2> /dev/null; then
  pkill -f "output_dir=$RUN" && log "resume test: killed training after checkpoint $(step)"
  wait $RA; sleep 5
  eval "$RT bash $P/pipeline_ep.sh $EP" > /content/resume_b.log 2>&1
  grep -aq "resuming from" /content/resume_b.log && [ -e $RUN/.done ] \
    && log "RESUME-OK: $(grep -a 'resuming from' /content/resume_b.log)" || log "RESUME-FAIL (see resume_b.log, $RUN/train.log)"
else
  log "RESUME-TEST-SKIPPED: no 10M checkpoint (see resume_a.log, $RUN/train.log)"; kill $RA 2> /dev/null
fi

label "day1: two trainings ep$EP"
PERC=perc2  bash $P/pipeline_ep.sh $EP > /content/pipe_perc2_ep$EP.log 2>&1 &
sleep 120                                                              # stagger the JIT compiles
PERC=oracle bash $P/pipeline_ep.sh $EP > /content/pipe_oracle_ep$EP.log 2>&1 &
wait
log "perc2:  $(tail -3 /content/pipe_perc2_ep$EP.log | tr '\n' ' ')"
log "oracle: $(tail -3 /content/pipe_oracle_ep$EP.log | tr '\n' ' ')"
grep -ah "steps/s\|env steps\|environment steps" /content/runs/*/ep$EP-s42/train.log | tail -4
