#!/bin/bash
# Second learner on STORED eval references (owner go-ahead 2026-10-25: "use both", rule fixed beforehand). For each
# EP:RUN:mck in PAIRS (RUN holds the episode's perception perc2/ep<N> and reference refs/perc2mck/ep<N>), train the
# standard FDR RL on that reference (hard_ab.sh SPLIT=eval: FDR + VOC + deployment-exact starts 0.25, 250M, checkpoint
# sweep, NREP official evaluations; the recipe of public ep18 0.889 / 0.776 and ep39 0.802), then tools/choose_learner.py
# keeps, per episode, the learner whose official rollouts track our perceived reference best (mean sim_vs_ref over the
# repeats), against the episode's chosen grasp-lock policy GL="EP:RUN ..." (its rollouts in
# runs/<RUN>/results/glock_public/ep<N>/best/r*). No ground truth exists or is read.
#   ops/vast.sh create <offer> <run> 'PAIRS="19:20261024-pack-31ef267:mck 1:20261024-pack-31ef267:mck" \
#       GL="19:20261024-seed43-61101f5 1:20261024-pack-31ef267" bash ops/jobs/std_learner.sh'
# Output: /content/results/hard_ab/ep<N>/mcks-s42 (the standard learner), /content/results/final_eval/ep<N>/choice.json
# and /content/results/final_eval/checkpoints.json.
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; NREP=${NREP:-5}; SEED=${SEED:-42}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
KIT=${KIT:-/content/kit/v2d_submission_kit}; F=/content/results/final_eval; H=/content/results/hard_ab; mkdir -p $F
log "std_learner code $(git -C $REPO_DIR rev-parse --short HEAD), pairs [${PAIRS:?}], grasp-lock [${GL:?}], LIB $LIB" >> $J
( export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
  SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=$NREP SEED=$SEED LIB=$LIB PAIRS="$PAIRS" \
    bash $REPO_DIR/ops/jobs/hard_ab.sh )
for x in $GL; do
  e=${x%%:*}; r=${x#*:}; d=/content/gl/$r
  hf download "$HF_STORE" --repo-type dataset --include "runs/$r/results/glock_public/ep$e/best/*" --local-dir $d > /dev/null 2>&1 \
    || log "std_learner ep$e: grasp-lock rollouts of $r: download FAILED" >> $J
  g=$d/runs/$r/results/glock_public/ep$e/best; s=$H/ep$e/mcks-s$SEED; c=(); y=""
  if [ -s $s/summary.json ]; then
    c+=(--cand "std:$s:$(python -c "import json; print(json.load(open('$s/summary.json'))['checkpoint'])")"); y="--yardstick $s"
  fi
  [ -s $g/summary.json ] && c+=(--cand "glock:$g:$g/policy.safetensors")
  [ ${#c[@]} -gt 0 ] || { log "std_learner ep$e: NO candidate" >> $J; continue; }
  KIT=$KIT python $REPO_DIR/tools/choose_learner.py $F $e "${c[@]}" $y > $F/choose_ep$e.log 2>&1 \
    && log "std_learner ep$e: $(tail -1 $F/choose_ep$e.log)" >> $J \
    || log "std_learner ep$e: choice FAILED ($(tail -2 $F/choose_ep$e.log | tr '\n' ' ' | cut -c1-200))" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
