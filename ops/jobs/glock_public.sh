#!/bin/bash
# Public validation of the grasp-lock recipe (2026-10-23; owner go-ahead, 2 Max-Q boxes ≈ $4–5). The recipe that took
# the eval spoon episodes to sim_vs_ref ≈ 0.97 (docs/research/notes/24), FROZEN as below, on public episodes that have
# references built with our own meshes, scored against mocap afterwards (registered AUC with our meshes, evaluation only):
#   1. reference = the stored own-mesh reference of a finished run (store pull-run; EP:RUN:BASE as in hard_ab.sh);
#      RUN=new builds it here from the raw episode, end to end as for an eval episode: perception (perc2, our
#      library), hands, mkref (wrist cost 3.0, capped lead-in), contact retargeting with rest settling (variant mck,
#      the 22 Oct ep18 fix), i.e. EP:new:mck;
#      with SF=1 (default since 2026-10-23) its meshes are made support-consistent first (pipeline/support_fill.py:
#      a resting pose the mesh cannot hold gets the smallest certified underside fill; public ep18's brush fell over);
#      SETTLE=1 then settles the start in the simulator (tools/sim_settle.py: frozen frame 0, object assist on, then
#      off; each object's settled pose until its first hold closes): no start jolt from overlapping collision pieces;
#   2. pipeline/grasp_lock.py with GL_ARGS (single-hand carry per object, anatomy closing, palm press, wrap only where
#      the human holds a narrow part, copied grasps snapped to the surface), lift feed-forward for the kp 400 wrist;
#   3. pipeline/wrist_ilc.py with the kp 400 embodiment (EMB=sharpa_hands_mid);
#      ILC_HOLD=1 (2026-10-26): object-level ILC while a hand carries an object (wrist_ilc.py --hold; ILC_ITERS, ILC_GAIN),
#      keeping the best-scoring iteration (eval 10: the beige cup sat 3-6 cm low in the grip and hit the blue cup's rim);
#   4. zero-action replay (tools/trace_rollout.py) scored with tools/trace_score.py (sim_vs_ref, our reference) and
#      checked by tools/rest_check.py (every object stays within 5 mm / 2 deg until a hand comes for it);
#      With REPLAN=N (> 0) the holds are then re-planned against the simulated world up to N times (grasp_lock.py
#      --sim_trace: an object that is off its reference before its grasp is grasped where it lies and carried back);
#      a re-planned version is kept only if its zero-action sim_vs_ref is at least the previous one (no ground truth);
#      EVOLVE=1 (2026-10-24) first refines each hold's grasp by an evolutionary search in the simulator (tools/grasp_evolve.py:
#      CMA-ES over a wrist offset + rotation + finger offsets, EV_POP worlds per generation = EV_POP / EV_ROBUST candidates,
#      each run as EV_ROBUST copies jittered by EV_JITTER (fitness = their mean: ep18's physics is chaotic), EV_GENS
#      generations, fitness = ADD AUC vs OUR reference over the hold window; the best edit is baked in). Put --onset_anchor 1 in GL_ARGS to lock
#      each hold from the object's motion onset (ep39 / ep18 / ep24: the object moves before the human hand track has it);
#   5. RL fine-tune: embodiment=sharpa_hands_mid, FDR rewards + VOC fix (lib.sh fc_patches), STEPS (70M), SEED;
#      FC_DROP_START=p adds recovery training (ops/box/patch_flashchord_drop.py: drop starts, training process only);
#      ES=1: early stopping (tools/early_stop.sh; STEPS is then the cap): checkpoints scored as they appear (ES_N
#      official evaluations, sim_vs_ref), stop at two in a row >= ES_TARGET or no new best for ES_PATIENCE steps;
#      CURR_SCALE=s scales the curriculum's step thresholds (s=0.4: object assist 0 from 49M instead of 123M);
#   6. official evaluation of every checkpoint (tools/ckpt_curve.sh, sim_vs_ref), checkpoint chosen by sim_vs_ref only
#      (no ground truth), then NREP official evaluations of it, each scored sim_vs_ref + registered AUC vs mocap.
# SPLIT=eval (2026-10-24): eval episodes, EP:new:mck only; the reference is built from the eval videos (no ground truth
# exists), the policies are scored against our reference only (pipeline/qa.py sim_vs_ref) and nothing is scored vs mocap.
# Episodes listed together run concurrently; at most TRAIN_SLOTS (2) trainings share the GPU at a time, the others wait,
# and a training that still runs out of GPU memory is retried twice. REUSE_REF=1 (2026-10-24) skips the reference stages
# of an episode whose reference is finished on this box (e.g. its training failed) and trains on it.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> \
#     'PAIRS="24:20261021-auto24-966eb96:mcs 27:20261021-auto18-966eb96:auto" bash ops/jobs/glock_public.sh'
# RUN "local" (2026-10-30) = a reference already built on this box (nothing pulled). A 4th field EP:RUN:BASE:PERC
# names the perception prefix of the base reference refs/<PERC><BASE>/ep<N> (default perc2). PERC other than perc2
# (the oracle twins, ops/jobs/oracle_twins.sh: PERC=oracle, a reference whose object motion is mocap) is for SPLIT=public
# and RUN local only, and keeps every working folder apart with the prefix "<PERC>_" (refs/oracle_sf, refs/oracle_glock,
# refs/oracle_glockt, runs/oracle_glock, results/oracle_glock_public, /content/oracle_glock_ep<N>.log), so the same
# episode can train on both references at once and nothing an eval pack pulls (refs/glockt, refs/sf) holds it.
# ENV_EP<N> (2026-10-30, as in hard_ab.sh): space-separated VAR=value settings for episode N only (both of its entries),
# e.g. ENV_EP11="SF=0" ENV_EP13="SF=1".
# REF_ONLY=1 (2026-10-31, ops/jobs/mass_check.sh): stop each episode after its reference stages (no training), e.g. to
# build one reference that several arms then train on with REUSE_REF=1. NO_PUSH=1: no store push at the end (the
# calling job pushes once). EVAL_TIMEOUT=<s>: cut an official evaluation that runs longer (a stalled evaluation
# otherwise holds the box until the 30-min watchdog destroys it; physics p3ms1, 31 Oct): timeout -k 60, so one that
# ignores SIGTERM is killed 60 s later; each evaluation folder then gets eval_rc.txt (its exit code: 124 cut, 137 killed
# after the grace) so the cuts can be counted (tools/mass_verify.py). REQUIRE_REUSE=1 (with REUSE_REF=1): exit before
# anything runs if any pair has no finished reference on this box (no silent rebuild). All four are off by default.
# 2026-10-31 (masses eval retrain, ops/jobs/mass_eval.sh): a PERC prefix mass<A>s<seed> (tools/mass_arm.py's per-arm copy of
# an eval episode's stored reference) is also allowed with SPLIT=eval, RUN local and REQUIRE_REUSE=1 only (no perception
# and no reference stage runs on an eval episode); CURR_SCALE in ENV_EP<N> scales that episode's curriculum only (before,
# CURR_SCALE was read once for the whole job, so ENV_EP<N>="CURR_SCALE=..." had no effect on training).
# EVAL_LOCAL_REF=1 (2026-10-31, eval-10 V4p retrain, ops/jobs/ev10_v4p.sh; opt-in, off by default): with SPLIT=eval, eval 10
# may also use a PERC prefix perc2e10v (the reference stages, REF_ONLY=1, on the V4p base reference refs/perc2e10vmck/ep10
# that the job built on this box) or perc2e10vs<seed> (its per-seed copies), RUN local; folders refs/perc2e10v*_glock*,
# results/perc2e10v*_glock_public. Unset, every PERC decision is exactly as before.
# FC_DR_PATCH=1 (2026-10-31, pack 9b D arm, ops/jobs/mass_eval.sh ARM=dr; docs/research/work/pack9b-20261031/PREREG.md;
# opt-in, off by default): ops/box/patch_flashchord_dr.py is applied right after fc_patches (start-state randomisation
# of sampled training resets; the patched tree is inert unless FC_DR_RESET is set in a process; the caller passes
# FC_DR_RESET / FC_DR_SEED to the training process only, through TRAIN_ENV). With it, SPLIT=eval also accepts a PERC
# prefix drs<seed> (the D arm's byte copy of a packed eval reference, tools/dr_arm.py) with RUN local and
# REQUIRE_REUSE=1 only; folders refs/drs<seed>_glock*, runs/drs<seed>_glock, results/drs<seed>_glock_public. Unset,
# nothing of this runs.
# EVAL_NJ_DIAG=1 (2026-11-01, eval-10 njmax diagnostic, ops/jobs/ev10_nj.sh; docs/research/work/eval10-njmax-20261101/;
# opt-in, off by default): with SPLIT=eval, eval 10 may also use a PERC prefix perc2e10njs<seed> (the diagnostic's byte copy
# of e10v's stored V4p reference) with RUN local and REQUIRE_REUSE=1 only; folders refs/perc2e10njs<seed>_glock*,
# runs/perc2e10njs<seed>_glock, results/perc2e10njs<seed>_glock_public (tools/no_oracle.py refuses every one of them: the
# caller trains them with TRAIN_ARGS="sim.njmax=1024 sim.nconmax=512", changed physics, never packed). Unset, every PERC
# decision is exactly as before.
# Summary: /content/results/glock_public/summary.json; per-episode logs /content/glock_ep<N>.log. Each rollout's
# summary row also holds ref_auc / floor_auc (public): its reference and the static floor vs mocap.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; T=$REPO_DIR/tools; J=${J:-/content/job.log}; NREP=${NREP:-5}; PAR=${PAR:-3}; SEED=${SEED:-42}
SPLIT=${SPLIT:-public}; SETTLE=${SETTLE:-0}; SF=${SF:-1}; REPLAN=${REPLAN:-0}; ES=${ES:-0}; STEPS=${STEPS:-70004736}; PAIRS=${PAIRS:-"24:20261021-auto24-966eb96:mcs 27:20261021-auto18-966eb96:auto"}
GL_ARGS=${GL_ARGS:-"--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1"}
# FlashCHORD requires total_environment_steps divisible by the world count (4096; 27 Oct: STEPS=30000128 failed at the
# training start after 22 min of reference building)
ST4=$(( STEPS / 4096 * 4096 )); [ "$ST4" != "$STEPS" ] && echo "[$(date -u +%FT%TZ)] STEPS $STEPS -> $ST4 (multiple of 4096)" >> ${J:-/content/job.log}; STEPS=$ST4
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} ASSETS=/content/assets
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/glock_public; mkdir -p $O
log "glock_public code $(git -C $REPO_DIR rev-parse --short HEAD), pairs [$PAIRS], seed $SEED, steps $STEPS, NREP $NREP, SPLIT $SPLIT, SETTLE $SETTLE, SF $SF, REPLAN $REPLAN, EVOLVE ${EVOLVE:-0} (worlds ${EV_POP:-256}, robust ${EV_ROBUST:-4}, gens ${EV_GENS:-20}), DROP ${FC_DROP_START:-0}, ES $ES (target ${ES_TARGET:-0.9}), CURR_SCALE ${CURR_SCALE:-1}, GL_ARGS [$GL_ARGS]" >> $J
[ -n "${REF_ONLY:-}${NO_PUSH:-}${EVAL_TIMEOUT:-}${REQUIRE_REUSE:-}" ] && log "glock_public: REF_ONLY ${REF_ONLY:-0}, NO_PUSH ${NO_PUSH:-0}, EVAL_TIMEOUT ${EVAL_TIMEOUT:-none}, REQUIRE_REUSE ${REQUIRE_REUSE:-0}" >> $J
if [ "${REQUIRE_REUSE:-0}" = 1 ]; then                           # every pair must train on this box's finished reference
  [ "${REUSE_REF:-0}" = 1 ] || { log "glock_public: REQUIRE_REUSE=1 needs REUSE_REF=1; nothing run" >> $J; exit 1; }
  for x in $PAIRS; do                                            # one()'s REUSE_REF condition, before anything runs
    IFS=: read -r ep_ run_ base_ perc_ <<< "$x"; pre_=; [ -n "$perc_" ] && [ "$perc_" != perc2 ] && pre_=${perc_}_
    ls /content/refs/${pre_}glockt/ep$ep_/processed/*/*/ref_gl_ilc.parquet > /dev/null 2>&1 \
      && [ -f /content/results/${pre_}glock_public/ep$ep_/rest_check.json ] \
      || { log "glock_public: REQUIRE_REUSE: pair $x has no finished reference on this box (refs/${pre_}glockt/ep$ep_/processed/*/*/ref_gl_ilc.parquet and results/${pre_}glock_public/ep$ep_/rest_check.json); nothing rebuilt or trained" >> $J; exit 1; }
  done
