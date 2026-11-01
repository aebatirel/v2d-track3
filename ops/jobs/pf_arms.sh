#!/bin/bash
# Perfect-following hand-assignment arms (2026-11-01, perfect-following session; docs/research/work/pf-hands-20261101/PREREG.md,
# written before any result). The packed grasp-lock recipe (glock_public.sh: SF 1, REPLAN 1, EVOLVE 0, 70M steps, CURVE_REP 3,
# NREP 10, stock sim=rl contact limits 512 / 256, library_v3) on the episode's own perceived base reference refs/perc2mck/ep<N>;
# arms differ ONLY in the grasp-lock arguments:
#   s  = the packed construction: --single_hand 1 (one hand carries each object; the other is parked);
#   2h = the same without --single_hand: every MANO hold phase becomes a robot hold, so hand-overs and two-hand holds are kept.
# Every arm-seed cell trains on its own byte copy refs/pf<arm>s<seed>mck/ep<N> of the base (glock_public.sh PERC prefix,
# GL_ARGS_pf<arm>s<seed>), one glock_public.sh invocation per seed (its pairs in a wave of TRAIN_SLOTS 2).
# SPLIT=public: public twin, scored by sim_vs_ref (our reference) and registered AUC vs mocap (evaluation only, after training);
#   the inputs are the stored perceived base reference of SRC_RUN (PULL_SUB refs/perc2mck/ep<N>); nothing is packed.
# SPLIT=eval: eval episode, GT-free only. Inputs = the packed episode's files (packed_refs.json pull_files, single-file pulls);
#   the packed reference P is kept aside for scoring (the arms change robot-hand tracks only: object poses equal P's, which
#   tools/dr_score.py's own-reference check verifies on every rollout). Per episode: seed choice (PREREG), training-box gate
#   (chosen seed's mean sim_vs_ref vs P > the packed policy's H5p7 fresh-draw mean), then NCONF fresh official draws on the
#   pristine evaluator, tools/dr_score.py (conf / packed H5p7 / old packed draw / training draws, all vs P) and
#   tools/pf_verdict.py (pack-9b swap rule a / b / c / s + the +0.02 inclusion bar). Nothing is packed or uploaded here.
# Env: EP (one or more episodes, space-separated), SPLIT (public|eval), ARMS (e.g. "s 2h" or "2h"), SEEDS (default "42 43"),
#      SRC_RUN (public only), NCONF (default 10). RUN_ID must contain -pf.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-pfA-<sha7> \
#     'EP=13 SPLIT=public ARMS="s 2h" SRC_RUN=20261030-orcB-38234d1 bash ops/jobs/pf_arms.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; HS=/content/hfstore; G=/content/results/pf_arms; I=/content/pf_in
mkdir -p $G $I
case "${RUN_ID:-}" in *-pf*) ;; *) log "pf_arms: RUN_ID '${RUN_ID:-}' must contain -pf" >> $J; exit 1 ;; esac
EPS=${EP:?EP}; SPLIT=${SPLIT:?SPLIT}; ARMS=${ARMS:?ARMS}; SEEDS=${SEEDS:-"42 43"}; NCONF=${NCONF:-10}
TAB=$REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json; H5P7_RUN=20261031-h5p7-1a7cdff
GC="--mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
gl_of() { case $1 in s) echo "--single_hand 1 $GC" ;; 2h) echo "$GC" ;; *) return 1 ;; esac; }
for a in $ARMS; do gl_of $a > /dev/null || { log "pf_arms: unknown arm $a" >> $J; exit 1; }; done
export LIB=$REPO_DIR/meshes/library_v3 SF=1 SETTLE=0 REPLAN=1 EVOLVE=0 CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 \
  STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets SPLIT
export MESH_DIR=$LIB
unset PIECES MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS CONTACT_RETARGET \
  TRAIN_LOCK CK_SWEEP EVAL_LOCAL_REF EVAL_NJ_DIAG EVAL_CS_REF EVAL_E20B1 FC_DR_PATCH FC_DR_RESET FC_DR_SEED HUMAN
for e in $EPS; do unset ENV_EP$e; done
[ $SPLIT = eval ] && export EVAL_PF=1
CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit; FC=/content/v2d/robotic_grounding/flash_chord; FCV=$FC/.venv/bin/python
log "pf_arms code $(git -C $REPO_DIR rev-parse --short HEAD), EP [$EPS], SPLIT $SPLIT, ARMS [$ARMS], SEEDS [$SEEDS], NCONF $NCONF, SRC_RUN ${SRC_RUN:-table}, stock limits, common GL_ARGS [$GC]" >> $J
pull1() { bash $OPS/store.sh pull-files $1 >> $J 2>&1; }
tabl() { python -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $TAB $1 $2; }

