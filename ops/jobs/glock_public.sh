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
# Summary: /content/results/glock_public/summary.json; per-episode logs /content/glock_ep<N>.log.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; T=$REPO_DIR/tools; J=${J:-/content/job.log}; NREP=${NREP:-5}; PAR=${PAR:-3}; SEED=${SEED:-42}
SPLIT=${SPLIT:-public}; SETTLE=${SETTLE:-0}; SF=${SF:-1}; REPLAN=${REPLAN:-0}; ES=${ES:-0}; STEPS=${STEPS:-70004736}; PAIRS=${PAIRS:-"24:20261021-auto24-966eb96:mcs 27:20261021-auto18-966eb96:auto"}
GL_ARGS=${GL_ARGS:-"--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1"}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} ASSETS=/content/assets
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/glock_public; mkdir -p $O
log "glock_public code $(git -C $REPO_DIR rev-parse --short HEAD), pairs [$PAIRS], seed $SEED, steps $STEPS, NREP $NREP, SPLIT $SPLIT, SETTLE $SETTLE, SF $SF, REPLAN $REPLAN, EVOLVE ${EVOLVE:-0} (worlds ${EV_POP:-256}, robust ${EV_ROBUST:-4}, gens ${EV_GENS:-20}), DROP ${FC_DROP_START:-0}, ES $ES (target ${ES_TARGET:-0.9}), CURR_SCALE ${CURR_SCALE:-1}, GL_ARGS [$GL_ARGS]" >> $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit budget_mesh (score_registered --meshes); support_fill union
python $P/make_assets.py $MESH_DIR $ASSETS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
fc_patches $J || exit 1                                          # FDR rewards + VOC fix; sets TRAIN_ARGS (curriculum, weights)
if [ -n "${CURR_SCALE:-}" ]; then                                # curriculum thresholds scaled to the planned length
  TRAIN_ARGS="$TRAIN_ARGS curriculum.thresholds=$(python -c "s = $CURR_SCALE; t = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]; print('[' + ','.join(str(int(x * s)) for x in t) + ']')")"
  log "curriculum thresholds scaled by $CURR_SCALE: TRAIN_ARGS [$TRAIN_ARGS]" >> $J
fi
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml   # kp 400 wrist (the checkpoint stores the resolved config)
[ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }
for run in $(for x in $PAIRS; do echo $x | cut -d: -f2; done | sort -u | grep -v '^new$'); do
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
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1 \
      && python $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
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
            s = json.load(open(f'{r}score_registered_ep{ep}.json'))['sim']; row.update(auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR'])
        rows.append(row)
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'sim_vs_ref' in x]; agg = {}
for k in ('sim_vs_ref', 'auc'):
    v = np.array([x[k] for x in ok if k in x], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4))
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