fi
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit budget_mesh (score_registered --meshes); support_fill union
# PIECES (2026-10-26): collision-copy pieces (e.g. meshes/carve/ev10, the hybrid cups) for the simulator copy, as in
# hard_ab.sh; use with SF=0 (support_fill would rebuild those objects' collision from the library mesh). References
# without SF name /content/assets (fix_assets), so they train and evaluate on the pieces.
python $P/make_assets.py $MESH_DIR $ASSETS ${PIECES:+--pieces $PIECES} ${MA_ARGS:-} >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
[ -n "${PIECES:-}" ] && log "glock_public: collision pieces from $PIECES ($(ls $PIECES | tr '\n' ' '))" >> $J
fc_patches $J || exit 1                                          # FDR rewards + VOC fix; sets TRAIN_ARGS (curriculum, weights)
if [ "${FC_DR_PATCH:-0}" = 1 ]; then                             # (2026-10-31, pack 9b D arm) after fc_patches; inert unless
  python $REPO_DIR/ops/box/patch_flashchord_dr.py $FC >> $J 2>&1 || { log "FlashCHORD DR patch FAILED" >> $J; exit 1; }   # FC_DR_RESET is set
  log "patched FlashCHORD (start-state randomisation of sampled training resets, ops/box/patch_flashchord_dr.py md5 $(md5sum < $REPO_DIR/ops/box/patch_flashchord_dr.py | cut -c1-12)); training env [${TRAIN_ENV:-}]" >> $J
