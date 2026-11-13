#!/bin/bash
# Eval-20 retrain on the b1 water-pitcher collision pieces (2026-11-01; owner's go relayed by the orchestrator, conditional on
# determined-wright's contact budget, which read clean at f59c897). PACKABLE if it passes the agreed swap rule and the pack-10
# inclusion bar: stock sim=rl contact limits (njmax 512 / nconmax 256), the PACKED eval-20 learner and recipe (grasp lock,
# glock_public.sh, as run 20261025-evb1420-ee7ba8e trained runs/glock/ep20-s42, sha256 61dcd7a6...), the PACKED reference P
# (md5 4d06d8d4) as byte copies, two seeds; the ONE changed input is the water pitcher's collision copy: the 41 b1 pieces
# (meshes/carve/ev20b1, MD5SUMS fe9aeca0..., bold-albattani 9c0bc0c / 83d18d0), applied exactly as the mesh lane specified
# and as determined-wright's budget / settle checks used them: pipeline/placement_carve.py assets on the packed
# refs/sf/ep20/assets, SF=0 (NOT make_assets.py --pieces, which would rebuild the blue cup without its 0.5 cm fill).
# Pre-registered in docs/research/work/eval20-b1-20261101/PREREG.md (written before any result); build notes BUILD.md, launch
# string and cost JOBS.txt there. EVAL episode 20: no ground truth exists or is read; every score is GT-free (vs P).
#   1. the piece set: tools/e20b1.py pieces (MD5SUMS / FROZEN.md md5 pinned; exactly water_pitcher/piece_00..40.obj),
#      tools/no_oracle.py on the folder;
#   2. the packed eval-20 inputs from the stored run (packed_refs.json pull_files / result_files: single-file pulls, no store
#      listing) and the packed checkpoint; tools/e20b1.py inputs (P md5 / fingerprint, support stage, the packed asset copy's
#      URDF / glb md5s, packed sha256);
#   3. the carve: a pristine copy of refs/sf/ep20/assets kept in /content/e20b1_in (not pushed), then placement_carve.py
#      assets refs/sf/ep20/assets meshes/carve/ev20b1 <out>, and <out> replaces refs/sf/ep20/assets (the path P names); tools/e20b1.py assets
#      (only the pitcher URDF changes, md5 77b395a5 = the lane's route-A URDF; 41 col_NN = piece_NN; visual and inertial
#      unchanged; blue cup untouched); tools/e20b1.py arms: seed copies refs/e20b1s<seed>_glockt/ep20 (byte copies of P),
#      base links, REUSE_REF records; tools/no_oracle.py on every input;
#   4. per seed (42, 43) one glock_public.sh call (REUSE_REF=1 REQUIRE_REUSE=1 EVAL_E20B1=1): 70M steps, checkpoint by
#      sim_vs_ref vs P over 3 evaluations per curve checkpoint, NREP 10 training-box evaluations;
#   5. FIRST check: tools/e10nj.py overflow per training log (nefc / broadphase / narrowphase lines; > 1,000 in a training log
#      labels the result "pieces not clean in training"); reported: the zero-action rest check of P on the b1 copy;
#   6. tools/e20b1.py cells (config = the packed checkpoint's but output_dir / task / reference / seeds, stock limits, P md5,
#      b1 URDFs, support stage, rollouts name the checkpoint), choose (pack 9b PREREG section 2), gate (>= 1 VERIFIED seed's
#      training-box mean sim_vs_ref vs P > 0.8933, the packed policy's fresh-draw mean);
#   7. only if a seed is chosen AND the gate is met: no_oracle on the chosen checkpoint, then 10 fresh official draws on the
#      pristine evaluator (ev10_cs.sh confirm(), verbatim but for names) -> results/ev20_b1/conf/r<i>;
#   8. tools/dr_score.py vs P (confirmation, the old packed draw = pack 6's eval-20 rollout, the packed policy's H5p7 eval-20
#      draws, training-box draws); tools/e20b1.py verify and verdict (the pack 9b swap rule a / b / c / s on P, the gate, the
#      binding pack-10 inclusion bar +0.02 vs P, the overflow label); one store push at the end.
# Integrity: new names only (refs/e20b1s<seed>_glock*, runs/e20b1s<seed>_glock, results/e20b1s<seed>_glock_public,
# results/ev20_b1); the stored run's files are read and never written there. This box's refs/sf/ep20/assets is the b1 copy
# (the path P names), pushed under this run id only. Run ids carry -e20b1- (refused otherwise). Nothing is packed or uploaded
# here: a pack is built on CPU after the box, only on SWAP-ELIGIBLE + inclusion; the upload stays the owner's word.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-e20b1-<sha7> 'bash ops/jobs/ev20_b1.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; G=/content/results/ev20_b1; HS=/content/hfstore; I=/content/e20b1_in
mkdir -p $G $I
case "${RUN_ID:-}" in *-e20b1-*) ;; *) log "ev20_b1: RUN_ID '${RUN_ID:-}' must contain -e20b1-" >> $J; exit 1 ;; esac
PS=ev20b1; PIECES_DIR=$REPO_DIR/meshes/carve/$PS; SRC_RUN=20261025-evb1420-ee7ba8e; EP=20; BASE=mck; PRE=e20b1; SEEDS="42 43"; NCONF=10
TAB=$REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json; A=/content/refs/sf/ep$EP/assets
# the packed eval-20 recipe (evb1420's glock_public.sh call: SF 1 REPLAN 1 EVOLVE 0, the GL_ARGS below, 70M steps, CURVE_REP 3);
# with REUSE_REF + REQUIRE_REUSE no reference stage runs, so SF (0 here, as the mesh lane asks) / REPLAN / EVOLVE / GL_ARGS are
# only logged; nothing is overridable from the job string
export SPLIT=eval LIB=$REPO_DIR/meshes/library_v3 SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 \
  STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets
