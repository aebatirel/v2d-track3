#!/bin/bash
# Multi-embodiment showcase, phase 1 (2026-11-06; owner: "lets do phase 0 and 1"; plan
# docs/research/work/embodiment-showcase-20261106/PLAN.md). One public episode (EP, default 27), several robots
# (ROBOTS="allegro leap ..."; "sharpa" = NVIDIA's Sharpa hands with our kp-400 wrist, embodiment sharpa_hands_mid).
# For each robot, one after another on the GPU (two trainings at once were ~30 % slower in total, 21 Oct):
#   1. train the standard FlashSAC learner on that robot's retargeted reference (showcase/retarget.py; inputs pulled
#      from the HF store at $INPUTS): experiment sharpa_flash_sac, embodiment <robot>, FDR rewards + VOC fix (lib.sh
#      fc_patches), STEPS (250M), seed SEED, contact buffers njmax 1024 / nconmax 512 (the eval-10 lesson: hands with
#      many shapes overflow the stock 512 / 256);
#   2. evaluate CANDS checkpoints (fractions of training, default final, 0.8, 0.6) once each with the official
#      evaluator and keep the best by sim_vs_ref (our reference only; pipeline/qa.py);
#   3. NREP official evaluations of the kept checkpoint, each scored against mocap (pipeline/score_sim.py; public
#      episode, evaluation only) -> results/showcase/ep<EP>_<robot>/summary.json;
#   4. one evaluator-style replay with a body trace (tools/trace_rollout.py, viewer off), for the videos (rendered on
#      CPU from the trace by showcase/tools/assemble.py).
# Steps 2-4 of a robot run in the background while the next robot trains. Results are pushed after every robot.
#   ops/vast.sh ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'ROBOTS="allegro leap shadow" bash ops/jobs/showcase.sh'
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; EP=${EP:-27}; STEPS=${STEPS:-250003456}; SEED=${SEED:-42}; NREP=${NREP:-5}
CANDS=${CANDS:-"1.0 0.8 0.6"}; INPUTS=${INPUTS:-showcase/inputs/20261106}
DEXURDF=${DEXURDF:-f5e7132f22108164577fea4c25ef99b5cc0e1900}
FC=/content/v2d/robotic_grounding/flash_chord; SC=$REPO_DIR/showcase; P=$REPO_DIR/pipeline; T=$REPO_DIR/tools
OUT=/content/results/showcase; E6=$(printf %06d $EP); mkdir -p $OUT
log "showcase code $(git -C $REPO_DIR rev-parse --short HEAD), ep $EP, robots [${ROBOTS:?}], steps $STEPS, seed $SEED, NREP $NREP" >> $J
label "showcase: robot assets"

# 1. robot models (dex-urdf at a pinned commit + FlashCHORD's own G1/Dex3), the generic embodiment, patches
mkdir -p /content/ext
if [ ! -d /content/ext/dex-urdf/robots/hands/allegro_hand ]; then
  ( cd /content/ext && git clone -q --filter=blob:none --no-checkout https://github.com/dexsuite/dex-urdf.git && cd dex-urdf \
    && git sparse-checkout set robots/hands/shadow_hand robots/hands/allegro_hand robots/hands/leap_hand robots/hands/inspire_hand \
         robots/hands/barrett_hand robots/hands/panda_gripper robots/hands/dclaw_gripper robots/hands/ability_hand \
    && git checkout -q $DEXURDF ) >> $J 2>&1 || { log "showcase: dex-urdf clone FAILED" >> $J; exit 1; }
fi
$FC/.venv/bin/python $SC/prep_robots.py /content/ext/dex-urdf/robots/hands $FC/src/flash_chord/assets /content/showcase/robots >> $J 2>&1 \
  || { log "showcase: prep_robots FAILED" >> $J; exit 1; }
bash $SC/install_fc.sh $FC /content/showcase/robots >> $J 2>&1 || { log "showcase: install FAILED" >> $J; exit 1; }
cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $FC/src/flash_chord/configs/embodiment/
fc_patches $J || exit 1
pip install -q fast_simplification manifold3d >> $J 2>&1 || true

