#!/bin/bash
# Recipe-test launches (2026-10-29; arms A/B/C launched that night, D pending budget). Source this file in the repo root, then call one launch_* function.
# Prerequisites: SHA = a pushed commit that contains flashchord_conf/embodiment/sharpa_hands_mid_bd2.yaml,
# flashchord_conf/embodiment/sharpa_hands_kp100.yaml (and tools/ckpt_meta.py); OFFER from `ops/vast.sh offers`;
# a `planned` ledger line per box (python3 ops/ledger.py add planned <run_id> <usd> "<purpose>").
SNAP=pt2.11-cu130-py313-20261020

# ---------- grasp-lock arms A / B / C: one box per arm, three trainings run one after another ----------
# g EP RUN BASE "PULL_SUB" SPLIT SEED: pull only that episode's stored reference, check it is complete (else skip the
# episode: glock_public.sh would silently REBUILD a different reference), then train on it with REUSE_REF=1.
read -r -d '' GLOCK_COMMON <<'EOF'
export REUSE_REF=1 SF=1 REPLAN=0 EVOLVE=1 CURVE_REP=3 NREP=5 LIB=/content/v2d-track3/meshes/library_v3
export GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
g() {
  PULL_SUB="$4" bash ops/box/store.sh pull-run $2 >> /content/prepull.log 2>&1
  if ls /content/refs/glockt/ep$1/processed/*/*/ref_gl_ilc.parquet /content/results/glock_public/ep$1/rest_check.json \
        /content/refs/sf/ep$1/assets/urdf > /dev/null 2>&1; then
    SPLIT=$5 SEED=$6 PULL_SUB="$4" PAIRS="$1:$2:$3" bash ops/jobs/glock_public.sh
  else
    echo "[$(date -u +%FT%TZ)] recipe arm: ep$1 stored reference from $2 incomplete; episode skipped" >> /content/job.log
  fi
}
g 12 20261024-ev2-2c1e4dd mc "refs/perc2mc/ep12 refs/sf/ep12 refs/glockt/ep12 results/glock_public/ep12" public 42
g 32 20261026-fr32s46b-5e0e100 mck "refs/perc2mck/ep32 refs/sf/ep32 refs/glockt/ep32 results/glock_public/ep32" eval 46
g 33 20261026-fr3233s43-6a8a0e2 mck "refs/perc2mck/ep33 refs/sf/ep33 refs/glockt/ep33 results/glock_public/ep33" eval 43
for c in /content/results/glock_public/ep*/best/policy.safetensors; do
  /content/v2d/robotic_grounding/flash_chord/.venv/bin/python tools/ckpt_meta.py $c
done > /content/results/glock_public/ckpt_meta.txt 2>&1
EOF

JOB_A="$GLOCK_COMMON"                                   # A: control, the frozen recipe as packed
JOB_B="export CURR_SCALE=0.4
$GLOCK_COMMON"                                          # B: curriculum thresholds x 0.4 (VOC 0 from 49.2M of 70M)
read -r -d '' C_PRE <<'EOF'
cp flashchord_conf/embodiment/sharpa_hands_mid_bd2.yaml /content/v2d/robotic_grounding/flash_chord/src/flash_chord/configs/embodiment/ || exit 1
export TRAIN_ARGS=embodiment=sharpa_hands_mid_bd2
EOF
read -r -d '' C_DIAG <<'EOF'
# GT-free confound check: zero-action replay of each reused reference (its ILC lead was tuned at kd 6) under kd 6 and kd 2
for e in 12 32 33; do
  R=$(ls /content/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1); [ -n "$R" ] || continue
  N=$(python -c "import sys, numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table(sys.argv[1]).column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))" $R)
  for m in sharpa_hands_mid sharpa_hands_mid_bd2; do for i in 1 2; do
    Z=/content/results/glock_public/ep$e/zero_${m}_r$i
    ( cd /content/v2d/robotic_grounding/flash_chord && EMB=$m DEV=cuda .venv/bin/python /content/v2d-track3/tools/trace_rollout.py zero $Z.npz $R $N ) > $Z.log 2>&1
    python tools/trace_score.py $R $Z.npz:zero_action > $Z.txt 2>&1
  done; done