export MESH_DIR=$LIB GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
unset PIECES MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME ENV_EP20 VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS \
  CONTACT_RETARGET TRAIN_LOCK CK_SWEEP EVAL_LOCAL_REF EVAL_NJ_DIAG EVAL_CS_REF EVAL_E20B1 FC_DR_PATCH FC_DR_RESET FC_DR_SEED
# (PIECES unset: /content/assets is the plain library build; P names refs/sf/ep20/assets, never /content/assets)
H5P7_RUN=20261031-h5p7-1a7cdff                                      # the packed policy's fresh draws (pack-10 comparison set)
OLD=runs/20261026-pack6-5203d42/results/submission/results/episode_000020   # the board pack's (9a+ / 9b) eval-20 rollout
CK0=runs/$SRC_RUN/results/final_eval/ep$EP/policy.safetensors       # the packed eval-20 checkpoint (= the table's)
CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit; FC=/content/v2d/robotic_grounding/flash_chord; FCV=$FC/.venv/bin/python
log "ev20_b1 code $(git -C $REPO_DIR rev-parse --short HEAD), ep $EP, piece set $PS ($PIECES_DIR), packed run $SRC_RUN, prefix $PRE, seeds [$SEEDS], LIB $LIB, NREP $NREP, NCONF $NCONF, STEPS $STEPS, SF $SF, stock sim limits, GL_ARGS [$GL_ARGS], H5P7_RUN $H5P7_RUN" >> $J

finish_verdict() {  # verify + verdict from whatever exists (also after a STOP)
  python $T/e20b1.py verify --dir $G --out $G/verify.json > $G/verify.txt 2>&1
  log "ev20_b1 verify: $(cut -c1-1500 $G/verify.txt)" >> $J
  python $T/e20b1.py verdict --dir $G $(ls $G/score.json 2> /dev/null | sed 's/^/--score /') --seeds "$SEEDS" --out $G/summary.json > $G/verdict.txt 2>&1
  log "ev20_b1 RESULT: $(cut -c1-3000 $G/verdict.txt)" >> $J; label "ev20 b1: $(cut -d' ' -f1 $G/verdict.txt)"
}
stop() {  # $1 reason: verdict (INVALID), push what exists, exit 1 (run_job.sh then self-destroys)
  log "ev20_b1 STOP: $1" >> $J; label "ev20 b1 stopped: $1"; echo "$1" > $G/STOPPED; finish_verdict
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev20_b1: push FAILED (self_destroy retries)" >> $J; exit 1
}
pull1() { bash $OPS/store.sh pull-files $1 >> $J 2>&1; }                        # one file, store.sh's retries
tabl() { python -c "import json, sys; print(' '.join(json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]))" $TAB $EP $1; }

