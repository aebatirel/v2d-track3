#!/bin/bash
# Eval run (2026-10-24 proposal; started only on the owner's go-ahead). Every eval episode goes through the SAME automatic
# pipeline; no ground truth exists or is read, no decision is taken by hand per episode:
#   1. reference from the eval videos, built once and shared: perception (perc2, our mesh library LIB), hands, mkref
#      (wrist cost 3.0), contact retargeting with rest settling (variant mck);
#   2. learner A, grasp-lock fine-tune (glock_public.sh SPLIT=eval): support fill (SF), grasp lock (GL_ARGS, early
#      approach 15 cm), re-plan against the simulated start (REPLAN, kept only if the zero-action replay improves), wrist
#      ILC + kp 400 wrist, FDR rewards + VOC fix, 70M steps; every checkpoint scored with CURVE_REP official evaluations,
#      NREP evaluations of the chosen one;
#   3. learner B, standard FDR RL on the same reference (hard_ab.sh SPLIT=eval, the recipe of public ep18 0.889 / 0.776):
#      FDR + VOC + deployment-exact starts 0.25, 250M steps, checkpoint sweep, NREP evaluations of the chosen one; it runs
#      for an episode only when learner A's mean sim_vs_ref is below GATE (default 0.9: on the public twins every
#      episode the standard RL won had grasp-lock below 0.9; GATE=2 trains both everywhere);
#   4. tools/choose_learner.py: the learner whose official rollouts track the perceived reference best (mean sim_vs_ref
#      over its NREP rollouts, all scored against the same perceived object trajectory) is the episode's policy:
#      results/final_eval/ep<N>/{policy.safetensors,choice.json} and results/final_eval/checkpoints.json for
#      ops/jobs/submit_pack.sh.
# Usage: ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'EPS="3 5" bash ops/jobs/eval_both.sh'
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; EPS=${EPS:?EPS (eval episodes) missing}; NREP=${NREP:-5}; GATE=${GATE:-0.9}; SEED=${SEED:-42}
LIB=${LIB:-$REPO_DIR/meshes/library_v3}; KIT=${KIT:-/content/kit/v2d_submission_kit}
GL_ARGS=${GL_ARGS:-"--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"}
F=/content/results/final_eval; G=/content/results/glock_public; H=/content/results/hard_ab; mkdir -p $F
log "eval_both code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], LIB $LIB, NREP $NREP, GATE $GATE, seed $SEED" >> $J
ensure_gdino $J                                                  # detection grounding term (the spoon fix, pipeline/det_rules.py)
for e in $EPS; do bash $OPS/store.sh pull-depth $e eval > /dev/null 2>&1 || true; done   # cached eval depth if stored
# 1 + 2: references and the grasp-lock learner
SPLIT=eval PAIRS="$(for e in $EPS; do printf '%s:new:mck ' $e; done)" LIB=$LIB NREP=$NREP SEED=$SEED CURVE_REP=${CURVE_REP:-3} \
  REPLAN=${REPLAN:-1} SF=${SF:-1} GL_ARGS="$GL_ARGS" bash $REPO_DIR/ops/jobs/glock_public.sh
mean() { python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref']['mean'])" $1 2> /dev/null; }
# 3: the standard learner where the grasp lock does not track well (or failed)
B=""
for e in $EPS; do
  m=$(mean $G/ep$e/best/summary.json)
  if [ -z "$m" ] || python -c "import sys; sys.exit(0 if $m < $GATE else 1)"; then B="$B $e:local:mck"; fi
  log "eval_both ep$e: grasp-lock mean sim_vs_ref ${m:-none} (gate $GATE)" >> $J
done
if [ -n "$B" ]; then
  ( export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
    SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=$NREP SEED=$SEED LIB=$LIB PAIRS="${B# }" \
      bash $REPO_DIR/ops/jobs/hard_ab.sh )
fi
# 4: one choice per episode
for e in $EPS; do
  c=(); y=""
  s=$H/ep$e/mcks-s$SEED
  if [ -s $s/summary.json ]; then
    c+=(--cand "std:$s:$(python -c "import json; print(json.load(open('$s/summary.json'))['checkpoint'])")"); y="--yardstick $s"
  fi
  [ -s $G/ep$e/best/summary.json ] && c+=(--cand "glock:$G/ep$e/best:$(python -c "import json; print(json.load(open('$G/ep$e/best/summary.json'))['checkpoint'])")")
  [ ${#c[@]} -gt 0 ] || { log "eval_both ep$e: NO candidate" >> $J; continue; }
  KIT=$KIT python $REPO_DIR/tools/choose_learner.py $F $e "${c[@]}" $y > $F/choose_ep$e.log 2>&1 \
    && log "eval_both ep$e: $(tail -1 $F/choose_ep$e.log)" >> $J || log "eval_both ep$e: choice FAILED ($(tail -2 $F/choose_ep$e.log | tr '\n' ' ' | cut -c1-200))" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
