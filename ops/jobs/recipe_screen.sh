#!/bin/bash
# Recipe screen, 3 arms (2026-10-31; pre-registered in docs/research/physics-2026-10-30/physics-solver.md section 8,
# written before any GPU result). Public episodes, the SAME stored reference per episode for every arm, seed and box
# (REUSE of store run SRCREF: the round-1 S1 grasp-lock + ILC + EVOLVE references, refs/glockt/ep<N>), NVIDIA's public
# scans with the S1 masses (MA_ARGS props_public_scans.json), the frozen glock_public recipe (FDR rewards + VOC fix,
# kp 400 wrist), seeds SEEDS, cap STEPS (70,004,736, total_environment_steps identical across arms), early stopping on
# for every arm with the option-1 settings (target 0.9, patience 20M, from 20M, 2 evaluations), checkpoint chosen by
# sim_vs_ref (our reference, no ground truth) as in rounds 1-3, then NREP (10) official evaluations of it, each scored
# sim_vs_ref + registered AUC vs mocap (pipeline/score_registered.py: ground truth only here, after inference).
# Arms (definitions in tools/recipe_screen.py, the single source for this job and the CPU tests):
#   C  control: the recipe as is (curriculum thresholds unscaled; FlashSAC LR 3e-4 -> 1.5e-4 over the run's updates)
#   K  keep-the-peak: LR initial = peak 6e-4, end 3e-5, learning_rate_schedule_updates pinned to the cap's 136,728
#      updates; curriculum thresholds x 2 (assist 1.0 to 39.3M, 0.75 to 68.8M, 0.5 to 70M; VOC >= 0.25 until 127.8M)
#   D  start-state randomization: the TRAINING process gets FC_DR_RESET=DR_RESET FC_DR_SEED=<seed>
#      (ops/box/patch_flashchord_dr.py; inert in every other process; no config field)
# The evaluator rebuilds the env from the checkpoint config and runs VOC 0 (harness.apply_evaluation_composition):
# K's keys only reach the learner and the training curriculum (CPU check: tools/recipe_screen_tests/eval_invariance.py).
# Cells = ARMS x EPS x SEEDS (or CELLS="arm:ep:seed ..."), trained in that order (episode-major) in TRAIN_SLOTS (2)
# shared GPU slots; scoring overlaps the next trainings. Each box writes its own store run; merge on CPU afterwards:
#   python tools/recipe_screen.py verdict <run A>/results/recipe_screen/summary.json <run B>/... --out merged.json
# (summary.json is rewritten after every cell; a results/recipe_screen directory is accepted too, e.g. of a box that
# died: its pushed cell.json files are read directly)
# Box plans (physics-solver.md section 8): 2 boxes SEEDS=42 | SEEDS=43, or 3 boxes ARMS=C | ARMS=K | ARMS=D.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'SEEDS=42 bash ops/jobs/recipe_screen.sh'
# Robustness: every official evaluation runs under `timeout EVAL_TIMEOUT` and the curve under CURVE_TIMEOUT; the ES
# watcher gets ES_TAIL s after its training ends; a training that exits non-zero without an early stop is a failed
# cell (no truncated runs compared). The box's stall watchdog and self-destroy are ops/box/run_job.sh's.
# Knobs: ARMS EPS SEEDS CELLS SRCREF STEPS NREP CURVE_REP PAR ES_TARGET ES_PATIENCE ES_MIN ES_N DR_RESET EVAL_TIMEOUT
#   CURVE_TIMEOUT ES_TAIL TRAIN_SLOTS SLOT_POLL CELL_GAP ZERO PIP; CROOT (default /content; the CPU dry run's root).
CROOT=${CROOT:-/content}
. $CROOT/v2d-track3/ops/box/lib.sh
R=$REPO_DIR; T=$R/tools; P=$R/pipeline; J=${J:-$CROOT/job.log}
FC=${FC:-$CROOT/v2d/robotic_grounding/flash_chord}; O=$CROOT/results/recipe_screen; mkdir -p $O/refs
ARMS=${ARMS:-"C K D"}; EPS=${EPS:-"2 12 18 24"}; SEEDS=${SEEDS:-"42 43"}; CELLS=${CELLS:-}
SRCREF=${SRCREF:-20261030-physS1-6a814df}; STEPS=${STEPS:-70004736}; NREP=${NREP:-10}; CURVE_REP=${CURVE_REP:-3}; PAR=${PAR:-3}
ES_TARGET=${ES_TARGET:-0.9}; ES_PATIENCE=${ES_PATIENCE:-20000000}; ES_MIN=${ES_MIN:-20000000}; ES_N=${ES_N:-2}
DR_RESET=${DR_RESET:-1.5,0.015,0.01}; EVAL_TIMEOUT=${EVAL_TIMEOUT:-1200}; CURVE_TIMEOUT=${CURVE_TIMEOUT:-1500}; ES_TAIL=${ES_TAIL:-1200}
TRAIN_SLOTS=${TRAIN_SLOTS:-2}; SLOT_POLL=${SLOT_POLL:-30}; CELL_GAP=${CELL_GAP:-30}; ZERO=${ZERO:-1}
[ $((STEPS % 4096)) = 0 ] || { log "recipe_screen: STEPS $STEPS is not a multiple of 4096" >> $J; exit 1; }
for v in FC_DR_RESET FC_DR_SEED FC_STATE_RESET FC_DROP_START FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME FDR FC_FDR_OBJ \
         FC_FDR_TIPS FC_VOC_INERTIA CURR_SCALE TRAIN_ARGS TRAIN_ENV; do   # the control is the recipe
  [ -n "${!v:-}" ] && log "recipe_screen: ignoring $v=${!v} from the environment" >> $J; unset $v   # as is; training-only