# ----- 1. the piece set
label "ev20 b1: piece set $PS"
python $T/e20b1.py pieces --dir $PIECES_DIR --out $G/pieces.json > $G/pieces.txt 2>&1 || stop "piece set check FAILED ($(tail -1 $G/pieces.txt | cut -c1-300))"
log "ev20_b1 pieces: $(cut -c1-600 $G/pieces.txt)" >> $J
python $T/no_oracle.py $PIECES_DIR $PIECES_DIR/water_pitcher > $G/no_oracle_pieces.txt 2>&1 || stop "no_oracle refused the piece set ($(tail -2 $G/no_oracle_pieces.txt | tr '\n' ' ' | cut -c1-300))"

# ----- 2. the packed eval-20 inputs (the table's single files), the packed checkpoint
label "ev20 b1: packed eval-20 inputs"
miss=""
for f in $(tabl pull_files); do
  if ! pull1 $f; then
    case $f in *.txt|*.jpg|*_log.json) log "ev20_b1: optional file $f not pulled (a log or image)" >> $J; continue ;; esac
    miss="$miss $f"; continue
  fi
  r=${f#runs/$SRC_RUN/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp $HS/$f /content/$r
done
[ -z "$miss" ] || stop "pull of the packed eval-20 reference FAILED for [${miss# }]"
mkdir -p /content/results/glock_public/ep$EP $I/packed_ck
for f in $(tabl result_files); do pull1 $f && cp $HS/$f /content/results/glock_public/ep$EP/ || stop "pull of $f FAILED"; done
pull1 $CK0 && cp $HS/$CK0 $I/packed_ck/policy.safetensors || stop "pull of the packed checkpoint $CK0 FAILED"
python $T/e20b1.py inputs --content /content --table $TAB --packed_ck $I/packed_ck/policy.safetensors --out $G/inputs.json > $G/inputs.txt 2>&1 \
  || stop "packed inputs check FAILED ($(tail -1 $G/inputs.txt | cut -c1-300))"
log "ev20_b1 inputs: $(cut -c1-700 $G/inputs.txt)" >> $J

# ----- 3. the carve (the mesh lane's method), the seed copies, the guard
label "ev20 b1: carve + seed copies"
rm -rf $I/sf_packed_assets /content/sf20_b1; cp -r $A $I/sf_packed_assets                 # pristine packed copy (not pushed)
$FCV $P/placement_carve.py assets $A $PIECES_DIR /content/sf20_b1 > $G/carve.txt 2>&1 && rm -rf $A && mv /content/sf20_b1 $A \
  || stop "placement_carve.py assets FAILED ($(tail -2 $G/carve.txt | tr '\n' ' ' | cut -c1-300))"
python $T/e20b1.py assets --packed $I/sf_packed_assets --carved $A --pieces $PIECES_DIR --out $G/assets.json > $G/assets.txt 2>&1 \
  || stop "assets check FAILED ($(tail -1 $G/assets.txt | cut -c1-300))"
log "ev20_b1 carve: $(head -c 300 $G/carve.txt | tr '\n' ' ') :: $(cut -c1-700 $G/assets.txt)" >> $J
python $T/e20b1.py arms --content /content --seeds "$SEEDS" --out $G/arms.json > $G/arms.txt 2>&1 \
  || stop "seed copies of P FAILED ($(tail -2 $G/arms.txt | tr '\n' ' ' | cut -c1-300))"
log "ev20_b1 arms: $(tail -1 $G/arms.txt | cut -c1-500)" >> $J
python $T/no_oracle.py /content/refs/glockt/ep$EP /content/refs/perc2$BASE/ep$EP /content/refs/sf/ep$EP /content/results/glock_public/ep$EP $I \
  $(for s in $SEEDS; do echo /content/refs/${PRE}s${s}_glockt/ep$EP; done) > $G/no_oracle_inputs.txt 2>&1 \
  || stop "no_oracle refused an input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))"
log "ev20_b1: inputs ok; no_oracle: $(tail -1 $G/no_oracle_inputs.txt | cut -c1-200)" >> $J

# ----- 4. training: one glock_public.sh call per seed (stock limits, the b1 asset copy)
for s in $SEEDS; do
  label "ev20 b1: seed $s"; log "ev20_b1: seed $s, PAIRS [$EP:local:$BASE:${PRE}s$s]" >> $J; t0=$(date +%s)
  ( REUSE_REF=1 REQUIRE_REUSE=1 EVAL_E20B1=1 SEED=$s PAIRS="$EP:local:$BASE:${PRE}s$s" bash $REPO_DIR/ops/jobs/glock_public.sh ) \
    || log "ev20_b1: seed $s returned $?" >> $J
  log "ev20_b1: seed $s training + curve + $NREP evaluations took $(( ($(date +%s) - t0) / 60 )) min" >> $J
done

# ----- 5. FIRST check: overflow lines per training log; reported: the b1 zero-action rest check
groups=(); for s in $SEEDS; do R_=/content/runs/${PRE}s${s}_glock/ep$EP-s$s; O_=/content/results/${PRE}s${s}_glock_public/ep$EP
  groups+=(--group train_s$s=$R_/train.log --group "train_oom_s$s=$R_.oom*/train.log" --group "curve_s$s=$O_/curve/policy_*/r*/eval.log,$O_/curve/policy_*/eval.log"
           --group "best_s$s=$O_/best/r*/eval.log"); done
count_overflow() { python $T/e10nj.py overflow --out $G/overflow.json "${groups[@]}" --group "conf=$G/conf/r*/eval.log" > $G/overflow.txt 2>&1; }
count_overflow; log "ev20_b1 overflow (FIRST check; > 1000 lines in a training log = pieces not clean in training): $(tr '\n' ' ' < $G/overflow.txt | cut -c1-1800)" >> $J
RF=$(ls /content/refs/${PRE}s42_glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
if [ -n "$RF" ]; then                                              # reported only (the packed run's: pitcher 10.4 mm / 3.9 deg by f8)
  NF=$(python -c "import numpy as np, pyarrow.parquet as pq, sys; print(len(np.array(pq.read_table(sys.argv[1]).column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))" $RF)
  ( cd $FC && EMB=sharpa_hands_mid DEV=cuda timeout -k 60 $EVAL_TIMEOUT .venv/bin/python $T/trace_rollout.py zero $G/zero_b1.npz $RF $NF ) > $G/zero_b1.log 2>&1
  ( cd $REPO_DIR && python $T/trace_score.py $RF $G/zero_b1.npz:zero_action ) > $G/zero_score_b1.txt 2>&1
  python $T/rest_check.py $G/zero_b1.npz $RF > $G/rest_check_b1.json 2>&1
  log "ev20_b1 rest check of P on the b1 copy (reported, not gating; packed run: pitcher 10.4 mm / 3.9 deg until f14): $(cut -c1-400 $G/rest_check_b1.json) | $(tr '\n' ' ' < $G/zero_score_b1.txt | cut -c1-200)" >> $J
fi

# ----- 6. per-seed verification, seed choice (pack 9b), the training-box gate
python $T/e20b1.py cells --content /content --seeds "$SEEDS" --steps $STEPS --packed_ck $I/packed_ck/policy.safetensors --out $G/cells.json > $G/cells.txt 2>&1
log "ev20_b1 cells: $(cut -c1-1500 $G/cells.txt)" >> $J
python $T/e20b1.py choose --cells $G/cells.json --seeds "$SEEDS" --out $G/choice.json > $G/choice.txt 2>&1; ch_rc=$?
log "ev20_b1 choice: $(cut -c1-600 $G/choice.txt)" >> $J
python $T/e20b1.py gate --cells $G/cells.json --out $G/gate.json > $G/gate.txt 2>&1; gate_rc=$?
log "ev20_b1 gate: $(cut -c1-600 $G/gate.txt)" >> $J

# ----- 7. confirmation: only with a chosen seed AND the gate met (PREREG section 4)
confirm() {  # draws of the chosen checkpoint on the pristine evaluator until NCONF have a qa_policy.json (ev10_cs.sh confirm())
  local ck sha CK i have n O tries=0 fails=0
  ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $G/choice.json)
  sha=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sha256'])" $G/choice.json)
  python $T/no_oracle.py $ck $(python -c "import json, sys; d = json.load(open(sys.argv[1])); print(d['seeds'][d['chosen']]['results'])" $G/choice.json) > $G/no_oracle_choice.txt 2>&1 \
    || stop "no_oracle refused the chosen checkpoint or its results"
  CK=$G/conf_checkpoints.json; python -c "import json, sys; json.dump({'20': sys.argv[2]}, open(sys.argv[1], 'w'))" $CK $ck
  [ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || stop "clean evaluator worktree FAILED"
  log "ev20_b1: confirmation of $ck (sha256 ${sha:0:12}) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  mkdir -p $G/conf
  have() { ls $G/conf/r*/ep$EP/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $G/conf/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); O=$G/conf/r$n; tries=$((tries + 1))
    label "ev20 b1: confirmation draw $n"; mkdir -p $O/results $O/ep$EP
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK --results $O/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1
    echo $? > $O/eval_rc.txt
    cp $O/results/episode_0000$EP.* $O/ep$EP/ 2> /dev/null && python $P/qa.py policy $O/ep$EP $EP > /dev/null 2>&1 || true
    rm -rf $O/results
    log "ev20_b1: confirmation draw $n rc $(cat $O/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $O/ep$EP/qa_policy.json 2>/dev/null || echo none) overflow lines $(grep -ac 'overflow - please' $O/eval.log)" >> $J
    if [ -s $O/ep$EP/qa_policy.json ]; then fails=0; else fails=$((fails + 1)); fi
    [ $fails -lt 3 ] || { log "ev20_b1: 3 confirmation draws in a row gave no rollout: confirmation stopped (INCOMPLETE; conf/r*/eval.log)" >> $J; break; }
  done
}
if [ $ch_rc = 0 ] && [ $gate_rc = 0 ]; then
  confirm
elif [ $ch_rc != 0 ]; then
  log "ev20_b1: no seed chosen ($(head -c 300 $G/choice.txt)): no confirmation draws (INVALID / INCOMPLETE; PREREG section 6)" >> $J
else
  log "ev20_b1: training-box gate not met: NO-SWAP, no confirmation draws (PREREG section 4)" >> $J
fi

# ----- 8. score, verify, verdict, push
label "ev20 b1: scoring, verify, verdict"
# the packed policy's fresh draws (h5_summary.json is pushed last by that run) and the old packed draw: single files
if PULL_RETRY_S=5 bash $OPS/store.sh pull-files runs/$H5P7_RUN/results/h5/h5_summary.json >> $J 2>&1; then
  for i in $(seq 1 10); do for x in parquet json; do
    f=runs/$H5P7_RUN/results/h5/r$i/ep$EP/episode_0000$EP.$x
    PULL_RETRY_S=5 bash $OPS/store.sh pull-files $f >> $J 2>&1 && mkdir -p $I/packed_h5/r$i/ep$EP && cp $HS/$f $I/packed_h5/r$i/ep$EP/ \
      || log "ev20_b1: $f not pulled (the packed side is then completed on CPU after)" >> $J
  done; done
else
  log "ev20_b1: $H5P7_RUN has no h5_summary.json in the store: the packed side is scored on CPU after" >> $J
fi
for x in parquet json; do
  PULL_RETRY_S=5 bash $OPS/store.sh pull-files $OLD.$x >> $J 2>&1 && mkdir -p $I/old/r1 && cp $HS/$OLD.$x $I/old/r1/ \
    || log "ev20_b1: $OLD.$x not pulled (the old draw is then scored on CPU after)" >> $J
done
count_overflow
PREF=$(ls /content/refs/glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
sets=(--set "conf:P:$G/conf/r*/ep$EP/episode_0000$EP.parquet" --set "old:P:$I/old/r1/episode_0000$EP.parquet" --set "packed:P:$I/packed_h5/r*/ep$EP/episode_0000$EP.parquet")
for s in $SEEDS; do sets+=(--set "train$s:P:/content/results/${PRE}s${s}_glock_public/ep$EP/best/r*/episode_0000$EP.parquet"); done
[ -n "$PREF" ] && python $T/dr_score.py --kit $KIT --lib $LIB --ep $EP --ref P=$PREF --out $G/score.json "${sets[@]}" > $G/score.txt 2>&1 \
  || log "ev20_b1: scoring FAILED or no P ($(tail -2 $G/score.txt 2>/dev/null | tr '\n' ' ' | cut -c1-300))" >> $J
log "ev20_b1 scores: $(cut -c1-1500 $G/score.txt 2>/dev/null | tr '\n' ' ')" >> $J
finish_verdict
for c in /content/results/${PRE}s*_glock_public/ep$EP/best/policy.safetensors; do   # stored config of each chosen checkpoint
  [ -f $c ] && $FCV $T/ckpt_meta.py $c
done > $G/ckpt_meta.txt 2>&1
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev20_b1: push FAILED (self_destroy retries)" >> $J
