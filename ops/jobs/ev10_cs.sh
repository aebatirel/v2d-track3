#!/bin/bash
# Eval-10 retrain on cavity-safe collision pieces (2026-11-01; owner's go relayed by the orchestrator, ~$3.5). PACKABLE if it
# passes the agreed swap rule and the pack-10 inclusion bar: stock sim=rl contact limits (njmax 512 / nconmax 256), the
# packed eval-10 recipe (gl10A2) exactly as e10v ran it, e10v's stored V4p reference V, two seeds; the ONE changed input is
# the collision piece set PIECESET (meshes/carve/ev10cs4 | ev10cs5, pinned by md5; the PREREG section 2.2 rule picks it) and
# the URDF mass properties make_assets.py derives from it (its inertia.json). Pre-registered in
# docs/research/work/eval10-cs4-20261101/PREREG.md (written before any result); build notes BUILD.md, launch string and cost
# JOBS.txt there. EVAL episode 10: no ground truth exists or is read; every score is GT-free (our references V and P).
#   1. the piece set: tools/e10cs.py pieces (MD5SUMS md5 pinned for the set; file set / md5 = MD5SUMS = FROZEN.md; ev10cs5:
#      clause (a) vs ev10cs4), tools/no_oracle.py on the folder; make_assets.py library_v3 --pieces <set> -> /content/assets;
#      tools/e10cs.py assets (col_NN.obj = piece_NN.obj, URDF inertial = inertia.json, URDF md5 pinned for the set);
#   2. e10v's stored V through its re-run manifest (results/ev10_v4p/rerun_files.txt; ev10_nj.sh's mechanism, one single-file
#      pull each, no listing): refs/perc2e10vmck/ep10 (base), refs/perc2e10v_glockt/ep10 (V),
#      results/perc2e10v_glock_public/ep10/{rest_check.json, zero_score.txt}; into /content/e10v_in (not pushed): e10v's
#      arms.json, the packed reference P, the packed checkpoint (config diff), the old packed draw, e10v's curves (lift
#      control); md5 checked; tools/e10cs.py arms: seed copies refs/perc2e10css<seed>_glockt/ep10 (V md5 / fingerprint / base
#      md5 = e10v's and pinned; URDFs = the set's md5, 0.3 kg); tools/no_oracle.py must accept every input;
#   3. per seed (42, 43) one glock_public.sh call (REUSE_REF=1 REQUIRE_REUSE=1 EVAL_CS_REF=1): 70M steps, checkpoint by
#      sim_vs_ref vs V over 3 evaluations per curve checkpoint, NREP 10 training-box evaluations;
#   4. FIRST check: tools/e10nj.py overflow per training log (nefc / broadphase / narrowphase lines; > 1,000 in a training log
#      labels the result "pieces not clean in training"); tools/e10nj.py lift per seed (beige / blue lift per checkpoint,
#      e10v's curves as control);
#   5. tools/e10cs.py cells (per seed: config = the packed checkpoint's but output_dir / task / reference / seeds, stock
#      limits, V md5, the set's URDFs, rollouts name the checkpoint), choose (pack 9b PREREG section 2), gate (>= 1 seed's
#      training-box mean sim_vs_ref vs V > 0.4632, the packed policy's fresh-draw mean);
#   6. only if a seed is chosen AND the gate is met: no_oracle on the chosen checkpoint, then 10 fresh official draws on the
#      pristine evaluator (ev10_v4p.sh confirm(), verbatim but for the result folder) -> results/ev10_cs/conf/r<i>;
#   7. tools/e10v_score.py vs V and P (confirmation, old packed draw, the packed policy's H5p7 eval-10 draws, training-box
#      draws); tools/e10cs.py verify and verdict (PREREG section 5: the agreed swap rule on both references by
#      tools/e10v_verdict.py's function, the training-box gate, the binding pack-10 inclusion bar +0.02 on V and P, the
#      overflow label, the lift clause, the piece set and URDF inertials); one store push at the end.
# Integrity: new names only (refs/perc2e10css<seed>_glock*, runs/perc2e10css<seed>_glock, results/perc2e10css<seed>_glock_public,
# results/ev10_cs); e10v's files are read, never written under e10v's result names. Run ids carry -e10cs- (refused
# otherwise). Nothing is packed or uploaded here: a pack is built on CPU after the box, only on SWAP-ELIGIBLE + inclusion,
# and the upload stays the owner's word in the uploading session.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-e10cs-<sha7> 'PIECESET=ev10cs5 bash ops/jobs/ev10_cs.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; G=/content/results/ev10_cs; HS=/content/hfstore; I=/content/e10v_in
mkdir -p $G $I
case "${RUN_ID:-}" in *-e10cs-*) ;; *) log "ev10_cs: RUN_ID '${RUN_ID:-}' must contain -e10cs-" >> $J; exit 1 ;; esac
case "${PIECESET:-}" in ev10cs4|ev10cs5) ;; *) log "ev10_cs: PIECESET '${PIECESET:-}' must be ev10cs4 or ev10cs5 (PREREG section 2.2)" >> $J; exit 1 ;; esac
PS=$PIECESET; REF_RUN=20261031-e10v-caf38fb; E=runs/$REF_RUN       # the stored V4p reference (fixed)
EP=10; BASE=mck; SRC=perc2e10v; PRE=perc2e10cs; SEEDS="42 43"; NCONF=10
# the packed eval-10 recipe (gl10A2) as the ep11 gate used it, SPLIT=eval; nothing overridable from the job string
export SPLIT=eval LIB=$REPO_DIR/meshes/library_v3 PIECES=$REPO_DIR/meshes/carve/$PS SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \
  CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets EVAL_LOCAL_REF=1