one() {
  local ep=$1 run=$2 base=$3 R0 P0 hive G RD N RUN LG=/content/glock_ep$1.log ck reuse=0
  if [ "${REUSE_REF:-0}" = 1 ] && ls /content/refs/glockt/ep$ep/processed/*/*/ref_gl_ilc.parquet > /dev/null 2>&1 \
      && [ -f $O/ep$ep/rest_check.json ]; then                     # finish an episode whose training failed on this box:
    reuse=1                                                        # keep its finished reference (grasp lock, ILC, search)
  fi
  if [ "$run" = new ] && [ $reuse = 0 ]; then                      # end to end from the raw episode (perception on)
    ( export VARIANT=$base MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STEPS=0 \
        STOP_AFTER=reference SPLIT=$SPLIT PERC=perc2; bash $P/pipeline_ep.sh $ep ) > /content/ref_ep$ep.log 2>&1 \
      || { log "glock ep$ep: reference build FAILED ($(tail -3 /content/ref_ep$ep.log | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
    log "glock ep$ep: reference built from the raw episode ($(grep -a 'perception:\|qa_ref\|contact_retarget:' /content/ref_ep$ep.log | cut -c1-160 | tr '\n' ' ' | cut -c1-500))" >> $J
  fi
  if [ "$base" = auto ]; then                                      # the variant auto_ep.sh published for that episode
    base=$(python -c "import json, os; print(os.path.basename(os.path.dirname(json.load(open('/content/results/final/ep$ep/final.json'))['chosen'])).replace('perc2', '', 1))" 2>/dev/null)
    [ -n "$base" ] || { log "glock ep$ep: no results/final/ep$ep/final.json in the pulled run" >> $J; return 1; }
  fi
  R0=/content/refs/perc2$base/ep$ep; P0=$(ls $R0/processed/*/*/*.parquet 2>/dev/null | head -1)
  [ -s "$P0" ] || { log "glock ep$ep: no reference under $R0" >> $J; return 1; }
  fix_assets $P0 >> $LG 2>&1 || { log "glock ep$ep: assets missing" >> $J; return 1; }
  hive=$(dirname ${P0#$R0/}); G=/content/refs/glock/ep$ep; RD=/content/refs/glockt/ep$ep; RUN=/content/runs/glock/ep$ep-s$SEED
  local ts_=$(date +%s)                                           # a pulled run may hold old checkpoints / curve scores for this
  [ -d $RUN ] && [ -n "$(ls -A $RUN 2>/dev/null)" ] && mv $RUN $RUN.pulled_$ts_   # episode (ev3 2026-10-24: ckpt_curve skips scored
  [ $reuse = 0 ] && [ -d $O/ep$ep ] && [ -n "$(ls -A $O/ep$ep 2>/dev/null)" ] && mv $O/ep$ep $O/ep$ep.pulled_$ts_   # checkpoints): keep them aside
  mkdir -p $G/$hive $RD/$hive $RUN $O/ep$ep; cp -r $R0/reconstructed_stage $G/; cp -r $R0/reconstructed_stage $RD/
  log "glock ep$ep: base $base ($P0)$([ $reuse = 1 ] && echo "; REUSE_REF: training on this box's finished reference $RD/$hive/ref_gl_ilc.parquet")" >> $J
  if [ $reuse = 0 ]; then                                          # reference stages (skipped with REUSE_REF)
  if [ "$SF" = 1 ]; then                                           # support-consistent meshes; the reference then names them
    local SFT=/content/refs/sf/ep$ep; mkdir -p $SFT/$hive; cp -r $R0/reconstructed_stage $SFT/
    python $P/support_fill.py $P0 $(ls $R0/reconstructed_stage/*.usda | head -1) $SFT/assets $SFT/$hive/ref_sf.parquet > $LG.sf 2>&1 \
      || { log "glock ep$ep: support_fill FAILED ($(tail -1 $LG.sf | cut -c1-200))" >> $J; return 1; }
    cp $SFT/$hive/ref_sf_support_fill.json $O/ep$ep/support_fill.json; P0=$SFT/$hive/ref_sf.parquet
    log "glock ep$ep: support_fill $(python -c "
import json; d = json.load(open('$O/ep$ep/support_fill.json'))
print('; '.join(n + (' FILLED ' if o['filled'] else ' as is ') + str([(r.get('frame'), r.get('status', 'skipped'), r.get('fill_cm')) for r in o['fills']]) for n, o in d['objects'].items()))" 2>&1 | cut -c1-600)" >> $J
  fi
  if [ "$SETTLE" = 1 ]; then                                       # settle the start in the simulator
    local SST=/content/refs/settle/ep$ep; mkdir -p $SST/$hive; cp -r $R0/reconstructed_stage $SST/
    ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/sim_settle.py $P0 $SST/$hive/ref_settled.parquet ) > $LG.settle 2>&1 \
      || { log "glock ep$ep: sim_settle FAILED ($(tail -1 $LG.settle | cut -c1-200))" >> $J; return 1; }
    cp $SST/$hive/ref_settled_settle.json $O/ep$ep/settle.json; P0=$SST/$hive/ref_settled.parquet
    log "glock ep$ep: sim_settle $(tail -1 $LG.settle | cut -c1-500)" >> $J
  fi
  ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl.parquet $GL_ARGS ) >> $LG 2>&1 \
    || { log "glock ep$ep: grasp_lock FAILED" >> $J; return 1; }
  ( cd $FC && EMB=sharpa_hands_mid .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl.parquet $G/$hive/ref_gl_ilc.parquet --iters 4 --device cuda ) >> $LG 2>&1 \
    || { log "glock ep$ep: wrist_ilc FAILED" >> $J; return 1; }
  if [ "${EVOLVE:-0}" = 1 ]; then                                  # evolutionary grasp refinement, one hold at a time
    local EV=$O/ep$ep/evolve np_ k; mkdir -p $EV; cp $G/$hive/ref_gl_ilc.parquet $EV/ref_before_evolve.parquet
    np_=$(python -c "import json; print(len(json.load(open('$G/$hive/ref_gl_grasp_lock.json'))['phases']))")
    for k in $(seq 0 $((np_ - 1))); do
      ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/grasp_evolve.py $G/$hive/ref_gl_ilc.parquet $G/$hive/ref_gl_grasp_lock.json \
          $EV/phase$k.json --phase $k --all_objects --pop ${EV_POP:-256} --gens ${EV_GENS:-20} --sigma_pos 0.03 --sigma_fin 0.3 \
          --robust ${EV_ROBUST:-4} --jitter ${EV_JITTER:-0.005} --keep_env \
          --bake $EV/phase$k.parquet ) > $EV/phase$k.log 2>&1 && [ -s $EV/phase$k.parquet ] && cp $EV/phase$k.parquet $G/$hive/ref_gl_ilc.parquet
      log "glock ep$ep: evolve phase $k: $(python -c "import json; d=json.load(open('$EV/phase$k.json')); g=d['generations']; print('window', d['window'], 'unedited', g[0]['unedited'], 'best', d['best']['fit'], 'at gen', d['best']['gen'], 'of', len(g))" 2>&1 | tail -1)" >> $J
    done
  fi
  cp $G/$hive/ref_gl_ilc.parquet $RD/$hive/
  N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$P0').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero.npz $RD/$hive/ref_gl_ilc.parquet $N ) >> $LG 2>&1
  ( cd $REPO_DIR && python $T/trace_score.py $RD/$hive/ref_gl_ilc.parquet $O/ep$ep/zero.npz:zero_action ) > $O/ep$ep/zero_score.txt 2>&1
  python $T/rest_check.py $O/ep$ep/zero.npz $RD/$hive/ref_gl_ilc.parquet > $O/ep$ep/rest_check.json 2>&1
  log "glock ep$ep: rest check $(cut -c1-400 $O/ep$ep/rest_check.json)" >> $J
  if [ "$REPLAN" -gt 0 ]; then                                     # re-plan against the simulated world
    local it n sc tr=$O/ep$ep/zero.npz best RT
    best=$(grep -a 'zero_action:' $O/ep$ep/zero_score.txt | awk '{print $NF}')
    for it in $(seq 1 $REPLAN); do
      ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl_r$it.parquet $GL_ARGS --sim_trace $tr ) >> $LG 2>&1 \
        || { log "glock ep$ep: replan $it: grasp_lock FAILED" >> $J; break; }
      n=$(python -c "import json; print(sum(1 for x in json.load(open('$G/$hive/ref_gl_r${it}_grasp_lock.json'))['phases'] if x.get('replan')))")
      [ "${n:-0}" -gt 0 ] || { log "glock ep$ep: replan $it: every object is where its reference says before its grasp; nothing to re-plan" >> $J; break; }
      ( cd $FC && EMB=sharpa_hands_mid .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl_r$it.parquet $G/$hive/ref_gl_r${it}_ilc.parquet --iters 4 --device cuda ) >> $LG 2>&1 \
        || { log "glock ep$ep: replan $it: wrist_ilc FAILED" >> $J; break; }
      RT=$RD.r$it; mkdir -p $RT/$hive; cp -r $R0/reconstructed_stage $RT/; cp $G/$hive/ref_gl_r${it}_ilc.parquet $RT/$hive/ref_gl_ilc.parquet
      ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero_r$it.npz $RT/$hive/ref_gl_ilc.parquet $N ) >> $LG 2>&1
      ( cd $REPO_DIR && python $T/trace_score.py $RT/$hive/ref_gl_ilc.parquet $O/ep$ep/zero_r$it.npz:zero_action ) > $O/ep$ep/zero_score_r$it.txt 2>&1
      python $T/rest_check.py $O/ep$ep/zero_r$it.npz $RT/$hive/ref_gl_ilc.parquet > $O/ep$ep/rest_check_r$it.json 2>&1
      sc=$(grep -a 'zero_action:' $O/ep$ep/zero_score_r$it.txt | awk '{print $NF}')
      log "glock ep$ep: replan $it: $n holds re-planned ($(grep -a 'REPLAN against' $LG | tail -$n | cut -d' ' -f1-2,6- | tr '\n' ' ' | cut -c1-300)); zero action $sc (previous $best)" >> $J
      if [ -n "$sc" ] && python -c "import sys; sys.exit(0 if $sc >= $best else 1)"; then
        cp $RT/$hive/ref_gl_ilc.parquet $RD/$hive/ref_gl_ilc.parquet; tr=$O/ep$ep/zero_r$it.npz; best=$sc
        log "glock ep$ep: replan $it KEPT (training on it)" >> $J
      else
        log "glock ep$ep: replan $it not better; kept the previous version" >> $J; break
      fi
    done
  fi
  log "glock ep$ep: $(grep -a 'grasp pose\|WRAP\|SNAP' $LG | cut -c1-160 | tr '\n' ' ') | zero action $(grep -a 'zero_action:\|floor' $O/ep$ep/zero_score.txt | tr '\n' ' ')" >> $J
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
      log "glock ep$ep: training ran out of GPU memory; retry $tries after 60 s" >> $J; sleep 60; continue
    fi
    break
  done
  if [ $rc -ne 0 ] && [ ! -f $RUN/EARLY_STOPPED ]; then
    log "glock ep$ep: training FAILED ($(tail -2 $RUN/train.log | tr '\n' ' ' | cut -c1-200))" >> $J; return 1
  fi
  log "glock ep$ep: trained $(ls $RUN/policy_*.safetensors | wc -l) checkpoints$([ -f $RUN/EARLY_STOPPED ] && echo "; early stop: $(cat $RUN/EARLY_STOPPED)")" >> $J
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
  [ -s "$ck" ] || { log "glock ep$ep: no scored checkpoint" >> $J; return 1; }
  log "glock ep$ep: curve $(tr -s ' ' < $O/ep$ep/curve.txt | cut -c1-40 | tr '\n' ';' | cut -c1-500); chosen by sim_vs_ref: $(basename $ck)" >> $J
  evalrep $ck $O/ep$ep/best $ep
  cp $ck $O/ep$ep/best/policy.safetensors                        # the chosen checkpoint survives the store's pruning
  log "glock ep$ep RESULT ($(basename $ck)): $(python -c "import json; d=json.load(open('$O/ep$ep/best/summary.json')); print('n', d['n'], 'sim_vs_ref', d.get('sim_vs_ref'), 'registered AUC vs mocap', d.get('auc'))" 2>&1 | tail -1)" >> $J
}

label "glock public: $PAIRS"
pids=()
for x in $PAIRS; do
  IFS=: read -r ep run base <<< "$x"
  one $ep $run $base & pids+=($!)
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
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
