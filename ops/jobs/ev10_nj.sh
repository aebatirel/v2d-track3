#!/bin/bash
# Eval-10 njmax diagnostic (2026-11-01; owner's go for ONE diagnostic training, ~$2-3). DIAGNOSTIC ONLY, NEVER PACKED: a
# checkpoint trained with sim.njmax 1024 stores it in its resolved config and the official evaluator rebuilds sim from that
# config, so it takes changed physics into evaluation (tools/no_oracle.py refuses every name and checkpoint of this run).
# Tests [H] "dropped constraint rows during eval-10 training (cup-in-cup contact; ~6.0 M 'nefc overflow' lines per seed in
# run 20261031-e10v-caf38fb) cause the cup-never-lifted floor". Pre-registered in
# docs/research/work/eval10-njmax-20261101/PREREG.md (written before any result); build notes BUILD.md, launch string and
# cost JOBS.txt there. EVAL episode 10: no ground truth exists or is read; every score is GT-free (our references V and P).
#   1. make_assets (library_v3 + meshes/carve/ev10 pieces, 0.3 kg; as e10v);
#   2. e10v's stored V4p reference through its re-run manifest (ev10_v4p.sh's RERUN_FROM mechanism: rerun_files.txt and the
#      files it lists, one single-file pull each, no listing): refs/perc2e10vmck/ep10 (base), refs/perc2e10v_glockt/ep10
#      (V), results/perc2e10v_glock_public/ep10/{rest_check.json, zero_score.txt}, e10v's arms.json and the packed
#      reference P; from rerun_results.txt only the control: e10v seed 43's chosen checkpoint + summary and e10v's 10
#      official draws; e10v's curve.json of both seeds (the lift control). Control files live in /content/e10v_in (not
#      pushed again). tools/e10nj.py arms: the seed copy refs/perc2e10njs43_glockt/ep10 (V md5 / fingerprint, base md5,
#      URDF mass / COM = e10v's arms.json); tools/no_oracle.py must accept every e10v input;
#   3. ONE training, seed 43 (e10v's chosen seed): glock_public.sh REUSE_REF=1 REQUIRE_REUSE=1 EVAL_NJ_DIAG=1
#      PAIRS=10:local:mck:perc2e10njs43 with TRAIN_ARGS="sim.njmax=1024 sim.nconmax=512" (fc_patches appends them after
#      the FDR overrides); 70M steps, curve 3 evaluations per checkpoint, checkpoint by sim_vs_ref vs V, NREP 10
#      training-box evaluations (all at 1024: the evaluator rebuilds sim from the checkpoint config); GPU memory sampled
#      every 60 s (outside the watchdog's paths);
#   4. tools/e10nj.py overflow (train.log: "nefc overflow", "broadphase overflow", "narrowphase overflow", ...; requested
#      njmax median / p95 / max) -> overflow.json; tools/e10nj.py lift (per curve checkpoint, both cups, 3 repeats; e10v's
#      curves as control) -> lift.json;
#   5. tools/e10nj.py identity (the chosen checkpoint's stored config = e10v seed 43's except output_dir / task.parquet /
#      reference.parquet and the four sim limits, which must read 1024/512) -> STOP if not; tools/e10nj.py cksim -> the
#      512 copy results/ev10_nj/ck512/policy.safetensors (header-only edit; config diff = exactly the four sim limits);
#      tools/e10nj_solver_check.py on the pristine evaluator tree (the evaluator's own config chain + SolverMuJoCo, 1 world)
#      for the 1024 checkpoint, the copy and e10v's s43; tools/e10nj.py guard (no_oracle must REFUSE both files, also as
#      neutral-name copies);
#   6. 10 official draws of the 1024 checkpoint and 10 of the 512 copy: the kit's run_policy_evaluation.py on the pristine
#      worktree, one call per draw, cut at EVAL_TIMEOUT (as ev10_v4p.sh confirm()) -> results/ev10_nj/conf1024|conf512/r<i>;
#   7. tools/e10v_score.py vs V and P (conf1024, conf512, train1024 and e10v's official draws re-scored as the control);
#      tools/e10nj.py verdict -> summary.json and a RESULT line (PREREG section 4 label); ONE store push at the end.
# Integrity: new names only (refs/perc2e10njs43_glock*, runs/perc2e10njs43_glock, results/perc2e10njs43_glock_public,
# results/ev10_nj); e10v's files are read, never written back. Run ids carry -e10nj- (refused otherwise). Nothing is
# packed or uploaded here; nothing of this run may ever be.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-e10nj-<sha7> 'bash ops/jobs/ev10_nj.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; G=/content/results/ev10_nj; HS=/content/hfstore; I=/content/e10v_in
mkdir -p $G $I
case "${RUN_ID:-}" in *-e10nj-*) ;; *) log "ev10_nj: RUN_ID '${RUN_ID:-}' must contain -e10nj-" >> $J; exit 1 ;; esac
REF_RUN=20261031-e10v-caf38fb; E=runs/$REF_RUN                      # the stored V4p reference + the control (fixed)
EP=10; BASE=mck; SRC=perc2e10v; PRE=perc2e10nj; SEED=43; NCONF=10; NJ=1024; NC=512
NJ_ARGS="sim.njmax=$NJ sim.nconmax=$NC"
# the packed eval-10 recipe (gl10A2) as the ep11 gate used it, SPLIT=eval; nothing overridable from the job string
export SPLIT=eval LIB=$REPO_DIR/meshes/library_v3 PIECES=$REPO_DIR/meshes/carve/ev10 SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \
  CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets EVAL_LOCAL_REF=1