export MESH_DIR=$LIB GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
unset MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME ENV_EP10 VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS \
  CONTACT_RETARGET TRAIN_LOCK CK_SWEEP
# (the three lines above are ev10_v4p.sh's, verbatim but for PIECES=meshes/carve/$PS; here no e10v prefix is trained and no
# reference stage runs (REUSE_REF), and the cavity-safe opt-in is given to the training calls only)
unset EVAL_LOCAL_REF EVAL_NJ_DIAG EVAL_CS_REF FC_DR_PATCH FC_DR_RESET FC_DR_SEED
H5P7_RUN=20261031-h5p7-1a7cdff                                     # the packed policy's fresh draws (pack-10 comparison set)
# e10v's copies of the packed inputs (rerun_files.txt): store path below runs/$REF_RUN, md5 (= ev10_v4p.sh's INPUTS)
CTRL="results/ev10_v4p/packed_ref/ref_gl_ilc.parquet 1a5003d94852c275519066645a1b9869
results/ev10_v4p/packed_ck/policy.safetensors 1aadc8122769a2b54d120cdd58852922
results/ev10_v4p/old/r1/episode_000010.parquet 64fdd8561f5e2cf51cd27e247a854a4a
results/ev10_v4p/old/r1/episode_000010.json 92afa9d53b8fd438602c57c1e04559d9"
CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit; FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python
log "ev10_cs code $(git -C $REPO_DIR rev-parse --short HEAD), ep $EP, piece set $PS (PIECES $PIECES), reference run $REF_RUN (V), prefix $PRE, seeds [$SEEDS], LIB $LIB, NREP $NREP, NCONF $NCONF, STEPS $STEPS, stock sim limits, GL_ARGS [$GL_ARGS], H5P7_RUN $H5P7_RUN" >> $J

finish_verdict() {  # verify + verdict from whatever exists (also after a STOP)
  python $T/e10cs.py verify --dir $G --out $G/verify.json > $G/verify.txt 2>&1
  log "ev10_cs verify: $(cut -c1-1500 $G/verify.txt)" >> $J
  python $T/e10cs.py verdict --dir $G $(ls $G/score.json 2> /dev/null | sed 's/^/--score /') --seeds "$SEEDS" --out $G/summary.json > $G/verdict.txt 2>&1
  log "ev10_cs RESULT: $(cut -c1-3000 $G/verdict.txt)" >> $J; label "ev10 cs: $(cut -d' ' -f1 $G/verdict.txt)"
}
stop() {  # $1 reason: verdict (INVALID), push what exists, exit 1 (run_job.sh then self-destroys)
  log "ev10_cs STOP: $1" >> $J; label "ev10 cs stopped: $1"; echo "$1" > $G/STOPPED; finish_verdict
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_cs: push FAILED (self_destroy retries)" >> $J; exit 1
}
pull() { bash $OPS/store.sh pull-files $E/$1 >> $J 2>&1; }                      # one file, store.sh's retries
pullq() { PULL_RETRY_S=5 bash $OPS/store.sh pull-files $E/$1 >> $J 2>&1; }      # optional file: short retries (~1 min)