# 2. references (retargeted on CPU by the agent, showcase/retarget.py) from the HF store
hf download "$HF_STORE" --repo-type dataset --include "$INPUTS/*" --local-dir /content/sc_in >> $J 2>&1 \
  || { log "showcase: inputs download FAILED" >> $J; exit 1; }
mkdir -p /content/refs/sc
for r in $(for x in $ROBOTS; do echo ${x%%:*}; done | sort -u); do
  src=/content/sc_in/$INPUTS/ep${EP}_$r; [ -d $src ] || { log "showcase: no inputs for $r ($src)" >> $J; exit 1; }
  rm -rf /content/refs/sc/ep${EP}_$r; cp -r $src /content/refs/sc/ep${EP}_$r
done
log "showcase: inputs ready: $(ls /content/refs/sc | tr '\n' ' ')" >> $J

evaluate() {  # $1 checkpoint, $2 out dir: one official evaluation + sim_vs_ref (qa.py) + vs mocap (score_sim.py)
  local ck=$1 d=$2; mkdir -p $d
  ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false timeout -k 60 1800 .venv/bin/python scripts/evaluate_policy.py \
      evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
      evaluation.metrics_output=$d/episode_$E6.json evaluation.object_trajectories_output=$d/episode_$E6.parquet \
      hydra.run.dir=$d/hydra logging.mode=disabled ) > $d/eval.log 2>&1 || return 1
  python $P/qa.py policy $d $EP > /dev/null 2>&1
  python $P/score_sim.py $EP $d > $d/score.log 2>&1
  return 0
}

post() {  # $1 robot, $2 run dir, $3 reference parquet: checkpoint choice, NREP draws, traced replay, summary
  local r=$1 RUN=$2 PQ=$3 O=$OUT/ep${EP}_$1 fr ck best bestck v N i OV
  mkdir -p $O/cand; best=-1; bestck=
  for fr in $CANDS; do
    ck=$(ls $RUN/policy_*.safetensors | python -c "import sys; L=[l.strip() for l in sys.stdin]; want=$fr*max(int(f.rsplit('_',1)[1].split('.')[0]) for f in L); print(min(L, key=lambda f: abs(int(f.rsplit('_',1)[1].split('.')[0]) - want)))")
    [ -s $O/cand/$(basename $ck .safetensors)/qa_policy.json ] && continue
    evaluate $ck $O/cand/$(basename $ck .safetensors) || { log "showcase $r: candidate $(basename $ck) eval FAILED" >> $J; continue; }
    v=$(python -c "import json; print(json.load(open('$O/cand/$(basename $ck .safetensors)/qa_policy.json'))['sim_vs_ref'])" 2>/dev/null || echo -1)
    log "showcase $r: candidate $(basename $ck) sim_vs_ref $v" >> $J
    if python -c "import sys; sys.exit(0 if float('$v') > float('$best') else 1)"; then best=$v; bestck=$ck; fi
  done
  [ -n "$bestck" ] || { log "showcase $r: NO candidate evaluated" >> $J; return 1; }
  echo "{\"chosen\": \"$bestck\", \"sim_vs_ref\": $best}" > $O/selection.json
  for i in $(seq 1 $NREP); do evaluate $bestck $O/r$i || log "showcase $r: draw $i FAILED" >> $J; done
  N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.ParquetFile('$PQ').read().column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  OV="evaluation.checkpoint=$bestck task.parquet='$PQ' reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
  for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
  # viewer off (2026-11-06: pyglet found no GL config on the phase-1 boxes); the videos are rendered from the trace on
  # CPU (showcase/tools/render_style.py, showcase/tools/assemble.py)
  OV="$OV viewer.backend=none viewer.num_frames=$N markers.keypoints=false markers.contacts=false"
  ( cd $FC && DEV=cuda timeout 1500 .venv/bin/python $T/trace_rollout.py policy $O/policy_trace.npz $OV ) > $O/trace.log 2>&1 \
    || log "showcase $r: trace FAILED ($(tail -2 $O/trace.log | tr '\n' ' ' | cut -c1-200))" >> $J
  python - $O $NREP $r > $O/summary.json << 'EOF'
import glob, json, os, sys
import numpy as np
O, n, robot = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = []
for i in range(1, n + 1):
    s = glob.glob(f'{O}/r{i}/score_ep*.json'); q = f'{O}/r{i}/qa_policy.json'
    if s:
        d = json.load(open(s[0])); rows.append(dict(draw=i, auc_mocap=d['sim_vs_mocap']['AUC'], mp_sr=d['sim_vs_mocap']['MP_SR'],
            sp_sr=d['sim_vs_mocap']['SP_SR'], mppe_cm=d['sim_vs_mocap']['MPPE_cm'], per_obj=d['sim_vs_mocap']['per_obj'],
            ref_vs_mocap=d.get('reference_vs_mocap', {}).get('AUC'), floor=d['static_floor']['AUC'],
            sim_vs_ref=json.load(open(q))['sim_vs_ref'] if os.path.exists(q) else None))
a = np.array([r['auc_mocap'] for r in rows]) if rows else np.zeros(0)
sel = json.load(open(f'{O}/selection.json'))
print(json.dumps(dict(robot=robot, checkpoint=sel['chosen'], cand_sim_vs_ref=sel['sim_vs_ref'], draws=rows, n=len(rows),
                      auc_mocap_mean=float(a.mean()) if len(a) else None, auc_mocap_sd=float(a.std()) if len(a) else None,
                      mp_sr_pass=int(sum(r['mp_sr'] >= 1.0 for r in rows))), indent=1))
EOF
  log "showcase $r: DONE $(python -c "import json; d=json.load(open('$O/summary.json')); print('AUC vs mocap', d['auc_mocap_mean'], '+-', d['auc_mocap_sd'], 'MP pass', d['mp_sr_pass'], '/', d['n'])")" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
}

