#!/bin/bash
# Standard learner on an eval episode's stored reference with a carved simulator collision copy (2026-10-26;
# pipeline/interaction_carve.py; for eval 25 the board slots, meshes/carve/ev25, CPU-tested in the proxy and in
# FlashCHORD's own physics: docs/work-log.md 26 Oct). Everything else is the recipe of the stored run (eval_both.sh step 3:
# FDR + VOC + deployment-exact starts 0.25, 250M steps, checkpoint sweep, NREP official evaluations of the chosen one):
#   pull only SRC_RUN's refs/perc2mck/ep<EP> and perc2/ep<EP> (the reference the pieces were carved from; mcks is a
#   byte copy of mck with CR=0), build /content/assets with --pieces, train and evaluate with hard_ab.sh.
# The submitted mesh is unchanged; only the simulator's collision shapes differ. No ground truth is read.
# Usage: ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> \
#          'EP=25 SRC_RUN=20261025-ev25idfix-02de0c7 SEED=42 bash ops/jobs/carve_rerun.sh'
# Output: /content/results/hard_ab/ep<EP>/mcks-s<SEED>/summary.json (sim_vs_ref per rollout), checkpoints under runs/.
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; EP=${EP:?EP missing}; SRC=${SRC_RUN:?SRC_RUN missing}; SEED=${SEED:-42}; NREP=${NREP:-5}
LIB=${LIB:-$REPO_DIR/meshes/library_v3}; PIECES=${PIECES:-$REPO_DIR/meshes/carve/ev$EP}
[ -d $PIECES ] || { log "carve_rerun: no pieces $PIECES" >> $J; exit 1; }
log "carve_rerun code $(git -C $REPO_DIR rev-parse --short HEAD), episode $EP from $SRC, seed $SEED, pieces $PIECES, LIB $LIB" >> $J
label "carve_rerun ep$EP s$SEED"
export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
PULL_SUB="refs/perc2mck/ep$EP perc2/ep$EP" SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=$NREP SEED=$SEED \
  LIB=$LIB PIECES=$PIECES PAIRS="$EP:$SRC:mck" bash $REPO_DIR/ops/jobs/hard_ab.sh
s=/content/results/hard_ab/ep$EP/mcks-s$SEED/summary.json
log "carve_rerun ep$EP s$SEED: $([ -s $s ] && python -c "import json; d=json.load(open('$s')); print('n', d['n'], 'sim_vs_ref', d.get('sim_vs_ref'), 'checkpoint', d['checkpoint'])" || echo 'NO summary')" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