# ----- 1. the piece set, the assets
label "ev10 cs: piece set $PS"
python $T/e10cs.py pieces --set $PS --dir $PIECES --out $G/pieces.json > $G/pieces.txt 2>&1 || stop "piece set check FAILED ($(tail -1 $G/pieces.txt | cut -c1-300))"
log "ev10_cs pieces: $(cut -c1-900 $G/pieces.txt)" >> $J
python $T/no_oracle.py $PIECES $PIECES/blue_cup $PIECES/beige_cup > $G/no_oracle_pieces.txt 2>&1 || stop "no_oracle refused the piece set ($(tail -2 $G/no_oracle_pieces.txt | tr '\n' ' ' | cut -c1-300))"
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # as glock_public.sh (kit budget_mesh, support_fill union)
python $P/make_assets.py $LIB $ASSETS --pieces $PIECES >> $J 2>&1 || stop "make_assets FAILED"   # the references name /content/assets
python $T/e10cs.py assets --set $PS --assets $ASSETS --pieces $PIECES --out $G/assets.json > $G/assets.txt 2>&1 || stop "assets check FAILED ($(tail -1 $G/assets.txt | cut -c1-300))"
log "ev10_cs assets (URDF inertials used): $(cut -c1-900 $G/assets.txt)" >> $J

# ----- 2. e10v's stored V4p reference (its re-run manifest), the packed inputs, the seed copies
label "ev10 cs: e10v reference"
pull results/ev10_v4p/rerun_files.txt || stop "rerun_files.txt of $REF_RUN missing"
while read -r f; do
  case $f in
    refs/${SRC}${BASE}/ep$EP/*|refs/${SRC}_glockt/ep$EP/*|results/${SRC}_glock_public/ep$EP/*) d=/content/$f ;;
    results/ev10_v4p/arms.json|results/ev10_v4p/identity.json|results/ev10_v4p/b0.json|results/ev10_v4p/build.json) d=$I/${f#results/ev10_v4p/} ;;
    results/ev10_v4p/packed_ref/ref_gl_ilc.parquet|results/ev10_v4p/packed_ck/policy.safetensors|results/ev10_v4p/old/r1/episode_000010.*) d=$I/${f#results/ev10_v4p/} ;;
    *) continue ;;                                                 # its track, inputs: not needed
  esac
  pull $f || stop "pull of $REF_RUN's $f FAILED"
  mkdir -p $(dirname $d) && { [ -e $d ] || cp $HS/$E/$f $d; }       # (not cp -n: newer coreutils warn on stderr)
done < $HS/$E/results/ev10_v4p/rerun_files.txt
while read -r f m; do
  [ "$(md5sum < $I/${f#results/ev10_v4p/} 2> /dev/null | cut -c1-32)" = "$m" ] || stop "e10v's $f missing or md5 != $m"
done <<< "$CTRL"
for s in 42 43; do                                                 # e10v's curves (lift control; not in its re-run lists)
  f=results/${SRC}s${s}_glock_public/ep$EP/curve/curve.json
  pullq $f && cp $HS/$E/$f $I/curve_s$s.json || log "ev10_cs: $f not pulled (that lift control is then missing)" >> $J
done
python $T/e10cs.py arms --content /content --seeds "$SEEDS" --set $PS --e10v_arms $I/arms.json --out $G/arms.json > $G/arms.txt 2>&1 \
  || stop "seed copies of e10v's V FAILED ($(tail -2 $G/arms.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_cs arms: $(tail -1 $G/arms.txt | cut -c1-700)" >> $J
python $T/no_oracle.py /content/refs/${SRC}${BASE}/ep$EP /content/refs/${SRC}_glockt/ep$EP /content/results/${SRC}_glock_public/ep$EP $I \
  $(for s in $SEEDS; do echo /content/refs/${PRE}s${s}_glockt/ep$EP; done) > $G/no_oracle_inputs.txt 2>&1 \
  || stop "no_oracle refused an input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_cs: e10v inputs ok; curves [$(ls $I/curve_s*.json 2> /dev/null | xargs -n1 basename 2> /dev/null | tr '\n' ' ')]; no_oracle: $(tail -1 $G/no_oracle_inputs.txt | cut -c1-200)" >> $J

# ----- 3. training: one glock_public.sh call per seed (stock limits, the piece set's assets)
for s in $SEEDS; do
  label "ev10 cs: seed $s"; log "ev10_cs: seed $s, PAIRS [$EP:local:$BASE:${PRE}s$s]" >> $J; t0=$(date +%s)
  ( REUSE_REF=1 REQUIRE_REUSE=1 EVAL_CS_REF=1 SEED=$s PAIRS="$EP:local:$BASE:${PRE}s$s" bash $REPO_DIR/ops/jobs/glock_public.sh ) \
    || log "ev10_cs: seed $s returned $?" >> $J
  log "ev10_cs: seed $s training + curve + $NREP evaluations took $(( ($(date +%s) - t0) / 60 )) min" >> $J
done

# ----- 4. FIRST check: overflow lines per training log; lift per checkpoint
groups=(); for s in $SEEDS; do R_=/content/runs/${PRE}s${s}_glock/ep$EP-s$s; O_=/content/results/${PRE}s${s}_glock_public/ep$EP
  groups+=(--group train_s$s=$R_/train.log --group "train_oom_s$s=$R_.oom*/train.log" --group "curve_s$s=$O_/curve/policy_*/r*/eval.log,$O_/curve/policy_*/eval.log"
           --group "best_s$s=$O_/best/r*/eval.log"); done