fi
case " $PAIRS" in *:new:*) ensure_gdino $J ;; esac              # perception runs here: detection grounding term (2026-10-24:
                                                                 # missing on the 24 Oct eval boxes, so that term was off)
curr_thresholds() { python -c "s = $1; t = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]; print('[' + ','.join(str(int(x * s)) for x in t) + ']')"; }
CURR_SCALE_JOB=${CURR_SCALE:-}; TRAIN_ARGS_UNSCALED=$TRAIN_ARGS   # one() rescales an episode whose ENV_EP<N> sets CURR_SCALE
if [ -n "${CURR_SCALE:-}" ]; then                               # curriculum thresholds scaled to the planned length
  TRAIN_ARGS="$TRAIN_ARGS curriculum.thresholds=$(curr_thresholds $CURR_SCALE)"
  log "curriculum thresholds scaled by $CURR_SCALE: TRAIN_ARGS [$TRAIN_ARGS]" >> $J
fi
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml   # kp 400 wrist (the checkpoint stores the resolved config)
[ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }
for run in $(for x in $PAIRS; do echo $x | cut -d: -f2; done | sort -u | grep -v '^new$\|^local$'); do
  bash $OPS/store.sh pull-run $run >> $J 2>&1 || { log "pull-run $run FAILED" >> $J; exit 1; }