export MESH_DIR=$LIB GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
unset MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME ENV_EP10 VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS \
  CONTACT_RETARGET TRAIN_LOCK CK_SWEEP
# (the two lines above are ev10_v4p.sh's, verbatim; here no e10v prefix is trained, no D patch runs, and the njmax opt-in
# is given to the one training call only)
unset EVAL_LOCAL_REF EVAL_NJ_DIAG FC_DR_PATCH FC_DR_RESET FC_DR_SEED
O=/content/results/${PRE}s${SEED}_glock_public/ep$EP; RUNDIR=/content/runs/${PRE}s${SEED}_glock/ep$EP-s$SEED
CK=$O/best/policy.safetensors; CK512=$G/ck512/policy.safetensors
TMPD=${TMPDIR:-/tmp}; CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit; FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python
log "ev10_nj code $(git -C $REPO_DIR rev-parse --short HEAD), DIAGNOSTIC ONLY (never packed), ep $EP, prefix $PRE, seed $SEED, training overrides [$NJ_ARGS], reference run $REF_RUN, LIB $LIB, PIECES $PIECES, NREP $NREP, NCONF $NCONF at $NJ + $NCONF of the 512 copy, STEPS $STEPS, GL_ARGS [$GL_ARGS]" >> $J

verdict() {  # PREREG section 4 label from whatever exists (also after a STOP)
  python $T/e10nj.py verdict --dir $G --ck1024 $CK --ck512 $CK512 --out $G/summary.json > $G/verdict.txt 2>&1
  log "ev10_nj RESULT: $(cut -c1-3000 $G/verdict.txt)" >> $J; label "ev10 nj: $(cut -d' ' -f1 $G/verdict.txt)"
}
stop() {  # $1 reason: verdict (INVALID), push what exists, exit 1 (run_job.sh then self-destroys)
  log "ev10_nj STOP: $1" >> $J; label "ev10 nj stopped: $1"; echo "$1" > $G/STOPPED; verdict
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_nj: push FAILED (self_destroy retries)" >> $J; exit 1
}
pull() { bash $OPS/store.sh pull-files $E/$1 >> $J 2>&1; }                      # one file, store.sh's retries
pullq() { PULL_RETRY_S=5 bash $OPS/store.sh pull-files $E/$1 >> $J 2>&1; }      # optional file: short retries (~1 min)
count_overflow() {  # every log this run has so far -> overflow.json (train = the PREREG count O)
  python $T/e10nj.py overflow --out $G/overflow.json --group train=$RUNDIR/train.log --group "train_oom_retries=$RUNDIR.oom*/train.log" \
    --group "curve=$O/curve/policy_*/r*/eval.log,$O/curve/policy_*/eval.log" --group "best=$O/best/r*/eval.log" \
    --group "conf1024=$G/conf1024/r*/eval.log" --group "conf512=$G/conf512/r*/eval.log" > $G/overflow.txt 2>&1
}
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # as glock_public.sh (kit budget_mesh, support_fill union)
python $P/make_assets.py $LIB $ASSETS --pieces $PIECES >> $J 2>&1 || stop "make_assets FAILED"   # the references name /content/assets