count_overflow() { python $T/e10nj.py overflow --out $G/overflow.json "${groups[@]}" --group "conf=$G/conf/r*/eval.log" > $G/overflow.txt 2>&1; }
count_overflow; log "ev10_cs overflow (FIRST check; > 1000 lines in a training log = pieces not clean in training): $(tr '\n' ' ' < $G/overflow.txt | cut -c1-1800)" >> $J
for s in $SEEDS; do
  python $T/e10nj.py lift --curve /content/results/${PRE}s${s}_glock_public/ep$EP/curve --control e10v_s42=$I/curve_s42.json --control e10v_s43=$I/curve_s43.json \
    --out $G/lift_s$s.json > $G/lift_s$s.txt 2>&1
  log "ev10_cs lift s$s: $(cut -c1-1500 $G/lift_s$s.txt)" >> $J
done

# ----- 5. per-seed verification, seed choice (pack 9b), the training-box gate
python $T/e10cs.py cells --content /content --seeds "$SEEDS" --set $PS --steps $STEPS --packed_ck $I/packed_ck/policy.safetensors --out $G/cells.json > $G/cells.txt 2>&1
log "ev10_cs cells: $(cut -c1-1500 $G/cells.txt)" >> $J
python $T/e10cs.py choose --cells $G/cells.json --seeds "$SEEDS" --out $G/choice.json > $G/choice.txt 2>&1; ch_rc=$?
log "ev10_cs choice: $(cut -c1-600 $G/choice.txt)" >> $J
python $T/e10cs.py gate --cells $G/cells.json --out $G/gate.json > $G/gate.txt 2>&1; gate_rc=$?
log "ev10_cs gate: $(cut -c1-600 $G/gate.txt)" >> $J