pids=()
for x in $ROBOTS; do                     # ROBOT[:EMBODIMENT[:SEED]] (2026-11-06: variants, e.g. panda:panda_pads:43)
  IFS=: read -r r emb sd <<< "$x"
  [ -n "$emb" ] || emb=$r; [ "$emb" = sharpa ] && emb=sharpa_hands_mid
  sd=${sd:-$SEED}; tag=$r; [ "$emb" != "$r" ] && [ "$emb" != sharpa_hands_mid ] && tag=$emb; [ "$sd" != "$SEED" ] && tag=${tag}_s$sd
  PQ=$(ls /content/refs/sc/ep${EP}_$r/processed/*/*/*.parquet | head -1)
  RUN=/content/runs/showcase/ep${EP}_$tag; mkdir -p $RUN
  label "showcase: training $tag"
  log "showcase $tag: training (embodiment $emb, seed $sd, reference $PQ)" >> $J
  t0=$(date +%s)
  ( cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac \
      embodiment=$emb "task.parquet='$PQ'" task.motion_speed=1.0 reset.seed=$sd logging.mode=disabled output_dir=$RUN \
      training.total_environment_steps=$STEPS sim.njmax=1024 sim.nconmax=512 $TRAIN_ARGS ) >> $RUN/train.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || ! ls $RUN/policy_*.safetensors > /dev/null 2>&1; then
    log "showcase $tag: training FAILED rc=$rc after $(( ($(date +%s) - t0) / 60 )) min ($(grep -a -iE 'error|exception' $RUN/train.log | tail -2 | tr '\n' ' ' | cut -c1-240))" >> $J
    bash $OPS/store.sh push-run > /dev/null 2>&1 || true; continue
  fi
  touch $RUN/.done
  log "showcase $tag: trained in $(( ($(date +%s) - t0) / 60 )) min, $(ls $RUN/policy_*.safetensors | wc -l) checkpoints; $(grep -a 'env steps/s' $RUN/train.log | tail -1 | grep -oE '[0-9,]+ env steps/s')" >> $J
  post $tag $RUN $PQ >> $OUT/post_$tag.log 2>&1 & pids+=($!)
done
label "showcase: final evaluations"
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
python - $OUT > $OUT/all_summary.json << 'EOF'
import glob, json, os, sys
print(json.dumps({os.path.basename(os.path.dirname(f)): json.load(open(f)) for f in sorted(glob.glob(f'{sys.argv[1]}/*/summary.json'))}, indent=1))
EOF
log "showcase done: $(ls $OUT/*/summary.json 2>/dev/null | wc -l) robot summaries" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
