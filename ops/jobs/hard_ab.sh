#!/bin/bash
# Hard-episode A/B of contact-anchored retargeting (2026-10-21; pipeline/contact_retarget.py, owner: "snap the
# fingertips, let the wrist follow"). For each EP:RUN:BASE (default ep24 mcs and ep18 mc, today's registered 0.232 /
# 0.396 with our meshes): pull that run's perception, references and checkpoints from the store; build BASE+"k" = the
# same reference after contact retargeting (pipeline_ep.sh stage 3c, CPU) and train it with the same recipe (250M steps,
# seed 42, checkpoint sweep 0.4/0.6/0.8). Only the robot hand in the reference changes; the object trajectory, meshes,
# embodiment and training recipe are the same. Then the base's chosen checkpoint and the new chosen checkpoint are
# evaluated NREP times each (the evaluator is not deterministic: ep18 mc ranged 0.13-0.41 vs mocap over 8 rollouts)
# and every rollout is scored: sim_vs_ref (no ground truth) and, afterwards, registered vs mocap with our meshes.
# Episodes listed together train concurrently on one GPU.
#   ops/vast.sh create <offer> <run_id> 'bash ops/jobs/hard_ab.sh'      (no RESUME_FROM: the job pulls the runs)
# BASE "auto" = the variant auto_ep.sh published for that episode (results/final/ep<N>/final.json, its policy.safetensors).
# Overnight rounds (2026-10-22) set: SEED (default 42), SUF (variant suffix, default k), CR (1 = contact retargeting),
# BASE_EVAL (0 = skip re-evaluating the base), TRAIN_ARGS (passed to training, e.g. reward weights / embodiment),
# FC_OBJECT_KEYPOINT_SCALE (object-keypoint reward distance in m), FC_IMMEDIATE_FIRST_FRAME (share of late-stage resets
# that start like the official evaluation); both patch FlashCHORD, see ops/box/patch_flashchord.py.
# ASSET_SRC=public: the organisers' public URDFs/meshes in the simulator instead of ours (oracle-mesh test).
# FC_FDR_OBJ / FC_FDR_TIPS (2026-10-22): FlashDexRetarget-style training rewards, see ops/box/patch_flashchord_fdr.py.
# FC_VOC_INERTIA=1 (2026-10-23): virtual object controller with the full inertia tensor (ops/box/patch_flashchord_voc.py;
#   default on in auto_runs via lib.sh fc_patches, opt-in here so A/Bs against older baselines stay comparable).
# ENV_EP<N> (2026-10-22): space-separated VAR=value settings for episode N only (no spaces inside a value), e.g.
#   ENV_EP18="SUF=kfid CR_ARGS=--rest_settle=1 FC_IMMEDIATE_FIRST_FRAME=0.25", so episodes with different baselines
#   share one box.
# SPLIT=eval (2026-10-24, eval run): RUN "local" = a reference already built on this box (e.g. by glock_public.sh
#   SPLIT=eval EP:new:mck), nothing pulled; PDIR_ROOT=/content/perc2 then names its perception; no mocap scoring
#   (summaries hold sim_vs_ref only); BASE_EVAL=0.
# A 4th field EP:RUN:BASE:PERC (2026-10-30) names the perception prefix of the base reference refs/<PERC><BASE>/ep<N>
#   (default perc2). PERC other than perc2 (the oracle twins, ops/jobs/oracle_twins.sh: PERC=oracle, object motion from
#   mocap) is for SPLIT=public and RUN local only: its perception is /content/<PERC>/ep<N>, its refs, runs and results
#   are refs/<PERC><BASE><SUF>, runs/<PERC>..., results/<PERC>... and results/hard_ab/ep<N>/<PERC>_<BASE><SUF>-s<SEED>,
#   its log /content/hard_ab_<PERC>_ep<N><SUF>-s<SEED>.log; BASE_EVAL is off for it. Both arms of one episode may be
#   listed together (they take turns on the GPU like any two entries).
# EVAL_TIMEOUT=<s> (2026-10-31, ops/jobs/mass_eval.sh; as glock_public.sh): cut an official evaluation that runs longer,
#   here and in pipeline_ep.sh's evaluations (main + checkpoint sweep): timeout -k 60, each evaluation folder gets
#   eval_rc.txt (124 cut, 137 killed after the 60 s grace). NO_PUSH=1: no store push at the end (the calling job pushes
#   once). Both off by default.
# FC_DR_PATCH=1 (2026-10-31, pack 9b D arm, ops/jobs/mass_eval.sh ARM=dr; docs/research/work/pack9b-20261031/PREREG.md;
#   opt-in, off by default): ops/box/patch_flashchord_dr.py is applied after this script's other FlashCHORD patches
#   (start-state randomisation of sampled training resets; inert unless FC_DR_RESET is set in a process). The caller
#   sets FC_DR_RESET / FC_DR_SEED / FC_DR_SKIP_IMMEDIATE per episode in ENV_EP<N>.
# Summary: /content/results/hard_ab/summary.json; per-episode pipeline logs /content/hard_ab_ep<N><SUF>-s<SEED>.log.
# Each rollout's summary row also holds ref_auc / floor_auc (public): its reference and the static floor vs mocap.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; NREP=${NREP:-6}; PAR=${PAR:-3}
SEED=${SEED:-42}; SUF=${SUF:-k}; CR=${CR:-1}; BASE_EVAL=${BASE_EVAL:-1}; PDIR_ROOT=${PDIR_ROOT:-/content/perc2m}
PAIRS=${PAIRS:-"24:20261021-auto24-966eb96:mcs 18:20261021-auto18-966eb96:mc"}
export MESH_DIR=${LIB:-$REPO_DIR/meshes/library_v2} ASSETS=/content/assets SPLIT=${SPLIT:-public} PERC=perc2 STEPS=${STEPS:-250003456}
[ $SPLIT = eval ] && BASE_EVAL=0
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/hard_ab; mkdir -p $O
log "hard_ab code $(git -C $REPO_DIR rev-parse --short HEAD), pairs [$PAIRS], suffix $SUF seed $SEED CR $CR, NREP $NREP, TRAIN_ARGS [${TRAIN_ARGS:-}]" >> $J
[ -n "${EVAL_TIMEOUT:-}${NO_PUSH:-}" ] && log "hard_ab: EVAL_TIMEOUT ${EVAL_TIMEOUT:-none}, NO_PUSH ${NO_PUSH:-0}" >> $J
[ -n "${EVAL_TIMEOUT:-}" ] && export EVAL_TIMEOUT                 # pipeline_ep.sh's evaluations too
pip install -q fast_simplification >> $J 2>&1 || true              # kit budget_mesh (score_registered --meshes)
SCORE_MESH="--meshes $MESH_DIR"
if [ "${ASSET_SRC:-ours}" = public ]; then   # 2026-10-22 owner test: the organisers' public assets (scans + their collision
  rm -rf $ASSETS; mkdir -p $ASSETS/urdf      # meshes) in the simulator, everything else unchanged ("is ep24 about the mesh?")
  cp /content/t3/urdf/*_rigid.urdf $ASSETS/urdf/ && ln -s /content/t3/mesh $ASSETS/mesh || { log "public assets FAILED" >> $J; exit 1; }
  SCORE_MESH=""                              # registered against the scans themselves (~identity); our-mesh score kept too
  log "assets: PUBLIC scans + collision meshes ($(ls $ASSETS/urdf | wc -l) urdfs)" >> $J
else
# MA_ARGS (2026-10-31): extra make_assets.py arguments, e.g. --physics <props.json> (realistic masses; physics study).
  python $P/make_assets.py $MESH_DIR $ASSETS ${PIECES:+--pieces $PIECES} ${MA_ARGS:-} >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
  [ -n "${PIECES:-}" ] && log "assets: collision copy from convex pieces $PIECES ($(ls $PIECES | tr '\n' ' '))" >> $J
fi
if [ -n "${FC_OBJECT_KEYPOINT_SCALE:-}${FC_IMMEDIATE_FIRST_FRAME:-}" ] \
   || env | grep -q '^ENV_EP[0-9]*=.*FC_\(OBJECT_KEYPOINT_SCALE\|IMMEDIATE_FIRST_FRAME\)='; then   # opt-in patches
  python $REPO_DIR/ops/box/patch_flashchord.py $FC >> $J 2>&1 || { log "FlashCHORD patch FAILED" >> $J; exit 1; }
  [ -n "${FC_OBJECT_KEYPOINT_SCALE:-}" ] && export FC_OBJECT_KEYPOINT_SCALE
  [ -n "${FC_IMMEDIATE_FIRST_FRAME:-}" ] && export FC_IMMEDIATE_FIRST_FRAME
  log "patched FlashCHORD (ops/box/patch_flashchord.py): object keypoints ${FC_OBJECT_KEYPOINT_SCALE:-1} m, deployment-exact starts p ${FC_IMMEDIATE_FIRST_FRAME:-0} (job-wide; per-episode values in ENV_EP<N>)" >> $J
fi
if [ -n "${FC_FDR_OBJ:-}${FC_FDR_TIPS:-}" ]; then   # FlashDexRetarget-style rewards (ops/box/patch_flashchord_fdr.py)
  python $REPO_DIR/ops/box/patch_flashchord_fdr.py $FC >> $J 2>&1 || { log "FlashCHORD FDR patch FAILED" >> $J; exit 1; }
  export FC_FDR_OBJ FC_FDR_TIPS FC_FDR_OBJ_POINTS FC_FDR_OBJ_TOPK FC_FDR_OBJ_RADIUS FC_FDR_TIP_SIGMA FC_FDR_OBJ_MODE FC_FDR_OBJ_LEVER FC_FDR_OBJ_SIGMA FC_RC FC_RC_GAMMA FC_RC_BETA
  log "patched FlashCHORD (FDR rewards): object points ${FC_FDR_OBJ:-0} (mode ${FC_FDR_OBJ_MODE:-topk}, lever ${FC_FDR_OBJ_LEVER:-0.1}, sigma ${FC_FDR_OBJ_SIGMA:-config}, radius ${FC_FDR_OBJ_RADIUS:-true}, top-k ${FC_FDR_OBJ_TOPK:-3}), fingertip bound ${FC_FDR_TIPS:-0} (sigma ${FC_FDR_TIP_SIGMA:-0.01} m), reward centring ${FC_RC:-0}" >> $J
fi
if [ "${FC_VOC_INERTIA:-0}" != 0 ]; then   # VOC with the full inertia tensor (ops/box/patch_flashchord_voc.py); opt-in here
  python $REPO_DIR/ops/box/patch_flashchord_voc.py $FC >> $J 2>&1 || { log "FlashCHORD VOC patch FAILED" >> $J; exit 1; }
  export FC_VOC_INERTIA; log "patched FlashCHORD (VOC with the full inertia tensor)" >> $J
fi
if [ "${FC_DR_PATCH:-0}" = 1 ]; then   # (2026-10-31, pack 9b D arm) after the patches above; per-episode env in ENV_EP<N>
  python $REPO_DIR/ops/box/patch_flashchord_dr.py $FC >> $J 2>&1 || { log "FlashCHORD DR patch FAILED" >> $J; exit 1; }
  log "patched FlashCHORD (start-state randomisation of sampled training resets, ops/box/patch_flashchord_dr.py md5 $(md5sum < $REPO_DIR/ops/box/patch_flashchord_dr.py | cut -c1-12)); per-episode env: $(env | grep '^ENV_EP[0-9]*=' | sort | tr '\n' ' ')" >> $J
fi
if [ "${FC_LIFT_PATCH:-0}" = 1 ]; then   # (2026-11-02, pf-lift PREREG addendum C) inert unless FC_LIFT_WINDOWS is set: per episode in ENV_EP<N>
  python $REPO_DIR/ops/box/patch_flashchord_lift.py $FC >> $J 2>&1 || { log "FlashCHORD lift patch FAILED" >> $J; exit 1; }
  log "patched FlashCHORD (lift-window training starts, ops/box/patch_flashchord_lift.py md5 $(md5sum < $REPO_DIR/ops/box/patch_flashchord_lift.py | cut -c1-12)); per-episode env: $(env | grep '^ENV_EP[0-9]*=' | sort | tr '\n' ' ')" >> $J
fi
for run in $(for x in $PAIRS; do echo $x | cut -d: -f2; done | sort -u | grep -v '^local$'); do
  bash $OPS/store.sh pull-run $run >> $J 2>&1 || { log "pull-run $run FAILED" >> $J; exit 1; }
done
# the controls trained on the ep18 box after this session lost sight of it (ep12 / ep27): report their scores
for ep in 12 27; do
  F=/content/results/final/ep$ep; [ -s $F/final.json ] || continue
  python $P/score_registered.py $ep $F --meshes $MESH_DIR --out $O/control_ep$ep.json > /dev/null 2>&1
  log "control ep$ep: $(python -c "import json; b=json.load(open('$O/control_ep$ep.json'))['sim']; print('registered AUC', b['AUC'], 'SP', b['SP_SR'], 'MP', b['MP_SR'])" 2>&1 | tail -1)" >> $J
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

chosen() {  # the checkpoint behind a pipeline result: the sweep's choice, else the newest policy (and say so)
  local res=$1 run=$2 ck
  ck=$(python -c "import json; print(json.load(open('$res/selection.json'))['chosen'])" 2>/dev/null)
  if [ -s "$ck" ]; then echo $ck; return; fi
  ck=$(ls -v $run/policy_*.safetensors 2>/dev/null | tail -1); echo "chosen checkpoint missing; using $ck" >&2; echo $ck
}

evalrep() {  # $1 checkpoint, $2 output dir, $3 episode: NREP official evaluations (PAR at a time), each scored
  local ck=$1 d=$2 ep=$3 E6 i pids=()
  E6=$(printf %06d $ep); mkdir -p $d
  for i in $(seq 1 $NREP); do
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false ${EVAL_TIMEOUT:+timeout -k 60 $EVAL_TIMEOUT} .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1
      rc_=$?; [ -n "${EVAL_TIMEOUT:-}" ] && echo $rc_ > $d/r$i/eval_rc.txt   # 124 cut, 137 killed after the 60 s grace
      [ $rc_ = 0 ] && python $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
      && { [ $SPLIT = eval ] || python $P/score_registered.py $ep $d/r$i $SCORE_MESH > /dev/null 2>&1; } \
      && { [ $SPLIT = public ] && [ -z "$SCORE_MESH" ] && python $P/score_registered.py $ep $d/r$i --meshes $MESH_DIR \
             --out $d/r$i/score_registered_ours_ep$ep.json > /dev/null 2>&1 || true; } ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  python - $d $ep $ck << 'EOF' > $d/summary.json
import glob, json, os, sys
import numpy as np
d, ep, ck = sys.argv[1], int(sys.argv[2]), sys.argv[3]; rows = []
for r in sorted(glob.glob(f'{d}/r*/')):
    try:
        q = json.load(open(f'{r}qa_policy.json')); rows.append(dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=q['sim_vs_ref']))
        if os.path.exists(f'{r}score_registered_ep{ep}.json'):              # public episodes only (vs mocap)
            sr = json.load(open(f'{r}score_registered_ep{ep}.json')); s = sr['sim']; rows[-1].update(auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR'])
            rows[-1].update({k: sr[n]['AUC'] for k, n in (('ref_auc', 'reference'), ('floor_auc', 'static_floor')) if n in sr})
        if os.path.exists(f'{r}score_registered_ours_ep{ep}.json'):        # public-asset runs: also our mesh registered
            rows[-1]['auc_ours'] = json.load(open(f'{r}score_registered_ours_ep{ep}.json'))['sim']['AUC']
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'sim_vs_ref' in x]; agg = {}
for k in ('sim_vs_ref', 'auc', 'auc_ours', 'ref_auc', 'floor_auc'):
    v = np.array([x[k] for x in ok if k in x], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4))
