#!/bin/bash
# Public validation of the grasp-lock recipe (2026-10-23; owner go-ahead, 2 Max-Q boxes ≈ $4–5). The recipe that took
# the eval spoon episodes to sim_vs_ref ≈ 0.97 (docs/research/notes/24), FROZEN as below, on public episodes that have
# references built with our own meshes, scored against mocap afterwards (registered AUC with our meshes, evaluation only):
#   1. reference = the stored own-mesh reference of a finished run (store pull-run; EP:RUN:BASE as in hard_ab.sh);
#   2. pipeline/grasp_lock.py with GL_ARGS (single-hand carry per object, anatomy closing, palm press, wrap only where
#      the human holds a narrow part, copied grasps snapped to the surface), lift feed-forward for the kp 400 wrist;
#   3. pipeline/wrist_ilc.py with the kp 400 embodiment (EMB=sharpa_hands_mid);
#   4. zero-action replay (tools/trace_rollout.py) scored with tools/trace_score.py (sim_vs_ref, our reference);
#   5. RL fine-tune: embodiment=sharpa_hands_mid, FDR rewards + VOC fix (lib.sh fc_patches), STEPS (70M), SEED;
#   6. official evaluation of every checkpoint (tools/ckpt_curve.sh, sim_vs_ref), checkpoint chosen by sim_vs_ref only
#      (no ground truth), then NREP official evaluations of it, each scored sim_vs_ref + registered AUC vs mocap.
# Episodes listed together run concurrently (two trainings share the GPU).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> \
#     'PAIRS="24:20261021-auto24-966eb96:mcs 27:20261021-auto18-966eb96:auto" bash ops/jobs/glock_public.sh'
# Summary: /content/results/glock_public/summary.json; per-episode logs /content/glock_ep<N>.log.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; T=$REPO_DIR/tools; J=${J:-/content/job.log}; NREP=${NREP:-5}; PAR=${PAR:-3}; SEED=${SEED:-42}
STEPS=${STEPS:-70004736}; PAIRS=${PAIRS:-"24:20261021-auto24-966eb96:mcs 27:20261021-auto18-966eb96:auto"}
GL_ARGS=${GL_ARGS:-"--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1"}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} ASSETS=/content/assets
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/glock_public; mkdir -p $O
log "glock_public code $(git -C $REPO_DIR rev-parse --short HEAD), pairs [$PAIRS], seed $SEED, steps $STEPS, NREP $NREP, GL_ARGS [$GL_ARGS]" >> $J
pip install -q fast_simplification >> $J 2>&1 || true              # kit budget_mesh (score_registered --meshes)
python $P/make_assets.py $MESH_DIR $ASSETS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
fc_patches $J || exit 1                                          # FDR rewards + VOC fix; sets TRAIN_ARGS (curriculum, weights)
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml   # kp 400 wrist (the checkpoint stores the resolved config)
[ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }
for run in $(for x in $PAIRS; do echo $x | cut -d: -f2; done | sort -u); do
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

evalrep() {  # $1 checkpoint, $2 output dir, $3 episode: NREP official evaluations, each scored (as in hard_ab.sh)
  local ck=$1 d=$2 ep=$3 E6 i pids=()
  E6=$(printf %06d $ep); mkdir -p $d
  for i in $(seq 1 $NREP); do
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1 \
      && python $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
      && python $P/score_registered.py $ep $d/r$i --meshes $MESH_DIR > /dev/null 2>&1 ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  python - $d $ep $ck << 'EOF' > $d/summary.json
import glob, json, os, sys
import numpy as np
d, ep, ck = sys.argv[1], int(sys.argv[2]), sys.argv[3]; rows = []
for r in sorted(glob.glob(f'{d}/r*/')):
    try:
        q = json.load(open(f'{r}qa_policy.json')); s = json.load(open(f'{r}score_registered_ep{ep}.json'))['sim']
        rows.append(dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=q['sim_vs_ref'], auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR']))
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'auc' in x]; agg = {}
for k in ('sim_vs_ref', 'auc'):
    v = np.array([x[k] for x in ok], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4))
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