# ----- 6. confirmation: only with a chosen seed AND the gate met (PREREG section 4)
confirm() {  # draws of the chosen checkpoint on the pristine evaluator until NCONF have a qa_policy.json (ev10_v4p.sh confirm())
  local ck sha CK i have n O tries=0 fails=0
  ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $G/choice.json)
  sha=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sha256'])" $G/choice.json)
  python $T/no_oracle.py $ck $(python -c "import json, sys; d = json.load(open(sys.argv[1])); print(d['seeds'][d['chosen']]['results'])" $G/choice.json) > $G/no_oracle_choice.txt 2>&1 \
    || stop "no_oracle refused the chosen checkpoint or its results"
  CK=$G/conf_checkpoints.json; python -c "import json, sys; json.dump({'10': sys.argv[2]}, open(sys.argv[1], 'w'))" $CK $ck
  [ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || stop "clean evaluator worktree FAILED"
  log "ev10_cs: confirmation of $ck (sha256 ${sha:0:12}) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  mkdir -p $G/conf
  have() { ls $G/conf/r*/ep$EP/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $G/conf/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); O=$G/conf/r$n; tries=$((tries + 1))
    label "ev10 cs: confirmation draw $n"; mkdir -p $O/results $O/ep$EP
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK --results $O/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1
    echo $? > $O/eval_rc.txt
    cp $O/results/episode_0000$EP.* $O/ep$EP/ 2> /dev/null && python $P/qa.py policy $O/ep$EP $EP > /dev/null 2>&1 || true
    rm -rf $O/results
    log "ev10_cs: confirmation draw $n rc $(cat $O/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $O/ep$EP/qa_policy.json 2>/dev/null || echo none) overflow lines $(grep -ac 'overflow - please' $O/eval.log)" >> $J
    if [ -s $O/ep$EP/qa_policy.json ]; then fails=0; else fails=$((fails + 1)); fi
    [ $fails -lt 3 ] || { log "ev10_cs: 3 confirmation draws in a row gave no rollout: confirmation stopped (INCOMPLETE; conf/r*/eval.log)" >> $J; break; }
  done
}
if [ $ch_rc = 0 ] && [ $gate_rc = 0 ]; then
  confirm
elif [ $ch_rc != 0 ]; then
  log "ev10_cs: no seed chosen ($(head -c 300 $G/choice.txt)): no confirmation draws (INVALID / INCOMPLETE; PREREG section 6)" >> $J
else
  log "ev10_cs: training-box gate not met: NO-SWAP, no confirmation draws (PREREG section 4)" >> $J
fi

# ----- 7. score, verify, verdict, push
label "ev10 cs: scoring, verify, verdict"
# the packed policy's fresh draws: only once that run has finished (its h5_summary.json is pushed last), short retries
if PULL_RETRY_S=5 bash $OPS/store.sh pull-files runs/$H5P7_RUN/results/h5/h5_summary.json >> $J 2>&1; then
  for i in $(seq 1 10); do for x in parquet json; do
    f=runs/$H5P7_RUN/results/h5/r$i/ep10/episode_000010.$x
    PULL_RETRY_S=5 bash $OPS/store.sh pull-files $f >> $J 2>&1 && mkdir -p $I/packed_h5/r$i/ep10 && cp $HS/$f $I/packed_h5/r$i/ep10/ \
      || log "ev10_cs: $f not pulled (the packed side is then completed on CPU after)" >> $J
  done; done
else
  log "ev10_cs: $H5P7_RUN has no h5_summary.json in the store: the packed side is scored on CPU after" >> $J
fi
count_overflow
V=$(ls /content/refs/${SRC}_glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
sets=(--set "conf:V:$G/conf/r*/ep$EP/episode_0000$EP.parquet" --set "old:P:$I/old/r1/episode_0000$EP.parquet" --set "packed:P:$I/packed_h5/r*/ep10/episode_000010.parquet")
for s in $SEEDS; do sets+=(--set "train$s:V:/content/results/${PRE}s${s}_glock_public/ep$EP/best/r*/episode_0000$EP.parquet"); done
[ -n "$V" ] && python $T/e10v_score.py --kit $KIT --lib $LIB --ref V=$V --ref P=$I/packed_ref/ref_gl_ilc.parquet --out $G/score.json "${sets[@]}" > $G/score.txt 2>&1 \
  || log "ev10_cs: scoring FAILED or no V ($(tail -2 $G/score.txt 2>/dev/null | tr '\n' ' ' | cut -c1-300))" >> $J
log "ev10_cs scores: $(cut -c1-1500 $G/score.txt 2>/dev/null | tr '\n' ' ')" >> $J
finish_verdict
for c in /content/results/${PRE}s*_glock_public/ep$EP/best/policy.safetensors; do   # stored config of each chosen checkpoint
  [ -f $c ] && $FCV $T/ckpt_meta.py $c
done > $G/ckpt_meta.txt 2>&1
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_cs: push FAILED (self_destroy retries)" >> $J
