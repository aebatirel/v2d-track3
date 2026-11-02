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
# BRIDGE=1 (eval; docs/research/work/pf-bridge-20261101/PREREG.md): the base's object track is first repaired by
# tools/guard_bridge.py at the perception's TRACK_GUARD re-acquisitions (events.json there); the candidate is then scored vs
# P (packed) and vs its own bridged reference B, and tools/pf_verdict.py applies that PREREG's two-reference rule.
# Env: EP (one or more episodes, space-separated), SPLIT (public|eval), ARMS (e.g. "s 2h" or "2h"), SEEDS (default "42 43"),
#      SRC_RUN (public only), NCONF (default 10). RUN_ID must contain -pf.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-pfA-<sha7> \
#     'EP=13 SPLIT=public ARMS="s 2h" SRC_RUN=20261030-orcB-38234d1 bash ops/jobs/pf_arms.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; HS=/content/hfstore; G=/content/results/pf_arms; I=/content/pf_in
mkdir -p $G $I
case "${RUN_ID:-}" in *-pf*) ;; *) log "pf_arms: RUN_ID '${RUN_ID:-}' must contain -pf" >> $J; exit 1 ;; esac
EPS=${EP:?EP}; SPLIT=${SPLIT:?SPLIT}; ARMS=${ARMS:?ARMS}; SEEDS=${SEEDS:-"42 43"}; NCONF=${NCONF:-10}
TAB=${TAB_OVERRIDE:-$REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json}; H5P7_RUN=20261031-h5p7-1a7cdff
GC="--mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
arms_of() { local v=ARMS_EP$1; echo ${!v:-$ARMS}; }              # ARMS_EP<N>: that episode's arms (default ARMS)
gl_of() { case $1 in s) echo "--single_hand 1 $GC" ;; f) echo "--single_hand 2 $GC" ;; se) echo "--single_hand 1 $GC --hold_to_end ${HOLD_TO_END:?HOLD_TO_END}" ;; p0|pz) echo "(packed reference reused: $GC)" ;; lw) echo "--single_hand 1 $GC" ;; plw) echo "(packed reference reused, lift windows: $GC)" ;; slw) echo "(standard learner: packed base reference byte copy, lift windows)" ;; sm) echo "(standard learner: packed base reference byte copy, Tier B collision MESH_OBJS_EP<N>)" ;; s0) echo "(standard learner: packed base reference byte copy, plain reseed)" ;; pm) echo "(packed reference reused, lift windows, Tier B collision MESH_OBJS_EP<N>: $GC)" ;; p0m) echo "(packed reference reused, Tier B collision MESH_OBJS_EP<N>: $GC)" ;; 2h) echo "$GC" ;; *) return 1 ;; esac; }
for a in $ARMS $(for e in $EPS; do arms_of $e; done); do gl_of $a > /dev/null || { log "pf_arms: unknown arm $a" >> $J; exit 1; }; done
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
OK=""; STD_EPS=""
for e in $EPS; do
  if [ $SPLIT = public ]; then
    PULL_SUB="refs/perc2mck/ep$e" bash $OPS/store.sh pull-run ${SRC_RUN:?SRC_RUN} >> $J 2>&1 || { log "pf_arms ep$e: pull FAILED" >> $J; continue; }
  else
    want=glock; case "$(arms_of $e)" in slw|sm|s0) want=std ;; esac   # (pf-lift addendum C, pf-mesh) standard-learner arms, alone
    [ "$(tabl $e mode)" = $want ] || { log "pf_arms ep$e: not a $want episode in the table (arms [$(arms_of $e)]); skipped" >> $J; continue; }
    src=$(tabl $e source_run); miss=""
    for f in $(tabl $e pull_files); do
      if ! pull1 $f; then case $f in *.txt|*.jpg|*_log.json) continue ;; esac; miss="$miss $f"; continue; fi
      r=${f#runs/$src/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp $HS/$f /content/$r
    done
    [ -z "$miss" ] || { log "pf_arms ep$e: pull of the packed inputs FAILED [${miss# }]" >> $J; continue; }
    ref=/content/$(tabl $e reference)
    [ $want = std ] && ref=$(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1)   # std: P = the base (a byte copy of refs/perc2mcks: md5)
    [ "$(md5sum < $ref | cut -c1-32)" = "$(tabl $e md5)" ] || { log "pf_arms ep$e: packed reference md5 mismatch" >> $J; continue; }
    mkdir -p $I/ep$e; cp $ref $I/ep$e/P.parquet                    # P (the packed reference), kept for scoring
  fi
  B=$(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1)
  [ -s "$B" ] || { log "pf_arms ep$e: no base reference refs/perc2mck/ep$e" >> $J; continue; }
  if case "$(arms_of $e)" in slw|sm|s0) true ;; *) false ;; esac; then   # std: the base must be the packed reference byte for byte
    [ "$(md5sum < $B | cut -c1-32)" = "$(tabl $e md5)" ] || { log "pf_arms ep$e: base $B is not the packed reference (md5)" >> $J; continue; }
    [ -s /content/refs/perc2mck/ep$e/hands.npz ] && [ -s /content/perc2/ep$e/poses.npz ] || { log "pf_arms ep$e: hands.npz / perc2 poses.npz missing" >> $J; continue; }
    STD_EPS="$STD_EPS $e"; log "pf_arms ep$e: $(arms_of $e) base $B md5 $(md5sum < $B | cut -c1-12) = packed reference" >> $J; OK="$OK $e"; continue
  fi
  if [ "${BRIDGE:-0}" = 1 ]; then                                   # (pf-bridge PREREG) guard-bridge the base's object track
    EVS=$(python -c "import json, sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], {}).get('events', ''))" $REPO_DIR/docs/research/work/pf-bridge-20261101/events.json $e)
  fi
  if [ "${BRIDGE:-0}" = 1 ] && [ -z "$EVS" ]; then log "pf_arms ep$e: no guard events (events.json): base not bridged, scored vs P only" >> $J; fi
  if [ "${BRIDGE:-0}" = 1 ] && [ -n "$EVS" ]; then
    python -c "import rtree" 2> /dev/null || pip install -q rtree >> $J 2>&1   # trimesh proximity queries (box image lacks it)
    touch $I/ep$e/BRIDGED; cp $B $I/ep$e/base_unbridged.parquet
    python $T/guard_bridge.py $I/ep$e/base_unbridged.parquet $B --events "$EVS" --mesh_dir $LIB --json $G/bridge_ep$e.json > $G/bridge_ep$e.txt 2>&1 \
      || { log "pf_arms ep$e: guard_bridge FAILED ($(tail -2 $G/bridge_ep$e.txt | tr '\n' ' ' | cut -c1-300))" >> $J; continue; }
    log "pf_arms ep$e: guard bridge [$EVS]: $(cut -c1-500 $G/bridge_ep$e.txt)" >> $J
  fi
  v=$(tabl $e env 2> /dev/null); [ -n "$v" ] && [ "$v" != None ] && export ENV_EP$e="$v" && log "pf_arms ep$e: ENV_EP$e=$v (the packed recipe's)" >> $J
  for s in $SEEDS; do for a in $(arms_of $e); do
    pre=pf${a}s$s; rm -rf /content/refs/${pre}mck/ep$e; mkdir -p /content/refs/${pre}mck
    cp -r /content/refs/perc2mck/ep$e /content/refs/${pre}mck/ep$e
  done; done
  for s in $SEEDS; do for a in $(arms_of $e); do                  # (pf-release PREREG_B) arms on the PACKED reference P itself:
    case $a in p0|pz|plw|pm|p0m) ;; *) continue ;; esac                    # p0 = byte copy, pz = tools/hold_freeze.py on it (FREEZE_EP<N>)
    [ $SPLIT = eval ] || { log "pf_arms ep$e: arm $a needs SPLIT=eval" >> $J; continue 2; }
    pre=pf${a}s$s; hive=$(dirname $(tabl $e reference)); hive=${hive#refs/*/ep$e/}; D_=/content/refs/${pre}_glockt/ep$e
    rm -rf $D_; mkdir -p $D_/$hive; cp -r /content/$(dirname $(dirname $(dirname $(tabl $e reference))))/reconstructed_stage $D_/ 2> /dev/null || cp -r /content/refs/perc2mck/ep$e/reconstructed_stage $D_/
    if [ $a = pz ]; then fv=FREEZE_EP$e; IFS=: read -r fs ff <<< "${!fv:?FREEZE_EP$e}"
      python $T/hold_freeze.py $I/ep$e/P.parquet $D_/$hive/ref_gl_ilc.parquet --side $fs --from $ff >> $J 2>&1 || { log "pf_arms ep$e: hold_freeze FAILED" >> $J; continue; }
    else cp $I/ep$e/P.parquet $D_/$hive/ref_gl_ilc.parquet; fi   # p0 / plw / pm / p0m: a byte copy of P
    if [ $a = pm ] || [ $a = p0m ]; then                            # (pf-mesh PREREG) Tier B collision: the mesh file only, in the
      AR=$(python -c "import os, sys, pyarrow.parquet as pq; print(os.path.dirname(os.path.dirname(pq.read_table(sys.argv[1]).column('object_urdf_paths')[0].as_py()[0])))" $D_/$hive/ref_gl_ilc.parquet)
      AR=${AR/#\/workspace\//\/content\/}; mv_=MESH_OBJS_EP$e            # the asset copy the reference itself names (URDF inertia / feet kept)
      for o in ${!mv_:?MESH_OBJS_EP$e}; do f=$AR/mesh/$o/$o.glb
        [ -f $f ] || { log "pf_arms ep$e: $a: no $f: episode DROPPED" >> $J; BADM=1; break; }
        [ -f $f.lib_orig ] || cp $f $f.lib_orig; cp $REPO_DIR/meshes/tierB_collision/$o.glb $f
        log "pf_arms ep$e: $a: collision mesh $f <- meshes/tierB_collision/$o.glb md5 $(md5sum < $f | cut -c1-12) (was $(md5sum < $f.lib_orig | cut -c1-12))" >> $J
      done
    fi
    mkdir -p /content/results/${pre}_glock_public/ep$e
    for f in $(tabl $e result_files); do pull1 $f && cp $HS/$f /content/results/${pre}_glock_public/ep$e/; done
    log "pf_arms ep$e: arm $a s$s on the packed reference: $D_/$hive/ref_gl_ilc.parquet md5 $(md5sum < $D_/$hive/ref_gl_ilc.parquet | cut -c1-12) (P $(md5sum < $I/ep$e/P.parquet | cut -c1-12))" >> $J
  done; done
  [ -n "${BADM:-}" ] && { unset BADM; continue; }                   # (pf-mesh) a collision swap failed: no training, no zero-shot
  log "pf_arms ep$e: base $B (md5 $(md5sum < $B | cut -c1-12)); arm copies made" >> $J; OK="$OK $e"
done
OK=${OK# }; [ -n "$OK" ] || { log "pf_arms: no episode has its inputs" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
[ $SPLIT = eval ] && { python $T/no_oracle.py $(for e in $OK; do echo /content/refs/perc2mck/ep$e $I/ep$e; [ -d /content/refs/sf/ep$e ] && echo /content/refs/sf/ep$e; done) > $G/no_oracle_inputs.txt 2>&1 \
  || { log "pf_arms: no_oracle refused an input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }; }

# ----- confirmation draws on the pristine evaluator (also the zero-shot check)
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

# ----- 1b. (pf-mesh PREREG) Tier B collision arms: library copy for sm; zero-shot contact check of the BOARD policy
STD_ARM=$(for e in $STD_EPS; do arms_of $e; done | sort -u | tr '\n' ' '); STD_ARM=${STD_ARM% }
[ $(echo $STD_ARM | wc -w) -le 1 ] || { log "pf_arms: one standard-learner arm per box (got [$STD_ARM])" >> $J; exit 1; }
if [ "$STD_ARM" = sm ]; then                                      # library_v3 (the table's) + meshes/tierB_collision/<obj>.glb
  LIB_TB=/content/lib_tb; rm -rf $LIB_TB; cp -r $REPO_DIR/meshes/$(tabl $(echo $STD_EPS | cut -d' ' -f1) lib) $LIB_TB
  for e in $STD_EPS; do mv_=MESH_OBJS_EP$e; for o in ${!mv_:?MESH_OBJS_EP$e}; do
    [ -f $LIB_TB/$o.glb ] || { log "pf_arms: sm: $o.glb not in the library" >> $J; exit 1; }
    cp $REPO_DIR/meshes/tierB_collision/$o.glb $LIB_TB/$o.glb; log "pf_arms ep$e: sm: collision library $LIB_TB/$o.glb <- meshes/tierB_collision/$o.glb md5 $(md5sum < $LIB_TB/$o.glb | cut -c1-12)" >> $J
  done; done
  pc=$(tabl $(echo $STD_EPS | cut -d' ' -f1) pieces); [ "$pc" = None ] && pc=""
  python $P/make_assets.py $LIB_TB /content/assets ${pc:+--pieces $REPO_DIR/$pc} >> $J 2>&1 || { log "pf_arms: sm: make_assets FAILED" >> $J; exit 1; }
fi
zeroshot() {  # $1 ep: one official draw of the board checkpoint with the new collision; refuse the episode on any overflow
  local e=$1 ckf ck rp ov svr
  ckf=$(tabl $e packed_checkpoint); pull1 $ckf || { log "pf_arms ep$e: zero-shot: checkpoint pull FAILED" >> $J; return 1; }
  ck=$I/ep$e/board.safetensors; cp $HS/$ckf $ck
  [ "$(sha256sum < $ck | cut -c1-64)" = "$(tabl $e packed_sha256)" ] || { log "pf_arms ep$e: zero-shot: board checkpoint sha256 mismatch" >> $J; return 1; }
  rp=$(python -c "
import json, struct, sys
b = open(sys.argv[1], 'rb'); n = struct.unpack('<Q', b.read(8))[0]; c = json.loads(json.loads(b.read(n))['__metadata__']['user.resolved_config_json'])
def find(d):
    if isinstance(d, dict):
        if isinstance(d.get('reference'), dict) and 'parquet' in d['reference']: return d['reference']['parquet']
        for v in d.values():
            r = find(v)
            if r: return r
print(find(c) or '')" $ck)
  [ -n "$rp" ] || { log "pf_arms ep$e: zero-shot: no reference path in the checkpoint config" >> $J; return 1; }
  if [ ! -s "$rp" ]; then mkdir -p $(dirname $rp); cp $I/ep$e/P.parquet $rp; fi   # the board's own reference (md5 = the table's)
  rr=${rp%%/processed/*}                                            # FlashCHORD reads <root>/reconstructed_stage/<seq>_support.usda
  if [ ! -d $rr/reconstructed_stage ]; then
    st=$(dirname $(dirname $(dirname $(dirname /content/$(tabl $e reference)))))/reconstructed_stage; [ -d $st ] || st=/content/refs/perc2mck/ep$e/reconstructed_stage
    [ -d $st ] || { log "pf_arms ep$e: zero-shot: no support stage for $rr" >> $J; return 1; }
    cp -r $st $rr/; log "pf_arms ep$e: zero-shot: support stage $st -> $rr/reconstructed_stage" >> $J
  fi
  [ "$(md5sum < $rp | cut -c1-32)" = "$(tabl $e md5)" ] || { log "pf_arms ep$e: zero-shot: $rp is not the board reference (md5)" >> $J; return 1; }
  NCONF=1 confirm $e $ck $G/zeroshot_ep$e
  ov=$(grep -ac 'overflow - please' $G/zeroshot_ep$e/r1/eval.log 2> /dev/null); [ -f $G/zeroshot_ep$e/r1/eval.log ] || ov=NA
  svr=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $G/zeroshot_ep$e/r1/ep$e/qa_policy.json 2> /dev/null || echo none)
  log "pf_arms ep$e: zero-shot (board policy, new collision): sim_vs_ref $svr, overflow lines $ov" >> $J
  [ "$ov" = 0 ] && [ "$svr" != none ]
}
for e in $OK; do                                                    # zero-shot contact budget before any training
  case " $(arms_of $e) " in *" pm "*|*" p0m "*|*" sm "*) zeroshot $e || { log "pf_arms ep$e: REFUSED by the zero-shot contact check (no training)" >> $J; OK=$(echo " $OK " | sed "s/ $e / /; s/^ //; s/ $//"); STD_EPS=$(echo " $STD_EPS " | sed "s/ $e / /; s/^ //; s/ $//"); } ;; esac
done
[ -n "$OK" ] || { log "pf_arms: no episode left after the zero-shot check" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }

# ----- 2. training: one glock_public.sh invocation per seed, every (episode, arm) of it in waves of 2
for s in $SEEDS; do
  PP=""; for e in $OK; do case " $STD_EPS " in *" $e "*) continue ;; esac; for a in $(arms_of $e); do PP="$PP $e:local:mck:pf${a}s$s"; export GL_ARGS_pf${a}s$s="$(gl_of $a)"
    case $a in lw|plw|pm)                                          # (pf-lift PREREG) lift-window starts, this pair's training only
      W_=$(python $T/lift_windows.py $(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet | head -1)) || { log "pf_arms ep$e: lift_windows FAILED" >> $J; continue; }
      export TRAIN_ENV_pf${a}s${s}_ep$e="FC_LIFT_WINDOWS=$W_ FC_LIFT_P=${LIFT_P:-0.3} FC_LIFT_SEED=$s"; export FC_LIFT_PATCH=1   # per episode
      log "pf_arms ep$e $a s$s: lift windows [$W_] share ${LIFT_P:-0.3}" >> $J ;;
    esac; done; done
  if [ -n "${PP# }" ]; then
  label "pf arms: seed $s [$PP ]"; log "pf_arms: seed $s, PAIRS [${PP# }]" >> $J; t0=$(date +%s)
  RU=""; case " $ARMS $(for e in $OK; do arms_of $e; done) " in *" p0 "*|*" pz "*|*" plw "*|*" pm "*|*" p0m "*) RU="REUSE_REF=1 REQUIRE_REUSE=1" ;; esac   # all arms of the box then reuse
  ( [ -n "$RU" ] && export $RU; SEED=$s PAIRS="${PP# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "pf_arms: seed $s returned $?" >> $J
  log "pf_arms: seed $s took $(( ($(date +%s) - t0) / 60 )) min" >> $J
  fi
  if [ -n "${STD_EPS# }" ]; then                                   # (pf-lift addendum C) arm slw: the packed standard-learner
    # recipe of mass_eval.sh MODE=std (FDR + VOC + deployment-exact starts 0.25, 250,003,456 steps, sweep 0.4 / 0.6 / 0.8,
    # CR=0 byte copy refs/perc2mcklw of the packed base, NREP 10) + lift-window starts (ENV_EP<N>, training and box draws)
    t0=$(date +%s); PS=""; case $STD_ARM in slw) SUF_=lw ;; sm) SUF_=tb ;; s0) SUF_=s0 ;; esac
    for e in $STD_EPS; do PS="$PS $e:local:mck"; done
    ( unset STEPS SF SETTLE REPLAN EVOLVE CURVE_REP TRAIN_SLOTS PIECES; LIBS=""; PCS=""
      for e in $STD_EPS; do LIBS="$LIBS $(tabl $e lib)"; v=$(tabl $e pieces); PCS="$PCS ${v/None/-}"; done
      [ $(echo $LIBS | tr ' ' '\n' | sort -u | wc -l) = 1 ] && [ $(echo $PCS | tr ' ' '\n' | sort -u | wc -l) = 1 ] \
        || { log "pf_arms slw: episodes [$STD_EPS ] need one library / pieces (got [$LIBS ] / [$PCS ])" >> $J; exit 1; }
      export LIB=$REPO_DIR/meshes/$(echo $LIBS | cut -d' ' -f1); export MESH_DIR=$LIB; pc=$(echo $PCS | cut -d' ' -f1)
      [ "$pc" != - ] && export PIECES=$REPO_DIR/$pc
      export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
      [ "$STD_ARM" = sm ] && { export LIB=$LIB_TB MESH_DIR=$LIB_TB; }          # (pf-mesh) Tier B collision library copy
      for e in $STD_EPS; do
        [ "$STD_ARM" = slw ] || { log "pf_arms ep$e $STD_ARM s$s: LIB $LIB PIECES ${PIECES:-none}" >> $J; continue; }
        export FC_LIFT_PATCH=1
        W_=$(python $T/lift_windows.py $(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet | head -1)) || { log "pf_arms ep$e: lift_windows FAILED" >> $J; exit 1; }
        export ENV_EP$e="FC_LIFT_WINDOWS=$W_ FC_LIFT_P=${LIFT_P:-0.3} FC_LIFT_SEED=$s"
        log "pf_arms ep$e slw s$s: lift windows [$W_] share ${LIFT_P:-0.3}; LIB $LIB PIECES ${PIECES:-none}" >> $J
      done
      label "pf arms: $STD_ARM seed $s [$PS ]"; log "pf_arms: $STD_ARM seed $s, PAIRS [${PS# }]" >> $J
      SPLIT=eval PDIR_ROOT=/content/perc2 SUF=$SUF_ CR=0 BASE_EVAL=0 NREP=10 SEED=$s MA_ARGS= EVAL_TIMEOUT=1200 NO_PUSH=1 \
        PAIRS="${PS# }" bash $REPO_DIR/ops/jobs/hard_ab.sh ) || log "pf_arms: $STD_ARM seed $s returned $?" >> $J
    for e in $STD_EPS; do                                          # the glock layout, so choice / confirmation / verdict are shared
      H=/content/results/hard_ab/ep$e/mck$SUF_-s$s; D_=/content/results/pf${STD_ARM}s${s}_glock_public/ep$e/best; mkdir -p $D_
      ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $H/summary.json 2> /dev/null)
      [ -s "$ck" ] || { log "pf_arms ep$e $STD_ARM s$s: no checkpoint in $H/summary.json" >> $J; continue; }
      cp $H/summary.json $D_/; cp -r $H/r* $D_/; cp $ck $D_/policy.safetensors; echo $ck > $D_/source_checkpoint.txt
      log "pf_arms ep$e $STD_ARM s$s: $(basename $ck) sha256 $(sha256sum < $ck | cut -c1-12), box draws $(python -c "import json, sys; print(json.load(open(sys.argv[1])).get('sim_vs_ref'))" $H/summary.json)" >> $J
    done
    log "pf_arms: $STD_ARM seed $s took $(( ($(date +%s) - t0) / 60 )) min" >> $J
  fi
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: interim push FAILED" >> $J
done
for e in $OK; do for s in $SEEDS; do for a in $(arms_of $e); do        # stored config of every chosen checkpoint
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
for e in $OK; do
  E6=$(printf %06d $e)
  for i in $(seq 1 10); do for x in parquet json; do              # the packed policy's fresh draws (H5p7)
    pdv=PACKED_DRAWS_EP$e; f=runs/$H5P7_RUN/results/h5/r$i/ep$e/episode_$E6.$x; [ -n "${!pdv:-}" ] && f=${!pdv}/r$i/ep$e/episode_$E6.$x   # (pf-lift) the pack-12b policy's own 10 draws
    PULL_RETRY_S=5 pull1 $f && mkdir -p $I/ep$e/packed_h5/r$i && cp $HS/$f $I/ep$e/packed_h5/r$i/
  done; done
  OLD=runs/20261026-pack6-5203d42/results/submission/results/episode_$E6   # the board pack's old packed draw (pack 6)
  odv=OLD_EP$e; [ -n "${!odv:-}" ] && OLD=${!odv}                   # (pf-lift) the board pack's row of this episode
  for x in parquet json; do PULL_RETRY_S=5 pull1 $OLD.$x && mkdir -p $I/ep$e/old/r1 && cp $HS/$OLD.$x $I/ep$e/old/r1/; done
  for a in $(arms_of $e); do
    python $T/pf_verdict.py choose --results /content/results --ep $e --arm $a --seeds "$SEEDS" --h5 $I/ep$e/packed_h5 --out $G/choice_ep${e}_$a.json $([ -f $I/ep$e/BRIDGED ] && echo --nogate) > $G/choice_ep${e}_$a.txt 2>&1; rc=$?
    log "pf_arms ep$e $a choice + gate: $(cut -c1-700 $G/choice_ep${e}_$a.txt)" >> $J
    if [ $rc = 0 ]; then
      ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $G/choice_ep${e}_$a.json)
      if python $T/no_oracle.py $ck > $G/no_oracle_ck_ep${e}_$a.txt 2>&1; then confirm $e $ck $G/conf_ep${e}_$a
      else log "pf_arms ep$e $a: no_oracle refused the chosen checkpoint" >> $J; fi
    fi
    sets=(--set "conf:P:$G/conf_ep${e}_$a/r*/ep$e/episode_$E6.parquet" --set "old:P:$I/ep$e/old/r1/episode_$E6.parquet" --set "packed:P:$I/ep$e/packed_h5/r*/episode_$E6.parquet")
    for s in $SEEDS; do sets+=(--set "train$s:P:/content/results/pf${a}s${s}_glock_public/ep$e/best/r*/episode_$E6.parquet"); done
    REFS=(--ref P=$I/ep$e/P.parquet); VREFS="P"
    if [ -f $I/ep$e/BRIDGED ]; then                                 # the candidate trained on P' (bridged): scored vs P and P'
      cs=$(python -c "import json, sys; print(json.load(open(sys.argv[1])).get('chosen') or '')" $G/choice_ep${e}_$a.json 2> /dev/null)
      PB=$(ls /content/refs/pf${a}s${cs:-42}_glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
      [ -s "$PB" ] && { REFS+=(--ref B=$PB); VREFS="P B"; sets[1]="conf:B:$G/conf_ep${e}_$a/r*/ep$e/episode_$E6.parquet"
        for s in $SEEDS; do sets+=(--set "trainB$s:B:/content/results/pf${a}s${s}_glock_public/ep$e/best/r*/episode_$E6.parquet"); done; }
    fi
    python $T/dr_score.py --kit $KIT --lib $LIB --ep $e "${REFS[@]}" --out $G/score_ep${e}_$a.json "${sets[@]}" > $G/score_ep${e}_$a.txt 2>&1 \
      || log "pf_arms ep$e $a: scoring FAILED ($(tail -2 $G/score_ep${e}_$a.txt | tr '\n' ' ' | cut -c1-300))" >> $J
    for r in $G/conf_ep${e}_$a/r*/ep$e; do python $T/simref_timeline.py $r $e --kit $KIT --names $(tabl $e objects | tr ' ' ,) --json $r/timeline.json > /dev/null 2>&1; done
    python $T/pf_verdict.py eval --score $G/score_ep${e}_$a.json --choice $G/choice_ep${e}_$a.json --table $TAB --ep $e --refs "$VREFS" --out $G/verdict_ep${e}_$a.json > $G/verdict_ep${e}_$a.txt 2>&1
    log "pf_arms ep$e $a RESULT: $(cut -c1-2500 $G/verdict_ep${e}_$a.txt)" >> $J; label "pf arms ep$e $a: $(head -c 60 $G/verdict_ep${e}_$a.txt)"
    bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: interim push FAILED" >> $J
  done
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_arms: push FAILED (self_destroy retries)" >> $J