done                                                             # variables go to the training command, never exported
export EMB=sharpa_hands_mid OMP_NUM_THREADS=1
PY=python; FCPY=$FC/.venv/bin/python
log "recipe_screen code $(git -C $R rev-parse --short HEAD 2> /dev/null), arms [$ARMS], eps [$EPS], seeds [$SEEDS], cells [${CELLS:-all}], refs $SRCREF, steps $STEPS, NREP $NREP, CURVE_REP $CURVE_REP, ES $ES_TARGET/$ES_PATIENCE/$ES_MIN/$ES_N, DR_RESET $DR_RESET, K [$($PY $T/recipe_screen.py args K $STEPS)]" >> $J
label "recipe_screen: setup"

# ---- assets (S1 masses on the scans, as rounds 1-3), embodiment, FlashCHORD patches (FDR + VOC fix, then the DR patch)
[ "${PIP:-1}" = 1 ] && { pip install -q fast_simplification manifold3d >> $J 2>&1 || true; }   # score_registered --meshes
mkdir -p $CROOT/scanlib
for d in $CROOT/t3/mesh/*/; do
  n=$(basename $d); f=$d/$n.glb; [ -f $f ] || f=$d/${n}_collision.glb
  [ -f $f ] && [ "$n" != wooden_spoon ] && ln -sf $f $CROOT/scanlib/$n.glb
done
export LIB=$CROOT/scanlib MA_ARGS="--physics $R/docs/research/physics-2026-10-30/props_public_scans.json"
$PY $P/make_assets.py $CROOT/scanlib $CROOT/assets $MA_ARGS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
grep -h mass $CROOT/assets/urdf/*.urdf > $O/asset_masses.txt 2>&1
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml
[ -s $E ] || cp $R/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }
fc_patches $J || exit 1                                          # exports FC_FDR_*, FC_VOC_INERTIA; sets TRAIN_ARGS
$PY $R/ops/box/patch_flashchord_dr.py $FC >> $J 2>&1 || { log "DR patch FAILED" >> $J; exit 1; }
log "recipe_screen: patches applied; TRAIN_ARGS [$TRAIN_ARGS] TRAIN_ENV [${TRAIN_ENV:-}]" >> $J

fix_assets() {  # as glock_public.sh: a reference names the asset root of the box that built it
  $PY - "$1" "$CROOT" << 'EOF'
import os, sys, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1]); root = sys.argv[2]
for r in sorted({os.path.dirname(os.path.dirname(p)) for p in t.column('object_urdf_paths')[0].as_py() if not os.path.exists(p)}):
    if r.startswith(root + '/') and not os.path.lexists(r):
        os.symlink(root + '/assets', r); print('linked', r, '->', root + '/assets')
    else:
        print('MISSING assets under', r); sys.exit(1)
EOF
}
killtree() {  # stop the process first (it cannot spawn more), then its children depth-first, then terminate it
  local c; kill -STOP $1 2> /dev/null; for c in $(pgrep -P $1 2> /dev/null); do killtree $c; done
  kill -TERM $1 2> /dev/null; kill -CONT $1 2> /dev/null
}
train_slot() {  # at most TRAIN_SLOTS FlashSAC trainings at once (40 GB each on the 96 GB card)
  local s
  while :; do
    for s in $(seq 1 $TRAIN_SLOTS); do mkdir $CROOT/train_slot_$s 2> /dev/null && { echo $s; return; }; done
    sleep $SLOT_POLL
  done
}
rmdir $CROOT/train_slot_* 2> /dev/null                           # stale slots of a job stopped on this box
write_summary() {  # the box summary (box-local verdicts), rewritten atomically after every cell and at the end
  local tmp=$O/.summary.$BASHPID.$RANDOM                         # (named here: a redirection expands in the child)
  $PY $T/recipe_screen.py summary $O --run ${RUN_ID:-?} --commit "$(git -C $R rev-parse --short HEAD 2> /dev/null)" --steps $STEPS --cells "$LIST" \
    --meta "arms=$ARMS" --meta "eps=$EPS" --meta "seeds=$SEEDS" --meta "srcref=$SRCREF" --meta "nrep=$NREP" --meta "curve_rep=$CURVE_REP" \
    --meta "es=$ES_TARGET/$ES_PATIENCE/$ES_MIN/$ES_N" --meta "dr_reset=$DR_RESET" --meta "train_args=$TRAIN_ARGS" > $tmp \
    && mv $tmp $O/summary.json || { rm -f $tmp; log "recipe_screen: summary FAILED" >> $J; }
}
evalrep() {  # $1 checkpoint, $2 output dir, $3 episode: NREP official evaluations, each scored (as physics_rl_loop.sh)
  local ck=$1 d=$2 ep=$3 E6 i pids=()
  E6=$(printf %06d $ep); mkdir -p $d
  for i in $(seq 1 $NREP); do
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false timeout $EVAL_TIMEOUT .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1 \
      && $PY $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
      && $PY $P/score_registered.py $ep $d/r$i --meshes $CROOT/scanlib > /dev/null 2>&1 ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  $PY - $d $ep $ck << 'EOF' > $d/summary.json
import glob, json, os, sys
import numpy as np
d, ep, ck = sys.argv[1], int(sys.argv[2]), sys.argv[3]; rows = []
for r in sorted(glob.glob(f'{d}/r*/'), key=lambda x: int(os.path.basename(x[:-1])[1:])):
    try:
        q = json.load(open(f'{r}qa_policy.json')); row = dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=q['sim_vs_ref'])
        if os.path.exists(f'{r}score_registered_ep{ep}.json'):
            s = json.load(open(f'{r}score_registered_ep{ep}.json'))['sim']; row.update(auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR'])
        rows.append(row)
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'sim_vs_ref' in x]; agg = {}
for k in ('sim_vs_ref', 'auc'):
    v = np.array([x[k] for x in ok if k in x], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4), n=int(len(v)))
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