one() {
  local ep=$1 run=$2 base=$3 R0 P0 hive G RD N RUN LG=/content/glock_ep$1.log ck
  if [ "$base" = auto ]; then                                      # the variant auto_ep.sh published for that episode
    base=$(python -c "import json, os; print(os.path.basename(os.path.dirname(json.load(open('/content/results/final/ep$ep/final.json'))['chosen'])).replace('perc2', '', 1))" 2>/dev/null)
    [ -n "$base" ] || { log "glock ep$ep: no results/final/ep$ep/final.json in the pulled run" >> $J; return 1; }
  fi
  R0=/content/refs/perc2$base/ep$ep; P0=$(ls $R0/processed/*/*/*.parquet 2>/dev/null | head -1)
  [ -s "$P0" ] || { log "glock ep$ep: no reference under $R0" >> $J; return 1; }
  fix_assets $P0 >> $LG 2>&1 || { log "glock ep$ep: assets missing" >> $J; return 1; }
  hive=$(dirname ${P0#$R0/}); G=/content/refs/glock/ep$ep; RD=/content/refs/glockt/ep$ep; RUN=/content/runs/glock/ep$ep-s$SEED
  mkdir -p $G/$hive $RD/$hive $RUN $O/ep$ep; cp -r $R0/reconstructed_stage $G/; cp -r $R0/reconstructed_stage $RD/
  log "glock ep$ep: base $base ($P0)" >> $J
  ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl.parquet $GL_ARGS ) >> $LG 2>&1 \
    || { log "glock ep$ep: grasp_lock FAILED" >> $J; return 1; }
  ( cd $FC && EMB=sharpa_hands_mid .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl.parquet $G/$hive/ref_gl_ilc.parquet --iters 4 --device cuda ) >> $LG 2>&1 \
    || { log "glock ep$ep: wrist_ilc FAILED" >> $J; return 1; }
  cp $G/$hive/ref_gl_ilc.parquet $RD/$hive/
  N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$P0').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  ( cd $FC && EMB=sharpa_hands_mid DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero.npz $RD/$hive/ref_gl_ilc.parquet $N ) >> $LG 2>&1
  ( cd $REPO_DIR && python $T/trace_score.py $RD/$hive/ref_gl_ilc.parquet $O/ep$ep/zero.npz:zero_action ) > $O/ep$ep/zero_score.txt 2>&1
  log "glock ep$ep: $(grep -a 'grasp pose\|WRAP\|SNAP' $LG | cut -c1-160 | tr '\n' ' ') | zero action $(grep -a 'zero_action:\|floor' $O/ep$ep/zero_score.txt | tr '\n' ' ')" >> $J
  ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac \
      embodiment=sharpa_hands_mid "task.parquet='$RD/$hive'" task.motion_speed=1.0 reset.seed=$SEED logging.mode=disabled \
      output_dir=$RUN training.total_environment_steps=$STEPS $TRAIN_ARGS ) >> $RUN/train.log 2>&1 \
    || { log "glock ep$ep: training FAILED ($(tail -2 $RUN/train.log | tr '\n' ' ' | cut -c1-200))" >> $J; return 1; }
  log "glock ep$ep: trained $(ls $RUN/policy_*.safetensors | wc -l) checkpoints" >> $J
  REPO_DIR=$REPO_DIR PAR=$PAR bash $T/ckpt_curve.sh $RUN $O/ep$ep/curve $ep >> $LG 2>&1
  python $T/ckpt_curve_summary.py $O/ep$ep/curve > $O/ep$ep/curve.txt 2>&1
  ck=$(python - $O/ep$ep/curve $RUN << 'EOF'
import glob, json, os, sys
best = max(((json.load(open(f)).get('sim_vs_ref', -1), os.path.basename(os.path.dirname(f))) for f in glob.glob(f'{sys.argv[1]}/policy_*/qa_policy.json')), default=None)
print(f'{sys.argv[2]}/{best[1]}.safetensors' if best else '')
EOF
)
  [ -s "$ck" ] || { log "glock ep$ep: no scored checkpoint" >> $J; return 1; }
  log "glock ep$ep: curve $(tr -s ' ' < $O/ep$ep/curve.txt | cut -c1-40 | tr '\n' ';' | cut -c1-500); chosen by sim_vs_ref: $(basename $ck)" >> $J
  evalrep $ck $O/ep$ep/best $ep
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