# ----- 1. e10v's stored V4p reference (its re-run manifest) and the control files
label "ev10 nj: e10v reference"
pull results/ev10_v4p/rerun_files.txt || stop "rerun_files.txt of $REF_RUN missing"
pullq results/ev10_v4p/rerun_results.txt || stop "rerun_results.txt of $REF_RUN missing"
while read -r f; do
  case $f in
    refs/${SRC}${BASE}/ep$EP/*|refs/${SRC}_glockt/ep$EP/*|results/${SRC}_glock_public/ep$EP/*) d=/content/$f ;;
    results/ev10_v4p/arms.json|results/ev10_v4p/identity.json|results/ev10_v4p/b0.json|results/ev10_v4p/build.json|results/ev10_v4p/packed_ref/ref_gl_ilc.parquet)
      d=$I/${f#results/ev10_v4p/} ;;
    *) continue ;;                                                 # its track, inputs, packed checkpoint, old draw: not needed
  esac
  pull $f || stop "pull of $REF_RUN's $f FAILED"
  mkdir -p $(dirname $d) && cp -n $HS/$E/$f $d
done < $HS/$E/results/ev10_v4p/rerun_files.txt
while read -r f; do                                                # the control: e10v s43's chosen checkpoint, e10v's draws
  case $f in
    results/${SRC}s${SEED}_glock_public/ep$EP/best/policy.safetensors)
      pull $f || stop "pull of e10v's seed-$SEED checkpoint FAILED (needed for the identity check)"; d=$I/s$SEED/$(basename $f) ;;
    results/${SRC}s${SEED}_glock_public/ep$EP/best/summary.json) d=$I/s$SEED/$(basename $f) ;;
    results/ev10_v4p/conf/r*/ep$EP/episode_0000$EP.parquet|results/ev10_v4p/conf/r*/ep$EP/episode_0000$EP.json|results/ev10_v4p/conf/r*/eval_rc.txt)
      d=$I/${f#results/ev10_v4p/} ;;
    *) continue ;;
  esac
  pullq $f && mkdir -p $(dirname $d) && cp -n $HS/$E/$f $d || log "ev10_nj: control file $f not pulled" >> $J
done < $HS/$E/results/ev10_v4p/rerun_results.txt
for s in 42 43; do                                                 # e10v's curves (lift control; not in its re-run lists)
  f=results/${SRC}s${s}_glock_public/ep$EP/curve/curve.json
  pullq $f && cp $HS/$E/$f $I/curve_s$s.json || log "ev10_nj: $f not pulled (that lift control is then missing)" >> $J
done
for f in s$SEED/policy.safetensors arms.json packed_ref/ref_gl_ilc.parquet; do
  [ -s $I/$f ] || stop "required e10v file $f not pulled"
done
python $T/e10nj.py arms --content /content --prefix $PRE --seed $SEED --e10v_arms $I/arms.json --out $G/arms.json > $G/arms.txt 2>&1 \
  || stop "seed copy of e10v's V FAILED ($(tail -2 $G/arms.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_nj arms: $(tail -1 $G/arms.txt | cut -c1-700)" >> $J