done

fix_assets() {  # the reference names absolute asset paths of the box that built it; point a missing root at ours
  python - "$1" << 'EOF'
import os, sys, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1])
for r in sorted({os.path.dirname(os.path.dirname(p)) for p in t.column('object_urdf_paths')[0].as_py() if not os.path.exists(p)}):
    if r.startswith('/content/') and not os.path.lexists(r):
        os.symlink('/content/assets', r); print('linked', r, '-> /content/assets')
    else:
        print('MISSING assets under', r); sys.exit(1)
EOF
}

train_slot() {  # take one of TRAIN_SLOTS GPU training slots and print its number. One FlashSAC training (4,096 worlds)
                # peaks at 40.4 GB; a third one beside two others ran out of memory on the 96 GB card (evF, 2026-10-24)
  local s
  while :; do
    for s in $(seq 1 ${TRAIN_SLOTS:-2}); do mkdir /content/train_slot_$s 2> /dev/null && { echo $s; return; }; done
    sleep 30
  done
}
rmdir /content/train_slot_* 2> /dev/null                         # stale slots of a job stopped on this box

evalrep() {  # $1 checkpoint, $2 output dir, $3 episode: NREP official evaluations, each scored (as in hard_ab.sh)
  local ck=$1 d=$2 ep=$3 E6 i pids=()
  E6=$(printf %06d $ep); mkdir -p $d
  for i in $(seq 1 $NREP); do
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false ${EVAL_TIMEOUT:+timeout -k 60 $EVAL_TIMEOUT} .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1
      rc_=$?; [ -n "${EVAL_TIMEOUT:-}" ] && echo $rc_ > $d/r$i/eval_rc.txt   # 124 cut, 137 killed after the 60 s grace
      [ $rc_ = 0 ] && python $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
      && { [ "$SPLIT" = eval ] || python $P/score_registered.py $ep $d/r$i --meshes $MESH_DIR > /dev/null 2>&1; } ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  python - $d $ep $ck << 'EOF' > $d/summary.json
import glob, json, os, sys
import numpy as np
d, ep, ck = sys.argv[1], int(sys.argv[2]), sys.argv[3]; rows = []
for r in sorted(glob.glob(f'{d}/r*/')):
    try:
        q = json.load(open(f'{r}qa_policy.json')); row = dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=q['sim_vs_ref'])
        if os.path.exists(f'{r}score_registered_ep{ep}.json'):          # public episodes only (vs mocap)
            sr = json.load(open(f'{r}score_registered_ep{ep}.json')); s = sr['sim']; row.update(auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR'])
            row.update({k: sr[n]['AUC'] for k, n in (('ref_auc', 'reference'), ('floor_auc', 'static_floor')) if n in sr})
        rows.append(row)
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'sim_vs_ref' in x]; agg = {}
for k in ('sim_vs_ref', 'auc', 'ref_auc', 'floor_auc'):
    v = np.array([x[k] for x in ok if k in x], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4))
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