# ----- 1. inputs
label "pf arms: inputs"
OK=""
for e in $EPS; do
  if [ $SPLIT = public ]; then
    PULL_SUB="refs/perc2mck/ep$e" bash $OPS/store.sh pull-run ${SRC_RUN:?SRC_RUN} >> $J 2>&1 || { log "pf_arms ep$e: pull FAILED" >> $J; continue; }
  else
    [ "$(tabl $e mode)" = glock ] || { log "pf_arms ep$e: not a grasp-lock episode in the table; skipped" >> $J; continue; }
    src=$(tabl $e source_run); miss=""
    for f in $(tabl $e pull_files); do
      if ! pull1 $f; then case $f in *.txt|*.jpg|*_log.json) continue ;; esac; miss="$miss $f"; continue; fi
      r=${f#runs/$src/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp $HS/$f /content/$r
    done
    [ -z "$miss" ] || { log "pf_arms ep$e: pull of the packed inputs FAILED [${miss# }]" >> $J; continue; }
    ref=/content/$(tabl $e reference)
    [ "$(md5sum < $ref | cut -c1-32)" = "$(tabl $e md5)" ] || { log "pf_arms ep$e: packed reference md5 mismatch" >> $J; continue; }
    mkdir -p $I/ep$e; cp $ref $I/ep$e/P.parquet                    # P (the packed reference), kept for scoring
  fi
  B=$(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1)
  [ -s "$B" ] || { log "pf_arms ep$e: no base reference refs/perc2mck/ep$e" >> $J; continue; }
  for s in $SEEDS; do for a in $ARMS; do
    pre=pf${a}s$s; rm -rf /content/refs/${pre}mck/ep$e; mkdir -p /content/refs/${pre}mck
    cp -r /content/refs/perc2mck/ep$e /content/refs/${pre}mck/ep$e
  done; done
  log "pf_arms ep$e: base $B (md5 $(md5sum < $B | cut -c1-12)); arm copies made" >> $J; OK="$OK $e"
done
OK=${OK# }; [ -n "$OK" ] || { log "pf_arms: no episode has its inputs" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
[ $SPLIT = eval ] && { python $T/no_oracle.py $(for e in $OK; do echo /content/refs/perc2mck/ep$e /content/refs/sf/ep$e $I/ep$e; done) > $G/no_oracle_inputs.txt 2>&1 \
  || { log "pf_arms: no_oracle refused an input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }; }

# ----- 2. training: one glock_public.sh invocation per seed, every (episode, arm) of it in waves of 2
for s in $SEEDS; do
  PP=""; for e in $OK; do for a in $ARMS; do PP="$PP $e:local:mck:pf${a}s$s"; export GL_ARGS_pf${a}s$s="$(gl_of $a)"; done; done
  label "pf arms: seed $s [$PP ]"; log "pf_arms: seed $s, PAIRS [${PP# }]" >> $J; t0=$(date +%s)
  ( SEED=$s PAIRS="${PP# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "pf_arms: seed $s returned $?" >> $J
  log "pf_arms: seed $s took $(( ($(date +%s) - t0) / 60 )) min" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: interim push FAILED" >> $J
done
for e in $OK; do for s in $SEEDS; do for a in $ARMS; do        # stored config of every chosen checkpoint
  c=/content/results/pf${a}s${s}_glock_public/ep$e/best/policy.safetensors; [ -f $c ] && { echo "== ep$e $a s$s"; $FCV $T/ckpt_meta.py $c; }
done; done; done > $G/ckpt_meta.txt 2>&1

# ----- 3. public: the arm table (registered AUC vs mocap + sim_vs_ref plain / symmetric), verdict by tools/pf_verdict.py public
if [ $SPLIT = public ]; then
  for e in $OK; do NM=$(python -c "import pyarrow.parquet as pq, sys; print(','.join(pq.read_table(sys.argv[1]).column('object_body_names')[0].as_py()))" $(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet | head -1)); for s in $SEEDS; do for a in $ARMS; do
    for r in /content/results/pf${a}s${s}_glock_public/ep$e/best/r*/; do
      [ -f $r/episode_$(printf %06d $e).parquet ] && python $T/simref_timeline.py $r $e --kit $KIT --names $NM --json $r/timeline.json > /dev/null 2>&1
    done
  done; done; done
  python $T/pf_verdict.py public --results /content/results --eps "$OK" --arms "$ARMS" --seeds "$SEEDS" --out $G/summary.json > $G/verdict.txt 2>&1
  log "pf_arms RESULT: $(cut -c1-3000 $G/verdict.txt)" >> $J; label "pf arms: $(head -c 80 $G/verdict.txt)"
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: push FAILED (self_destroy retries)" >> $J
  exit 0
fi

# ----- 4. eval: seed choice + training-box gate per (episode, arm); confirmation draws of the chosen checkpoint
confirm() {  # $1 ep, $2 checkpoint, $3 out dir: draws on the pristine evaluator until NCONF have a qa_policy.json (ev20_b1.sh)
  local ep=$1 ck=$2 D=$3 CK n O tries=0 fails=0 E6
  E6=$(printf %06d $ep); CK=$D/conf_checkpoints.json; mkdir -p $D
  python -c "import json, sys; json.dump({sys.argv[2]: sys.argv[3]}, open(sys.argv[1], 'w'))" $CK $ep $ck
  [ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || { log "pf_arms: clean evaluator worktree FAILED" >> $J; return 1; }
  log "pf_arms ep$ep: confirmation of $ck (sha256 $(sha256sum < $ck | cut -c1-12)) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  have() { ls $D/r*/ep$ep/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $D/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); O=$D/r$n; tries=$((tries + 1))
    label "pf arms: ep$ep confirmation draw $n"; mkdir -p $O/results $O/ep$ep
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK --results $O/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1
    echo $? > $O/eval_rc.txt
    cp $O/results/episode_$E6.* $O/ep$ep/ 2> /dev/null && python $P/qa.py policy $O/ep$ep $ep > /dev/null 2>&1 || true
    rm -rf $O/results
    log "pf_arms ep$ep: confirmation draw $n rc $(cat $O/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $O/ep$ep/qa_policy.json 2>/dev/null || echo none) overflow lines $(grep -ac 'overflow - please' $O/eval.log)" >> $J
    if [ -s $O/ep$ep/qa_policy.json ]; then fails=0; else fails=$((fails + 1)); fi
    [ $fails -lt 3 ] || { log "pf_arms ep$ep: 3 draws in a row gave no rollout: confirmation stopped (INCOMPLETE)" >> $J; break; }
  done
}
for e in $OK; do
  E6=$(printf %06d $e)
  for i in $(seq 1 10); do for x in parquet json; do              # the packed policy's fresh draws (H5p7)
    f=runs/$H5P7_RUN/results/h5/r$i/ep$e/episode_$E6.$x; PULL_RETRY_S=5 pull1 $f && mkdir -p $I/ep$e/packed_h5/r$i && cp $HS/$f $I/ep$e/packed_h5/r$i/
  done; done
  OLD=runs/20261026-pack6-5203d42/results/submission/results/episode_$E6   # the board pack's old packed draw (pack 6)
  for x in parquet json; do PULL_RETRY_S=5 pull1 $OLD.$x && mkdir -p $I/ep$e/old/r1 && cp $HS/$OLD.$x $I/ep$e/old/r1/; done
  for a in $ARMS; do
    python $T/pf_verdict.py choose --results /content/results --ep $e --arm $a --seeds "$SEEDS" --h5 $I/ep$e/packed_h5 --out $G/choice_ep${e}_$a.json > $G/choice_ep${e}_$a.txt 2>&1; rc=$?
    log "pf_arms ep$e $a choice + gate: $(cut -c1-700 $G/choice_ep${e}_$a.txt)" >> $J
    if [ $rc = 0 ]; then
      ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $G/choice_ep${e}_$a.json)
      if python $T/no_oracle.py $ck > $G/no_oracle_ck_ep${e}_$a.txt 2>&1; then confirm $e $ck $G/conf_ep${e}_$a
      else log "pf_arms ep$e $a: no_oracle refused the chosen checkpoint" >> $J; fi
    fi
    sets=(--set "conf:P:$G/conf_ep${e}_$a/r*/ep$e/episode_$E6.parquet" --set "old:P:$I/ep$e/old/r1/episode_$E6.parquet" --set "packed:P:$I/ep$e/packed_h5/r*/episode_$E6.parquet")
    for s in $SEEDS; do sets+=(--set "train$s:P:/content/results/pf${a}s${s}_glock_public/ep$e/best/r*/episode_$E6.parquet"); done
    python $T/dr_score.py --kit $KIT --lib $LIB --ep $e --ref P=$I/ep$e/P.parquet --out $G/score_ep${e}_$a.json "${sets[@]}" > $G/score_ep${e}_$a.txt 2>&1 \
      || log "pf_arms ep$e $a: scoring FAILED ($(tail -2 $G/score_ep${e}_$a.txt | tr '\n' ' ' | cut -c1-300))" >> $J
    for r in $G/conf_ep${e}_$a/r*/ep$e; do python $T/simref_timeline.py $r $e --kit $KIT --names $(tabl $e objects | tr ' ' ,) --json $r/timeline.json > /dev/null 2>&1; done
    python $T/pf_verdict.py eval --score $G/score_ep${e}_$a.json --choice $G/choice_ep${e}_$a.json --table $TAB --ep $e --out $G/verdict_ep${e}_$a.json > $G/verdict_ep${e}_$a.txt 2>&1
    log "pf_arms ep$e $a RESULT: $(cut -c1-2500 $G/verdict_ep${e}_$a.txt)" >> $J; label "pf arms ep$e $a: $(head -c 60 $G/verdict_ep${e}_$a.txt)"
    bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: interim push FAILED" >> $J
  done
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: push FAILED (self_destroy retries)" >> $J