python $T/no_oracle.py /content/refs/${SRC}${BASE}/ep$EP /content/refs/${SRC}_glockt/ep$EP /content/results/${SRC}_glock_public/ep$EP $I \
  > $G/no_oracle_inputs.txt 2>&1 || stop "no_oracle refused an e10v input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_nj: e10v inputs ok; control: $(ls $I/conf/r*/ep$EP/episode_0000$EP.parquet 2> /dev/null | wc -l) e10v draws, curves [$(ls $I/curve_s*.json 2> /dev/null | xargs -n1 basename 2> /dev/null | tr '\n' ' ')]; no_oracle: $(tail -1 $G/no_oracle_inputs.txt | cut -c1-200)" >> $J

# ----- 2. the one training (seed 43) at njmax 1024 / nconmax 512; overflow and lift
label "ev10 nj: training seed $SEED at njmax $NJ"
( while sleep 60; do echo "$(date +%s), $(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2> /dev/null | head -1)"; done ) \
  > $TMPD/ev10_nj_gpu_mem.csv 2>&1 & MEMP=$!                       # /tmp: not a watchdog path (a stalled training still trips it)
t0=$(date +%s)
( REUSE_REF=1 REQUIRE_REUSE=1 EVAL_NJ_DIAG=1 SEED=$SEED PAIRS="$EP:local:$BASE:${PRE}s$SEED" TRAIN_ARGS="$NJ_ARGS" bash $REPO_DIR/ops/jobs/glock_public.sh ) \
  || log "ev10_nj: glock_public.sh returned $?" >> $J
kill $MEMP 2> /dev/null; cp $TMPD/ev10_nj_gpu_mem.csv $G/gpu_mem.csv 2> /dev/null
log "ev10_nj: training + curve + $NREP evaluations took $(( ($(date +%s) - t0) / 60 )) min; GPU memory peak $(cut -d, -f2 $G/gpu_mem.csv 2> /dev/null | sort -n | tail -1) MiB of$(cut -d, -f3 $G/gpu_mem.csv 2> /dev/null | head -1) MiB (60 s samples)" >> $J
count_overflow; log "ev10_nj overflow: $(tr '\n' ' ' < $G/overflow.txt | cut -c1-1500)" >> $J
python $T/e10nj.py lift --curve $O/curve --control e10v_s42=$I/curve_s42.json --control e10v_s43=$I/curve_s43.json --out $G/lift.json > $G/lift.txt 2>&1
log "ev10_nj lift: $(cut -c1-1800 $G/lift.txt)" >> $J
[ -s $CK ] || stop "no chosen checkpoint (training, curve or evaluations failed; overflow.json / lift.json hold what exists)"

# ----- 3. identity, the 512 copy, the evaluator's view of both, the pack guard
label "ev10 nj: identity, 512 copy, solver and guard checks"
python $T/e10nj.py identity --content /content --prefix $PRE --ck $CK --control $I/s$SEED/policy.safetensors --seed $SEED --steps $STEPS \
  --want $NJ $NC --arms $G/arms.json --out $G/identity.json > $G/identity.txt 2>&1; rc=$?
log "ev10_nj identity: $(cut -c1-900 $G/identity.txt)" >> $J
[ $rc = 0 ] || stop "identity FAILED: the diagnostic checkpoint is not e10v's seed-$SEED recipe at njmax $NJ (identity.json)"
python $T/e10nj.py cksim --src $CK --dst $CK512 --from $NJ $NC --to 512 256 --out $G/ck512.json > $G/ck512.txt 2>&1 \
  || log "ev10_nj: the 512 copy FAILED (the 512 readout is then missing)" >> $J