one() {
  local ep=$1 run=$2 base=$3 perc=${4:-perc2} pre="" tg=ep$1 O=$O R0 P0 hive G RD N RUN LG ck reuse=0 ev=ENV_EP$1
  if [ "$perc" != perc2 ]; then                                    # e.g. the oracle twins: folders apart, public only;
    if [ "$SPLIT" = eval ]; then                                   # an eval episode's mass-arm copy (mass_eval.sh): reuse only
      if [[ $perc =~ ^drs[0-9]+$ ]]; then                          # (2026-10-31) the D arm's byte copy: FC_DR_PATCH only
        { [ "$run" = local ] && [ "${REQUIRE_REUSE:-0}" = 1 ] && [ "${FC_DR_PATCH:-0}" = 1 ]; } \
          || { log "glock ep$ep: PERC $perc (D arm) with SPLIT=eval needs RUN local, REQUIRE_REUSE=1 and FC_DR_PATCH=1" >> $J; return 1; }
      else
      { [[ $perc =~ ^mass[0-9]+s[0-9]+$ ]] && [ "$run" = local ] && [ "${REQUIRE_REUSE:-0}" = 1 ]; } \
        || { [ "${EVAL_LOCAL_REF:-0}" = 1 ] && [ "$ep" = 10 ] && [[ $perc =~ ^perc2e10v(s[0-9]+)?$ ]] && [ "$run" = local ]; } \
        || { [ "${EVAL_NJ_DIAG:-0}" = 1 ] && [ "$ep" = 10 ] && [[ $perc =~ ^perc2e10njs[0-9]+$ ]] && [ "$run" = local ] && [ "${REQUIRE_REUSE:-0}" = 1 ]; } \
        || { log "glock ep$ep: PERC $perc with SPLIT=eval needs a mass<A>s<seed> prefix, RUN local and REQUIRE_REUSE=1" >> $J; return 1; }
      fi
    else
    [ "$SPLIT" = public ] && [ "$run" = local ] || { log "glock ep$ep: PERC $perc needs SPLIT=public and RUN local" >> $J; return 1; }
    fi
    pre=${perc}_; tg="$perc ep$ep"; O=/content/results/${pre}glock_public
  fi
  LG=/content/${pre}glock_ep$ep.log
  if [ -n "${!ev:-}" ]; then                                        # per-episode settings (one() runs in its own subshell)
    eval "export ${!ev}" || { log "glock $tg: bad $ev" >> $J; return 1; }
    log "glock $tg: $ev = ${!ev}" >> $J
    if [ "${CURR_SCALE:-}" != "$CURR_SCALE_JOB" ]; then             # this episode's curriculum (2026-10-31)
      TRAIN_ARGS="$TRAIN_ARGS_UNSCALED${CURR_SCALE:+ curriculum.thresholds=$(curr_thresholds $CURR_SCALE)}"
      log "glock $tg: curriculum thresholds scaled by ${CURR_SCALE:-1} for this episode: TRAIN_ARGS [$TRAIN_ARGS]" >> $J
    fi
  fi
  if [ "${REUSE_REF:-0}" = 1 ] && ls /content/refs/${pre}glockt/ep$ep/processed/*/*/ref_gl_ilc.parquet > /dev/null 2>&1 \
      && [ -f $O/ep$ep/rest_check.json ]; then                     # finish an episode whose training failed on this box:
    reuse=1                                                        # keep its finished reference (grasp lock, ILC, search)
  fi
  if [ "${REQUIRE_REUSE:-0}" = 1 ] && [ $reuse = 0 ]; then         # (e.g. ENV_EP<N> changed it): never rebuild silently
    log "glock $tg: REQUIRE_REUSE: no finished reference on this box; not rebuilt, not trained" >> $J; return 1
  fi
  if [ "$run" = new ] && [ $reuse = 0 ]; then                      # end to end from the raw episode (perception on)
    ( export VARIANT=$base MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STEPS=0 \
        STOP_AFTER=reference SPLIT=$SPLIT PERC=perc2; bash $P/pipeline_ep.sh $ep ) > /content/ref_ep$ep.log 2>&1 \
      || { log "glock $tg: reference build FAILED ($(tail -3 /content/ref_ep$ep.log | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
    log "glock $tg: reference built from the raw episode ($(grep -a 'perception:\|qa_ref\|contact_retarget:' /content/ref_ep$ep.log | cut -c1-160 | tr '\n' ' ' | cut -c1-500))" >> $J
  fi
  if [ "$base" = auto ]; then                                      # the variant auto_ep.sh published for that episode
    base=$(python -c "import json, os; print(os.path.basename(os.path.dirname(json.load(open('/content/results/final/ep$ep/final.json'))['chosen'])).replace('perc2', '', 1))" 2>/dev/null)
    [ -n "$base" ] || { log "glock $tg: no results/final/ep$ep/final.json in the pulled run" >> $J; return 1; }
  fi
  R0=/content/refs/$perc$base/ep$ep; P0=$(ls $R0/processed/*/*/*.parquet 2>/dev/null | head -1)
  [ -s "$P0" ] || { log "glock $tg: no reference under $R0" >> $J; return 1; }
  fix_assets $P0 >> $LG 2>&1 || { log "glock $tg: assets missing" >> $J; return 1; }
  hive=$(dirname ${P0#$R0/}); G=/content/refs/${pre}glock/ep$ep; RD=/content/refs/${pre}glockt/ep$ep; RUN=/content/runs/${pre}glock/ep$ep-s$SEED
  local ts_=$(date +%s)                                           # a pulled run may hold old checkpoints / curve scores for this
  [ -d $RUN ] && [ -n "$(ls -A $RUN 2>/dev/null)" ] && mv $RUN $RUN.pulled_$ts_   # episode (ev3 2026-10-24: ckpt_curve skips scored
  [ $reuse = 0 ] && [ -d $O/ep$ep ] && [ -n "$(ls -A $O/ep$ep 2>/dev/null)" ] && mv $O/ep$ep $O/ep$ep.pulled_$ts_   # checkpoints): keep them aside
  if [ $reuse = 1 ]; then                                          # e.g. another seed on a pulled reference: the earlier
    for d in curve best; do [ -d $O/ep$ep/$d ] && mv $O/ep$ep/$d $O/ep$ep/$d.prev_$ts_; done   # scores must not be reused
    rm -f $O/ep$ep/curve.txt
  fi
  mkdir -p $G/$hive $RD/$hive $RUN $O/ep$ep; cp -r $R0/reconstructed_stage $G/; cp -r $R0/reconstructed_stage $RD/
  log "glock $tg: base $base ($P0)$([ $reuse = 1 ] && echo "; REUSE_REF: training on this box's finished reference $RD/$hive/ref_gl_ilc.parquet")" >> $J
  if [ $reuse = 0 ]; then                                          # reference stages (skipped with REUSE_REF)
  if [ "$SF" = 1 ]; then                                           # support-consistent meshes; the reference then names them
    local SFT=/content/refs/${pre}sf/ep$ep; mkdir -p $SFT/$hive; cp -r $R0/reconstructed_stage $SFT/
    python $P/support_fill.py $P0 $(ls $R0/reconstructed_stage/*.usda | head -1) $SFT/assets $SFT/$hive/ref_sf.parquet > $LG.sf 2>&1 \
      || { log "glock $tg: support_fill FAILED ($(tail -1 $LG.sf | cut -c1-200))" >> $J; return 1; }
    cp $SFT/$hive/ref_sf_support_fill.json $O/ep$ep/support_fill.json; P0=$SFT/$hive/ref_sf.parquet
    log "glock $tg: support_fill $(python -c "
import json; d = json.load(open('$O/ep$ep/support_fill.json'))
print('; '.join(n + (' FILLED ' if o['filled'] else ' as is ') + str([(r.get('frame'), r.get('status', 'skipped'), r.get('fill_cm')) for r in o['fills']]) for n, o in d['objects'].items()))" 2>&1 | cut -c1-600)" >> $J
  fi
  if [ "$SETTLE" = 1 ]; then                                       # settle the start in the simulator
    local SST=/content/refs/${pre}settle/ep$ep; mkdir -p $SST/$hive; cp -r $R0/reconstructed_stage $SST/
    ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/sim_settle.py $P0 $SST/$hive/ref_settled.parquet ) > $LG.settle 2>&1 \
      || { log "glock $tg: sim_settle FAILED ($(tail -1 $LG.settle | cut -c1-200))" >> $J; return 1; }
    cp $SST/$hive/ref_settled_settle.json $O/ep$ep/settle.json; P0=$SST/$hive/ref_settled.parquet
    log "glock $tg: sim_settle $(tail -1 $LG.settle | cut -c1-500)" >> $J
  fi
  ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl.parquet $GL_ARGS ) >> $LG 2>&1 \
    || { log "glock $tg: grasp_lock FAILED" >> $J; return 1; }
  ( cd $FC && EMB=sharpa_hands_mid .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl.parquet $G/$hive/ref_gl_ilc.parquet --iters ${ILC_ITERS:-4} --device cuda \
      ${ILC_HOLD:+--hold $G/$hive/ref_gl_grasp_lock.json --gain ${ILC_GAIN:-0.6}} ) >> $LG 2>&1 \
    || { log "glock $tg: wrist_ilc FAILED" >> $J; return 1; }
  if [ "${EVOLVE:-0}" = 1 ]; then                                  # evolutionary grasp refinement, one hold at a time
    local EV=$O/ep$ep/evolve np_ k; mkdir -p $EV; cp $G/$hive/ref_gl_ilc.parquet $EV/ref_before_evolve.parquet
    np_=$(python -c "import json; print(len(json.load(open('$G/$hive/ref_gl_grasp_lock.json'))['phases']))")
    for k in $(seq 0 $((np_ - 1))); do
      ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/grasp_evolve.py $G/$hive/ref_gl_ilc.parquet $G/$hive/ref_gl_grasp_lock.json \
          $EV/phase$k.json --phase $k --all_objects --pop ${EV_POP:-256} --gens ${EV_GENS:-20} --sigma_pos 0.03 --sigma_fin 0.3 \
          --robust ${EV_ROBUST:-4} --jitter ${EV_JITTER:-0.005} --keep_env \
          --bake $EV/phase$k.parquet ) > $EV/phase$k.log 2>&1 && [ -s $EV/phase$k.parquet ] && cp $EV/phase$k.parquet $G/$hive/ref_gl_ilc.parquet
      log "glock $tg: evolve phase $k: $(python -c "import json; d=json.load(open('$EV/phase$k.json')); g=d['generations']; print('window', d['window'], 'unedited', g[0]['unedited'], 'best', d['best']['fit'], 'at gen', d['best']['gen'], 'of', len(g))" 2>&1 | tail -1)" >> $J
    done
  fi
  cp $G/$hive/ref_gl_ilc.parquet $RD/$hive/
  N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$P0').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero.npz $RD/$hive/ref_gl_ilc.parquet $N ) >> $LG 2>&1
  ( cd $REPO_DIR && python $T/trace_score.py $RD/$hive/ref_gl_ilc.parquet $O/ep$ep/zero.npz:zero_action ) > $O/ep$ep/zero_score.txt 2>&1
  python $T/rest_check.py $O/ep$ep/zero.npz $RD/$hive/ref_gl_ilc.parquet > $O/ep$ep/rest_check.json 2>&1
  log "glock $tg: rest check $(cut -c1-400 $O/ep$ep/rest_check.json)" >> $J
  if [ "$REPLAN" -gt 0 ]; then                                     # re-plan against the simulated world
    local it n sc tr=$O/ep$ep/zero.npz best RT
    best=$(grep -a 'zero_action:' $O/ep$ep/zero_score.txt | awk '{print $NF}')
    for it in $(seq 1 $REPLAN); do
      ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl_r$it.parquet $GL_ARGS --sim_trace $tr ) >> $LG 2>&1 \
        || { log "glock $tg: replan $it: grasp_lock FAILED" >> $J; break; }
      n=$(python -c "import json; print(sum(1 for x in json.load(open('$G/$hive/ref_gl_r${it}_grasp_lock.json'))['phases'] if x.get('replan')))")
      [ "${n:-0}" -gt 0 ] || { log "glock $tg: replan $it: every object is where its reference says before its grasp; nothing to re-plan" >> $J; break; }
      ( cd $FC && EMB=sharpa_hands_mid .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl_r$it.parquet $G/$hive/ref_gl_r${it}_ilc.parquet --iters ${ILC_ITERS:-4} --device cuda \
        ${ILC_HOLD:+--hold $G/$hive/ref_gl_r${it}_grasp_lock.json --gain ${ILC_GAIN:-0.6}} ) >> $LG 2>&1 \
        || { log "glock $tg: replan $it: wrist_ilc FAILED" >> $J; break; }
      RT=$RD.r$it; mkdir -p $RT/$hive; cp -r $R0/reconstructed_stage $RT/; cp $G/$hive/ref_gl_r${it}_ilc.parquet $RT/$hive/ref_gl_ilc.parquet
      ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero_r$it.npz $RT/$hive/ref_gl_ilc.parquet $N ) >> $LG 2>&1
      ( cd $REPO_DIR && python $T/trace_score.py $RT/$hive/ref_gl_ilc.parquet $O/ep$ep/zero_r$it.npz:zero_action ) > $O/ep$ep/zero_score_r$it.txt 2>&1
      python $T/rest_check.py $O/ep$ep/zero_r$it.npz $RT/$hive/ref_gl_ilc.parquet > $O/ep$ep/rest_check_r$it.json 2>&1
      sc=$(grep -a 'zero_action:' $O/ep$ep/zero_score_r$it.txt | awk '{print $NF}')
      log "glock $tg: replan $it: $n holds re-planned ($(grep -a 'REPLAN against' $LG | tail -$n | cut -d' ' -f1-2,6- | tr '\n' ' ' | cut -c1-300)); zero action $sc (previous $best)" >> $J
      if [ -n "$sc" ] && python -c "import sys; sys.exit(0 if $sc >= $best else 1)"; then
        cp $RT/$hive/ref_gl_ilc.parquet $RD/$hive/ref_gl_ilc.parquet; tr=$O/ep$ep/zero_r$it.npz; best=$sc
        log "glock $tg: replan $it KEPT (training on it)" >> $J
      else
        log "glock $tg: replan $it not better; kept the previous version" >> $J; break
      fi
    done
  fi
  log "glock $tg: $(grep -a 'grasp pose\|WRAP\|SNAP' $LG | cut -c1-160 | tr '\n' ' ') | zero action $(grep -a 'zero_action:\|floor' $O/ep$ep/zero_score.txt | tr '\n' ' ')" >> $J
  fi
  if [ "${REF_ONLY:-0}" = 1 ]; then                                 # reference only (mass_check.sh builds it once)
    log "glock $tg: REF_ONLY: reference finished ($RD/$hive/ref_gl_ilc.parquet); not trained" >> $J; return 0
  fi
  local tp esp rc slot tries=0
  while :; do
    slot=$(train_slot); esp=
    ( cd $FC && env ${TRAIN_ENV:-} MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac \
        embodiment=sharpa_hands_mid "task.parquet='$RD/$hive'" task.motion_speed=1.0 reset.seed=$SEED logging.mode=disabled \
        output_dir=$RUN training.total_environment_steps=$STEPS $TRAIN_ARGS ) >> $RUN/train.log 2>&1 &
    tp=$!
    if [ "$ES" = 1 ]; then J=$J REPO_DIR=$REPO_DIR bash $T/early_stop.sh $RUN $O/ep$ep/curve $ep $tp & esp=$!; fi
    wait $tp; rc=$?
    [ -n "$esp" ] && wait $esp
    rmdir /content/train_slot_$slot
    if [ $rc -ne 0 ] && [ $tries -lt 2 ] && grep -aq 'out of memory' $RUN/train.log; then   # another process took the memory
      tries=$((tries + 1)); mv $RUN $RUN.oom$tries; mkdir -p $RUN
      log "glock $tg: training ran out of GPU memory; retry $tries after 60 s" >> $J; sleep 60; continue
    fi
    break
  done
  if [ $rc -ne 0 ] && [ ! -f $RUN/EARLY_STOPPED ]; then
    log "glock $tg: training FAILED ($(tail -2 $RUN/train.log | tr '\n' ' ' | cut -c1-200))" >> $J; return 1
  fi
  log "glock $tg: trained $(ls $RUN/policy_*.safetensors | wc -l) checkpoints$([ -f $RUN/EARLY_STOPPED ] && echo "; early stop: $(cat $RUN/EARLY_STOPPED)")" >> $J
  REPO_DIR=$REPO_DIR PAR=$PAR REP=${CURVE_REP:-1} bash $T/ckpt_curve.sh $RUN $O/ep$ep/curve $ep >> $LG 2>&1
  python $T/ckpt_curve_summary.py $O/ep$ep/curve > $O/ep$ep/curve.txt 2>&1
  ck=$(python - $O/ep$ep/curve $RUN << 'EOF'
import glob, json, os, sys
def score(f):                                                       # the early-stop mean of several evaluations if present
    e = os.path.join(os.path.dirname(f), 'es.json')
    return json.load(open(e))['mean'] if os.path.exists(e) else json.load(open(f)).get('sim_vs_ref', -1)
best = max(((score(f), os.path.basename(os.path.dirname(f))) for f in glob.glob(f'{sys.argv[1]}/policy_*/qa_policy.json')), default=None)
print(f'{sys.argv[2]}/{best[1]}.safetensors' if best else '')
EOF
)
  [ -s "$ck" ] || { log "glock $tg: no scored checkpoint" >> $J; return 1; }
  log "glock $tg: curve $(tr -s ' ' < $O/ep$ep/curve.txt | cut -c1-40 | tr '\n' ';' | cut -c1-500); chosen by sim_vs_ref: $(basename $ck)" >> $J
  evalrep $ck $O/ep$ep/best $ep
  cp $ck $O/ep$ep/best/policy.safetensors                        # the chosen checkpoint survives the store's pruning
  log "glock $tg RESULT ($(basename $ck)): $(python -c "import json; d=json.load(open('$O/ep$ep/best/summary.json')); print('n', d['n'], 'sim_vs_ref', d.get('sim_vs_ref'), 'registered AUC vs mocap', d.get('auc'))" 2>&1 | tail -1)" >> $J
}

label "glock public: $PAIRS"
pids=()
for x in $PAIRS; do
  IFS=: read -r ep run base perc <<< "$x"
  one $ep $run $base $perc & pids+=($!)
  sleep 30
done
wait "${pids[@]}"
python - $O << 'EOF' > $O/summary.json
import glob, json, sys
out = {}
for f in sorted(glob.glob(f'{sys.argv[1]}/ep*/best/summary.json')):
    ep = f.split('/')[-3]; d = json.load(open(f)); d.pop('rollouts', None); out[ep] = d
print(json.dumps(out, indent=1))
EOF
log "glock_public summary: $(tr -d '\n ' < $O/summary.json | cut -c1-1500)" >> $J
[ "${NO_PUSH:-0}" = 1 ] || bash $OPS/store.sh push-run > /dev/null 2>&1 || true