done
EOF
JOB_C="$C_PRE
$GLOCK_COMMON
$C_DIAG"                                                # C: ball-wrist kd 6 -> 2

launch_A() { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-rcA-${SHA:0:7} "$JOB_A"; }
launch_B() { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-rcB-${SHA:0:7} "$JOB_B"; }
launch_C() { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-rcC-${SHA:0:7} "$JOB_C"; }

# ---------- arm D: standard learner (std_learner.sh's hard_ab environment), kp 100 vs kp 25, sequential trainings ----------
read -r -d '' STD_COMMON <<'EOF'
. /content/v2d-track3/ops/box/lib.sh
cp flashchord_conf/embodiment/sharpa_hands_kp100.yaml /content/v2d/robotic_grounding/flash_chord/src/flash_chord/configs/embodiment/ || exit 1
export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 CR=0 BASE_EVAL=0 NREP=5 SEED=42 \
       LIB=/content/v2d-track3/meshes/library_v3 PDIR_ROOT=/content/perc2
KP100="embodiment=sharpa_hands_kp100 action.wrist_kp=100.0 action.wrist_tau_max=100.0"
EOF
# D-pub2: public ep2 (twin of eval 1), stored reference built 24 Oct by the eval path (glock_public 2:new:mck)
JOB_DP2="$STD_COMMON
export SPLIT=public PULL_SUB=\"refs/perc2mck/ep2 perc2/ep2\" PAIRS=\"2:20261024-e3-e49e83d:mck\"
SUF=s TRAIN_ARGS=\"\$FDR_TRAIN_ARGS\" bash ops/jobs/hard_ab.sh
SUF=s100 TRAIN_ARGS=\"\$FDR_TRAIN_ARGS \$KP100\" bash ops/jobs/hard_ab.sh"
# D-pub27: public ep27 (twin of eval 28), reference rebuilt here by the eval path (the stored ep27 mck is a 22 Oct
# contact-retarget of the 21 Oct mc, without rest settling and on perc2m perception)
read -r -d '' DP27_BUILD <<'EOF'
export MESH_DIR=/content/v2d-track3/meshes/library_v3 ASSETS=/content/assets
python pipeline/make_assets.py $MESH_DIR $ASSETS >> /content/ref_ep27.log 2>&1 || exit 1
ensure_gdino /content/job.log
bash ops/box/store.sh pull-depth 27 public >> /content/ref_ep27.log 2>&1
( export VARIANT=mck MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STEPS=0 STOP_AFTER=reference \
    SPLIT=public PERC=perc2; bash pipeline/pipeline_ep.sh 27 ) >> /content/ref_ep27.log 2>&1 || exit 1
export SPLIT=public PAIRS="27:local:mck"
SUF=s TRAIN_ARGS="$FDR_TRAIN_ARGS" bash ops/jobs/hard_ab.sh
SUF=s100 TRAIN_ARGS="$FDR_TRAIN_ARGS $KP100" bash ops/jobs/hard_ab.sh
EOF
JOB_DP27="$STD_COMMON
$DP27_BUILD"
# D-eval: evals 1 and 28 at kp 100 on the references their packed standard-learner policies trained on (std0116 /
# std1928 pulled 20261024-pack-31ef267); the kp-25 control is those runs (same code path, seed 42)
JOB_DE="$STD_COMMON
export SPLIT=eval SUF=s100 PULL_SUB=\"refs/perc2mck/ep1 perc2/ep1 refs/perc2mck/ep28 perc2/ep28\" PAIRS=\"1:20261024-pack-31ef267:mck 28:20261024-pack-31ef267:mck\"
TRAIN_ARGS=\"\$FDR_TRAIN_ARGS \$KP100\" bash ops/jobs/hard_ab.sh"

launch_DP2()  { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-kp2-${SHA:0:7} "$JOB_DP2"; }
launch_DP27() { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-kp27-${SHA:0:7} "$JOB_DP27"; }
launch_DE()   { ops/vast.sh V2D_COMMIT=$SHA ENV_SNAPSHOT=$SNAP create $1 $(date -u +%Y%m%d)-kpE-${SHA:0:7} "$JOB_DE"; }