# ---- the stored references: one parquet per task dir, md5 recorded (the merge checks every cell used the same one)
label "recipe_screen: references"
PULL_SUB="$(for e in $EPS; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $SRCREF >> $J 2>&1 || log "pull-run $SRCREF: error (checking)" >> $J
for e in $EPS; do
  P0=$(ls $CROOT/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
  [ -s "$P0" ] || { log "recipe_screen ep$e: no reference in $SRCREF (its cells are skipped)" >> $J; continue; }
  n=$(find $CROOT/refs/glockt/ep$e/processed -name '*.parquet' | wc -l)
  [ "$n" = 1 ] || { log "recipe_screen ep$e: $n parquets in its task tree (its cells are skipped)" >> $J; continue; }
  fix_assets $P0 >> $J 2>&1 || { log "recipe_screen ep$e: assets missing (its cells are skipped)" >> $J; continue; }
  hive=$(dirname ${P0#$CROOT/refs/glockt/ep$e/}); echo $hive > $O/refs/ep$e.hive; md5sum $P0 | cut -d' ' -f1 > $O/refs/ep$e.md5
  if [ "$ZERO" = 1 ]; then                                        # diagnostic only: this box's zero-action replay of it
    N=$($PY -c "import pyarrow.parquet as pq; print(len(pq.read_table('$P0').column('robot_left_wrist_position')[0].as_py()))")
    ( cd $FC && DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/refs/ep$e.zero.npz $P0 $N ) > $O/refs/ep$e.zero.log 2>&1
    ( cd $R && $PY $T/trace_score.py $P0 $O/refs/ep$e.zero.npz:zero_action ) > $O/refs/ep$e.zero_score.txt 2>&1
  fi
  log "recipe_screen ep$e: reference $SRCREF ${P0#$CROOT/} md5 $(cat $O/refs/ep$e.md5)$([ "$ZERO" = 1 ] && echo "; zero action $(grep -a 'zero_action:' $O/refs/ep$e.zero_score.txt | tr -s ' ' | cut -c1-80)")" >> $J
done

# ---- cells
LIST=$CELLS
[ -n "$LIST" ] || LIST=$(for e in $EPS; do for s in $SEEDS; do for a in $ARMS; do echo -n "$a:$e:$s "; done; done; done)
for c in $LIST; do IFS=: read -r a e s <<< "$c"; mkdir -p $O/$a/ep$e-s$s; echo queued > $O/$a/ep$e-s$s/status; done
run_cell() {  # $1 arm, $2 episode, $3 seed, $4 the GPU slot this cell holds (released when its training ends)
  local arm=$1 ep=$2 seed=$3 slot=$4 RUN OC hive targs tenv tp esp rc tries=0 ck t0 i
  RUN=$CROOT/runs/screen/$arm/ep$ep-s$seed; OC=$O/$arm/ep$ep-s$seed; hive=$(cat $O/refs/ep$ep.hive)
  [ -d $RUN ] && [ -n "$(ls -A $RUN 2> /dev/null)" ] && mv $RUN $RUN.prev_$(date +%s)   # never score old checkpoints
  for d in curve best; do [ -d $OC/$d ] && mv $OC/$d $OC/$d.prev_$(date +%s); done
  mkdir -p $RUN $OC; cp $O/refs/ep$ep.md5 $OC/ref_md5; : > $OC/notes
  targs="$TRAIN_ARGS $($PY $T/recipe_screen.py args $arm $STEPS)"; tenv="$($PY $T/recipe_screen.py env $arm $seed $DR_RESET)"
  t0=$(date +%s); echo training > $OC/status
  while :; do
    echo "cd $FC && env ${TRAIN_ENV:-} $tenv MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac embodiment=sharpa_hands_mid task.parquet='$CROOT/refs/glockt/ep$ep/$hive' task.motion_speed=1.0 reset.seed=$seed logging.mode=disabled output_dir=$RUN training.total_environment_steps=$STEPS $targs" > $OC/train_cmd.txt
    log "recipe_screen $arm/ep$ep-s$seed: training on slot $slot (try $tries; env [$tenv])" >> $J
    ( cd $FC && env ${TRAIN_ENV:-} $tenv MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py \
        experiment=sharpa_flash_sac embodiment=sharpa_hands_mid "task.parquet='$CROOT/refs/glockt/ep$ep/$hive'" task.motion_speed=1.0 \
        reset.seed=$seed logging.mode=disabled output_dir=$RUN training.total_environment_steps=$STEPS $targs ) >> $RUN/train.log 2>&1 &
    tp=$!
    J=$J REPO_DIR=$R ES_TARGET=$ES_TARGET ES_PATIENCE=$ES_PATIENCE ES_MIN=$ES_MIN ES_N=$ES_N bash $T/early_stop.sh $RUN $OC/curve $ep $tp &
    esp=$!
    wait $tp; rc=$?
    i=0
    while kill -0 $esp 2> /dev/null; do                          # the watcher scores what is left, within ES_TAIL s
      if [ $i -ge $ES_TAIL ]; then killtree $esp; echo "ES watcher killed $ES_TAIL s after the training ended" >> $OC/notes; break; fi
      sleep 5; i=$((i + 5))
    done
    wait $esp 2> /dev/null
    if [ $rc -ne 0 ] && [ $tries -lt 2 ] && grep -aq 'out of memory' $RUN/train.log; then   # another process took the memory
      tries=$((tries + 1)); mv $RUN $RUN.oom$tries; mkdir -p $RUN; echo "out of memory: retry $tries" >> $OC/notes
      [ -d $OC/curve ] && mv $OC/curve $OC/curve.oom$tries      # its scores belong to the moved checkpoints
      log "recipe_screen $arm/ep$ep-s$seed: out of GPU memory; retry $tries after 60 s" >> $J; sleep 60; continue
    fi
    break
  done
  rmdir $CROOT/train_slot_$slot
  echo "{\"train_start\": $t0, \"train_end\": $(date +%s), \"train_rc\": $rc}" > $OC/times.json
  if [ $rc -ne 0 ] && [ ! -f $RUN/EARLY_STOPPED ]; then
    echo train_failed > $OC/status; echo "training rc $rc: $(tail -2 $RUN/train.log | tr '\n' ' ' | cut -c1-300)" >> $OC/notes
    log "recipe_screen $arm/ep$ep-s$seed: training FAILED rc $rc ($(tail -2 $RUN/train.log | tr '\n' ' ' | cut -c1-200))" >> $J
    $PY $T/recipe_screen.py cell $arm $ep $seed $OC $RUN > $OC/cell.json; return 1
  fi
  echo trained > $OC/status
  log "recipe_screen $arm/ep$ep-s$seed: trained $(ls $RUN/policy_*.safetensors 2> /dev/null | wc -l) checkpoints$([ -f $RUN/EARLY_STOPPED ] && echo "; early stop: $(cat $RUN/EARLY_STOPPED)")" >> $J
  REPO_DIR=$R PAR=$PAR REP=$CURVE_REP timeout $CURVE_TIMEOUT bash $T/ckpt_curve.sh $RUN $OC/curve $ep >> $OC/curve.log 2>&1 \
    || echo "curve rc $? (timeout $CURVE_TIMEOUT s or error): unscored checkpoints are not candidates" >> $OC/notes
  $PY $T/ckpt_curve_summary.py $OC/curve > $OC/curve.txt 2>&1
  ck=$($PY - $OC/curve $RUN << 'EOF'
import glob, json, os, sys
def score(f):                                                       # the early-stop mean of several evaluations if present
    e = os.path.join(os.path.dirname(f), 'es.json')
    return json.load(open(e))['mean'] if os.path.exists(e) else json.load(open(f)).get('sim_vs_ref', -1)
best = max(((score(f), os.path.basename(os.path.dirname(f))) for f in glob.glob(f'{sys.argv[1]}/policy_*/qa_policy.json')), default=None)
print(f'{sys.argv[2]}/{best[1]}.safetensors' if best else '')
EOF
)
  if [ ! -s "$ck" ]; then
    echo no_checkpoint > $OC/status; log "recipe_screen $arm/ep$ep-s$seed: no scored checkpoint" >> $J
    $PY $T/recipe_screen.py cell $arm $ep $seed $OC $RUN > $OC/cell.json; return 1
  fi
  evalrep $ck $OC/best $ep; cp $ck $OC/best/policy.safetensors   # the chosen checkpoint survives the store's pruning
  $FCPY $T/recipe_screen.py ckcfg $ck $OC/config_check.json $RUN >> $OC/notes 2>&1 || echo "config check FAILED" >> $OC/notes
  if $PY -c "import json, sys; sys.exit(0 if json.load(open('$OC/best/summary.json')).get('auc') else 1)" 2> /dev/null; then
    echo scored > $OC/status
  else
    echo eval_failed > $OC/status
  fi
  $PY $T/recipe_screen.py cell $arm $ep $seed $OC $RUN > $OC/cell.json
  log "recipe_screen $arm/ep$ep-s$seed RESULT ($(basename $ck)): $($PY -c "import json; d=json.load(open('$OC/cell.json')); print(d['status'], 'AUC', d['auc'], 'svr', d['sim_vs_ref'], 'ES', d['early_stop'])" 2>&1 | tail -1)" >> $J
  label "recipe_screen: $(ls $O/*/*/cell.json 2> /dev/null | wc -l) of $(echo $LIST | wc -w) cells done"; write_summary
}
label "recipe_screen: running $(echo $LIST | wc -w) cells"
pids=()
for c in $LIST; do
  IFS=: read -r a e s <<< "$c"
  [ -s $O/refs/ep$e.hive ] || { echo not_run > $O/$a/ep$e-s$s/status; echo "no reference" > $O/$a/ep$e-s$s/notes; continue; }
  slot=$(train_slot)                                             # trainings start in list order as slots free up
  run_cell $a $e $s $slot & pids+=($!)
  sleep $CELL_GAP
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
for c in $LIST; do                                               # cells that never wrote a record
  IFS=: read -r a e s <<< "$c"; [ -s $O/$a/ep$e-s$s/cell.json ] || $PY $T/recipe_screen.py cell $a $e $s $O/$a/ep$e-s$s $CROOT/runs/screen/$a/ep$e-s$s > $O/$a/ep$e-s$s/cell.json
done

# ---- box summary (box-local verdicts: other boxes' cells count as missing here) and the box's view of the merge
write_summary
$PY $T/recipe_screen.py verdict $O/summary.json > $O/summary.txt 2>&1
log "recipe_screen summary (box-local): $(grep -a '_vs_C:' $O/summary.txt | tr '\n' ' ' | cut -c1-600)" >> $J
label "recipe_screen: done"
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