if [x for x in ok if 'auc' in x]:
    agg['auc_of_best_sim_vs_ref'] = max([x for x in ok if 'auc' in x], key=lambda x: x['sim_vs_ref'])['auc']
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

one() {
  local ep=$1 run=$2 base=$3 perc=${4:-perc2} pre="" pd="" k R0 R1 ck0="" ck1 F LG ev=ENV_EP$1
  if [ "$perc" != perc2 ]; then                                    # e.g. the oracle twins: folders apart, public only
    [ $SPLIT = public ] && [ "$run" = local ] || { log "ab ep$ep: PERC $perc needs SPLIT=public and RUN local" >> $J; return 1; }
    pre=${perc}_; pd=/content/$perc; BASE_EVAL=0
  fi
  if [ -n "${!ev:-}" ]; then                                        # per-episode settings; one() runs in its own
    eval "export ${!ev}" || { log "ab ep$ep: bad $ev" >> $J; return 1; }   # subshell, so they stay with this episode
    log "ab ep$ep: $ev = ${!ev}" >> $J
  fi
  if [ "$base" = auto ]; then                                      # the variant auto_ep.sh published
    base=$(python -c "import json, os; print(os.path.basename(os.path.dirname(json.load(open('/content/results/final/ep$ep/final.json'))['chosen'])).replace('perc2', '', 1))" 2>/dev/null)
    [ -n "$base" ] || { log "ab ep$ep: no results/final/ep$ep/final.json in the pulled run" >> $J; return 1; }
    ck0=/content/results/final/ep$ep/policy.safetensors; log "ab ep$ep: auto base = $base ($ck0)" >> $J
  fi
  k=$base$SUF; R0=/content/refs/$perc$base/ep$ep; R1=/content/refs/$perc$k/ep$ep; LG=/content/hard_ab_${pre}ep$ep$SUF-s$SEED.log
  [ -d $R0/processed ] || { log "ab ep$ep: no reference $R0 in the pulled run" >> $J; return 1; }
  fix_assets $(ls $R0/processed/*/*/*.parquet | head -1) >> $J 2>&1 || { log "ab ep$ep: assets missing" >> $J; return 1; }
  rm -rf $R1; mkdir -p $(dirname $R1)                              # 2026-10-22: without the parent, cp failed silently
  cp -r $R0 $R1 || { log "ab ep$ep: copy $R0 -> $R1 FAILED" >> $J; return 1; }   # a real copy: stage 3c rewrites it
  [ -s $R1/hands.npz ] || { log "ab ep$ep: $R1 has no hands.npz" >> $J; return 1; }
  rm -f $R1/contact_retarget.json $R1/e2s_reference.parquet
  PERC=$perc VARIANT=$k PDIR=${pd:-$PDIR_ROOT}/ep$ep CONTACT_RETARGET=$CR SEED=$SEED CK_SWEEP="0.4 0.6 0.8" \
    bash $P/pipeline_ep.sh $ep > $LG 2>&1
  log "ab ep$ep $pre$k s$SEED: pipeline rc=$? $(grep -a 'contact_retarget:\|qa_policy:' $LG | cut -c1-300 | tr '\n' ' ')" >> $J
  F=/content/results/$perc$k/ep$ep-s$SEED
  [ $SPLIT = public ] && [ -s $F/episode_$(printf %06d $ep).parquet ] && python $P/score_registered.py $ep $F $SCORE_MESH > /dev/null 2>&1
  # the base checkpoint behind today's score is in git (policies/<run>/perc2<base>/); the store keeps every 10th only
  [ -s "$ck0" ] || ck0=$(ls $REPO_DIR/policies/$run/perc2$base/ep${ep}_policy_*.safetensors 2>/dev/null | head -1)
  [ -s "$ck0" ] || ck0=$(chosen /content/results/perc2$base/ep$ep-s42 /content/runs/perc2$base/ep$ep-s42 2>> $J)
  ck1=$(chosen $F /content/runs/$perc$k/ep$ep-s$SEED 2>> $J)
  local todo=("$pre$k-s$SEED:$ck1"); [ "$BASE_EVAL" = 1 ] && todo=("$base:$ck0" "${todo[@]}")
  for v in "${todo[@]}"; do
    [ -s "${v#*:}" ] || { log "ab ep$ep ${v%%:*}: no checkpoint" >> $J; continue; }
    [ -s $O/ep$ep/${v%%:*}/summary.json ] && { log "ab ep$ep ${v%%:*}: already evaluated" >> $J; continue; }
    evalrep ${v#*:} $O/ep$ep/${v%%:*} $ep
    log "ab ep$ep ${v%%:*} ($(basename ${v#*:})): $(python -c "import json; d=json.load(open('$O/ep$ep/${v%%:*}/summary.json')); print('n', d['n'], 'sim_vs_ref', d.get('sim_vs_ref'), 'registered AUC', d.get('auc'))" 2>&1 | tail -1)" >> $J
  done
}

label "hard A/B: $PAIRS"
pids=()
# trainings take turns on the GPU in PAIRS order (pipeline_ep.sh TRAIN_LOCK); the next episode starts its CPU stages
# once the previous one holds the GPU (or has ended), so its training is next in line
export TRAIN_LOCK=${TRAIN_LOCK:-/content/train.lock}; rm -f $TRAIN_LOCK.ep*
for x in $PAIRS; do
  IFS=: read -r ep run base perc <<< "$x"
  one $ep $run $base $perc & pids+=($!)
  while [ ! -e $TRAIN_LOCK.ep$ep ] && kill -0 $! 2> /dev/null; do sleep 20; done
  sleep 60
done
wait "${pids[@]}"
python - $O << 'EOF' > $O/summary.json
import glob, json, sys
out = {}
for f in sorted(glob.glob(f'{sys.argv[1]}/ep*/*/summary.json')):
    ep, v = f.split('/')[-3:-1]; d = json.load(open(f)); d.pop('rollouts', None); out.setdefault(ep, {})[v] = d
print(json.dumps(out, indent=1))
EOF
log "hard_ab summary: $(tr -d '\n ' < $O/summary.json | cut -c1-1500)" >> $J
[ "${NO_PUSH:-0}" = 1 ] || bash $OPS/store.sh push-run > /dev/null 2>&1 || true