log "ev10_nj 512 copy: $(cut -c1-700 $G/ck512.txt)" >> $J
[ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || stop "clean evaluator worktree FAILED"
solver_check() {  # $1 out name, then flags: the evaluator's own code path on the pristine tree (as the official draws import it)
  local out=$1; shift
  ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
      timeout -k 60 900 $FCV $T/e10nj_solver_check.py --out $G/$out.json "$@" ck1024=$CK \
      $([ -s $CK512 ] && echo ck512=$CK512) e10v_s$SEED=$I/s$SEED/policy.safetensors ) > $G/$out.txt 2>&1
  log "ev10_nj $out (pristine evaluator tree, 1 world): $(tr '\n' ' ' < $G/$out.txt | cut -c1-1500)" >> $J
}
solver_check solver_check                                          # config chain only (fast; cannot be lost to a crash below)
solver_check solver_build --solver --device cuda:0                 # + setup_scene / RLEnv / SolverMuJoCo: njmax, naconmax, bytes
python $T/e10nj.py guard --repo $REPO_DIR --neutral_dir $TMPD --out $G/guard.json $CK $([ -s $CK512 ] && echo $CK512) > $G/guard.txt 2>&1
log "ev10_nj pack guard: $(cut -c1-800 $G/guard.txt)" >> $J

# ----- 4. official draws: 10 at 1024, 10 of the 512 copy (the kit evaluator on the pristine worktree, one call per draw)
confirm_set() {  # $1 set name, $2 checkpoint: draws until NCONF have a qa_policy.json (ev10_v4p.sh confirm(), PREREG 3.4)
  local name=$1 ck=$2 CKJ=$G/$1_checkpoints.json n D tries=0 fails=0
  python -c "import json, sys; json.dump({'10': sys.argv[2]}, open(sys.argv[1], 'w'))" $CKJ $ck
  log "ev10_nj: $name: official draws of $ck (sha256 $(sha256sum < $ck | cut -c1-12)) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  mkdir -p $G/$name
  have() { ls $G/$name/r*/ep$EP/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $G/$name/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); D=$G/$name/r$n; tries=$((tries + 1))
    label "ev10 nj: $name draw $n"; mkdir -p $D/results $D/ep$EP
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CKJ --results $D/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $D/eval.log 2>&1
    echo $? > $D/eval_rc.txt
    cp $D/results/episode_0000$EP.* $D/ep$EP/ 2> /dev/null && python $P/qa.py policy $D/ep$EP $EP > /dev/null 2>&1 || true
    rm -rf $D/results
    log "ev10_nj: $name draw $n rc $(cat $D/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $D/ep$EP/qa_policy.json 2>/dev/null || echo none) overflow lines $(grep -ac 'overflow - please' $D/eval.log)" >> $J
    if [ -s $D/ep$EP/qa_policy.json ]; then fails=0; else fails=$((fails + 1)); fi
    [ $fails -lt 3 ] || { log "ev10_nj: $name: 3 draws in a row gave no rollout: stopped ($name/r*/eval.log)" >> $J; break; }
  done
}
confirm_set conf1024 $CK
[ -s $CK512 ] && confirm_set conf512 $CK512

# ----- 5. score, verdict, push
label "ev10 nj: scoring, verdict"
count_overflow
V=$(ls /content/refs/${SRC}_glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
python $T/e10v_score.py --kit $KIT --lib $LIB --ref V=$V --ref P=$I/packed_ref/ref_gl_ilc.parquet --out $G/score.json \
  --set "conf1024:V:$G/conf1024/r*/ep$EP/episode_0000$EP.parquet" --set "conf512:V:$G/conf512/r*/ep$EP/episode_0000$EP.parquet" \
  --set "train1024:V:$O/best/r*/episode_0000$EP.parquet" --set "e10vconf:V:$I/conf/r*/ep$EP/episode_0000$EP.parquet" > $G/score.txt 2>&1 \
  || log "ev10_nj: scoring FAILED ($(tail -2 $G/score.txt 2>/dev/null | tr '\n' ' ' | cut -c1-300))" >> $J
log "ev10_nj scores: $(cut -c1-1500 $G/score.txt 2>/dev/null | tr '\n' ' ')" >> $J
verdict
$FCV $T/ckpt_meta.py $CK $([ -s $CK512 ] && echo $CK512) > $G/ckpt_meta.txt 2>&1
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_nj: push FAILED (self_destroy retries)" >> $J
