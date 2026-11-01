#!/bin/bash
# One public episode end to end on a GPU box (Colab G4 or Vast; /content = the work root):
#   perception (perc2 by default; PERC=perc4 for the unvalidated perc.py) -> hands (hands_mp.py) -> reference (mkref.py) -> FlashCHORD train -> official eval -> score vs mocap
# Usage: STEPS=250003456 setsid nohup bash /content/v2d-track3/pipeline/pipeline_ep.sh 12 > /content/pipe_ep12.log 2>&1 < /dev/null &
# Stages are skipped when their output already exists (delete the output to redo a stage).
set -u
EP=$1; STEPS=${STEPS:-250003456}; SEED=${SEED:-42}; PERC=${PERC:-perc2}
S=${REPO_DIR:-/content/v2d-track3}/pipeline
# SPLIT=eval: an eval episode (videos in /content/t3/eval/v, object names from the kit roster, no ground truth):
# perception, hands and mkref read SPLIT from the environment; scoring against mocap is skipped. Public and eval
# episode numbers are disjoint, so the folders below cannot collide.
export SPLIT=${SPLIT:-public}
ROSTER=/content/kit/v2d_submission_kit/data/track_3_evaluation_objects.json
if [ $SPLIT = eval ]; then
  [ $PERC = oracle ] && { echo "PERC=oracle needs mocap; not allowed with SPLIT=eval"; exit 1; }
  python -c "import json,sys; sys.exit(0 if '$EP' in json.load(open('$ROSTER'))['episodes'] else 1)" \
    || { echo "episode $EP is not in the eval roster $ROSTER"; exit 1; }
elif [ ! -s /content/t3/ep$EP.parquet ]; then
  echo "episode $EP has no public parquet (an eval episode needs SPLIT=eval)"; exit 1
fi
# PERC=oracle (public episodes only) swaps in mocap object poses on top of perc2's camera trajectory: oracle_poses.py
# (2026-10-30 v2: with MESH_DIR the mocap poses are converted to our meshes' body frames and aligned to the perceived
# table by gravity; ORACLE_ARGS is passed through, e.g. "--align anchor0" for the 20 Oct rule)
case $PERC in perc2|oracle) PSCRIPT=$S/perc2.py ;; perc4) PSCRIPT=$S/perc.py ;; *) echo "unknown PERC=$PERC"; exit 1 ;; esac
# VARIANT (e.g. "v") keeps a variant's refs, runs and results apart (refs/perc2v/...); PDIR overrides the perception
# folder (e.g. /content/perc2c/epN from DET_PRIOR=compact); HANDS_ARGS is passed to hands_mp.py (e.g. "--linker greedy").
V=${VARIANT:-}
P=${PDIR:-/content/$PERC/ep$EP}; R=/content/refs/$PERC$V/ep$EP; RUN=/content/runs/$PERC$V/ep$EP-s$SEED; RES=/content/results/$PERC$V/ep$EP-s$SEED
FC=/content/v2d/robotic_grounding/flash_chord
mkdir -p $P $R $RUN $RES
SEQ=$(printf 't3_ep%03d' $EP)
echo "[$(date +%T)] ep$EP start ($SPLIT, perception $PERC, steps $STEPS, seed $SEED, code $(git -C $S rev-parse --short HEAD 2>/dev/null))"

# 1) perception (uses a cached depth if present)
if [ $PERC = oracle ] && [ ! -s $P/poses.npz ]; then
  [ -s /content/perc2/ep$EP/poses.npz ] || PERC=perc2 SEED=$SEED STEPS=0 STOP_AFTER=perception bash $0 $EP || exit 1
  python $S/oracle_poses.py $EP /content/perc2/ep$EP $P ${MESH_DIR:+--meshes $MESH_DIR} ${ORACLE_ARGS:-} > $P.oracle_log.txt 2>&1 \
    || { echo "oracle FAILED"; tail -5 $P.oracle_log.txt; exit 1; }
  cp /content/perc2/ep$EP/log.txt $P/log.txt
fi
if [ ! -s $P/poses.npz ]; then
  D=$(ls /content/cache/depth/ep$EP/depths_fs0.5.npy /content/perc/ep$EP/depths_fs0.5.npy /content/perc2/ep$EP/depths_fs0.5.npy 2>/dev/null | head -1)
  [ -n "$D" ] && [ ! -e $P/depths_fs0.5.npy ] && ln -sf $(readlink -f $D) $P/
  KF_MIN=120 EP=$EP OUT=$P python $PSCRIPT > $P/log.txt 2>&1 || { echo "perception FAILED"; tail -15 $P/log.txt; exit 1; }
fi
echo "[$(date +%T)] perception: $(grep -a '^\[.* vo  \|DONE (eval' $P/log.txt | tail -1 | cut -c1-120)"
[ "${STOP_AFTER:-}" = perception ] && exit 0

# 2) hands (MediaPipe on colour cam_a, lifted with stereo depth)
if [ ! -s $R/hands.npz ]; then
  DEP=$(readlink -f $P/depths_fs0.5.npy)
  /content/mpvenv/bin/python $S/hands_mp.py --ep $EP ${HANDS_ARGS:-} --depth $DEP --poses $P/poses.npz --out $R > $R/hands_log.txt 2>&1 \
    || { echo "hands FAILED"; tail -5 $R/hands_log.txt; exit 1; }
fi
echo "[$(date +%T)] hands done"
# 2b) bone-length-consistent refinement (hand_refine.py; HAND_REFINE=0 to skip): mkref then reads hands_refined.npz
HANDS=$R/hands.npz
if [ "${HAND_REFINE:-1}" = 1 ]; then
  [ -s $R/hands_refined.npz ] || python $S/hand_refine.py --hands $R/hands.npz --poses $P/poses.npz \
    --out $R/hands_refined.npz > $R/hand_refine_log.txt 2>&1 || echo "hand_refine failed (using raw hands)"
  [ -s $R/hands_refined.npz ] && HANDS=$R/hands_refined.npz
fi
[ "${STOP_AFTER:-}" = hands ] && exit 0   # mesh v5 G1 (spec 12): tracks + hands only; mkref would read the scans without ASSETS

# 3) reference (table frame, Sharpa IK via unchanged E2S, contacts, FlashCHORD validation)
if ! ls $R/processed/sequence_id=$SEQ/robot_name=sharpa_wave/*.parquet > /dev/null 2>&1; then
  DEP=$(readlink -f $P/depths_fs0.5.npy)
  PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding /content/rtvenv/bin/python $S/mkref.py \
    --ep $EP --poses $P/poses.npz --depth $DEP --hands $HANDS --out $R ${MKREF_ARGS:-} > $R/mkref_log.txt 2>&1 \
    || { echo "mkref FAILED"; tail -8 $R/mkref_log.txt; exit 1; }
fi
REFDIR=$R/processed/sequence_id=$SEQ/robot_name=sharpa_wave
echo "[$(date +%T)] reference: $REFDIR (code $(git -C $S rev-parse --short HEAD 2>/dev/null))"
# 3b) reference QA (robot wrist IK error, wrist jumps): $R/qa_ref.json, used by auto_ep.sh to choose/retry variants
[ -s $R/ref_summary.json ] && echo "[$(date +%T)] qa_ref: $(python $S/qa.py ref $R/ref_summary.json 2>&1 | tail -1)"
# 3c) contact-anchored retargeting (CONTACT_RETARGET=1; contact_retarget.py, CPU, a few minutes): the robot hand is
#     re-fitted to the objects' collision shapes (fingertips on the human contacts, no penetration). The E2S parquet is
#     kept as $R/e2s_reference.parquet, the stats go to $R/contact_retarget.json. Use a VARIANT so refs stay apart.
if [ "${CONTACT_RETARGET:-0}" = 1 ] && [ ! -s $R/contact_retarget.json ]; then
  REFP=$(ls $REFDIR/*.parquet | head -1); CRT=$R/cr_stage
  CRP=$CRT/processed/sequence_id=$SEQ/robot_name=sharpa_wave/$(basename $REFP)
  mkdir -p $(dirname $CRP) && ln -sfn $R/reconstructed_stage $CRT/reconstructed_stage
  (cd $FC && FC=$FC .venv/bin/python $S/contact_retarget.py $REFP $CRP ${CR_ARGS:-} > $R/contact_retarget_log.txt 2>&1) \
    || { echo "contact_retarget FAILED"; tail -8 $R/contact_retarget_log.txt; exit 1; }
  { [ -e $R/e2s_reference.parquet ] || cp $REFP $R/e2s_reference.parquet; } && cp $CRP $REFP && cp ${CRP%.parquet}_contact_retarget.json $R/contact_retarget.json \
    && rm -rf $CRT || { echo "contact_retarget: could not install the new reference"; exit 1; }
  echo "[$(date +%T)] contact_retarget: $(tr -d '\n ' < $R/contact_retarget.json | cut -c1-400)"
fi
[ "${STOP_AFTER:-}" = reference ] && exit 0

# 4) train (timing rule: fps 20 written in the parquet, motion_speed 1.0, sim=rl at 20 fps).
#    Checkpoints every 10,000,384 env steps (policy_<step> + state_<step>); a rerun resumes from the newest state_ file
#    (FlashCHORD training.resume; the replay buffer is not saved by default, so it refills after a resume).
if ! ls $RUN/policy_*.safetensors > /dev/null 2>&1 || [ ! -e $RUN/.done ]; then
  LAST=$(ls -v $RUN/state_*.safetensors 2> /dev/null | tail -1); RESUME=()
  [ -n "$LAST" ] && RESUME=(training.resume=true training.checkpoint_path=$LAST) && echo "[$(date +%T)] resuming from $LAST"
  # TRAIN_LOCK (a file path): trainings on one box take turns on the GPU (two at once ran ~30 % slower in total than
  # one after the other, 2026-10-21); the lock is held for the training only, so evaluations overlap the next training
  if [ -n "${TRAIN_LOCK:-}" ]; then
    exec 9> $TRAIN_LOCK; echo "[$(date +%T)] waiting for the GPU (TRAIN_LOCK)"; flock 9; touch $TRAIN_LOCK.ep$EP
    echo "[$(date +%T)] GPU lock acquired"
  fi
  cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py \
    experiment=sharpa_flash_sac "task.parquet='$REFDIR'" task.motion_speed=1.0 reset.seed=$SEED \
    logging.mode=disabled output_dir=$RUN training.total_environment_steps=$STEPS ${TRAIN_ARGS:-} "${RESUME[@]}" >> $RUN/train.log 2>&1 \
    && touch $RUN/.done || { echo "train FAILED"; tail -15 $RUN/train.log; exit 1; }
fi
exec 9>&-                                                    # release TRAIN_LOCK (no-op without it)
CK=$(ls -v $RUN/policy_*.safetensors | tail -1)
echo "[$(date +%T)] trained: $CK (code $(git -C $S rev-parse --short HEAD 2>/dev/null))"

# 5) official evaluator, 1 world, trajectory export
#    EVAL_TIMEOUT=<s> (2026-10-31, opt-in; hard_ab.sh exports it): cut an evaluation that runs longer (timeout -k 60) and
#    write its exit code to eval_rc.txt (124 cut, 137 killed after the grace); unset = unchanged
cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false ${EVAL_TIMEOUT:+timeout -k 60 $EVAL_TIMEOUT} .venv/bin/python scripts/evaluate_policy.py \
  evaluation.checkpoint=$CK evaluation.world_count=1 evaluation.reset_mode=explicit \
  evaluation.metrics_output=$RES/episode_$(printf %06d $EP).json \
  evaluation.object_trajectories_output=$RES/episode_$(printf %06d $EP).parquet \
  hydra.run.dir=$RES/hydra logging.mode=disabled > $RES/eval.log 2>&1; rc_=$?
[ -n "${EVAL_TIMEOUT:-}" ] && echo $rc_ > $RES/eval_rc.txt
[ $rc_ = 0 ] || { echo "eval FAILED"; tail -15 $RES/eval.log; exit 1; }
echo "[$(date +%T)] evaluated"
# 5b) checkpoint sweep (CK_SWEEP = fractions of training, e.g. "0.4 0.6 0.8"; default off): evaluate earlier policies
#     and keep the one that tracks OUR reference best (qa.py policy; no ground truth). The chosen rollout is copied
#     over the main one; every candidate stays in $RES/sweep/<step>/; $RES/selection.json records the choice.
python $S/qa.py policy $RES $EP > /dev/null 2>&1
if [ -n "${CK_SWEEP:-}" ]; then
  E6=$(printf %06d $EP); best=$(python -c "import json; print(json.load(open('$RES/qa_policy.json'))['sim_vs_ref'])"); bestck=$CK
  floor=$(python -c "import json; print(json.load(open('$RES/qa_policy.json'))['floor_vs_ref'])"); seen=" $CK "
  sweep() {                                                  # evaluate the checkpoints nearest the given fractions
    for fr in "$@"; do
      want=$(python -c "print(int($fr * $STEPS))")
      C2=$(ls $RUN/policy_*.safetensors | python -c "import sys; L=[l.strip() for l in sys.stdin]; print(min(L, key=lambda f: abs(int(f.rsplit('_',1)[1].split('.')[0]) - $want)))")
      case "$seen" in *" $C2 "*) continue ;; esac; seen="$seen$C2 "
      D2=$RES/sweep/$(basename $C2 .safetensors); mkdir -p $D2
      (cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false ${EVAL_TIMEOUT:+timeout -k 60 $EVAL_TIMEOUT} .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$C2 evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$D2/episode_$E6.json evaluation.object_trajectories_output=$D2/episode_$E6.parquet \
        hydra.run.dir=$D2/hydra logging.mode=disabled > $D2/eval.log 2>&1); rc_=$?
      [ -n "${EVAL_TIMEOUT:-}" ] && echo $rc_ > $D2/eval_rc.txt
      [ $rc_ = 0 ] || continue
      v=$(python $S/qa.py policy $D2 $EP 2>/dev/null | python -c "import json,sys; print(json.loads(sys.stdin.read())['sim_vs_ref'])")
      echo "[$(date +%T)] sweep $(basename $C2): sim_vs_ref $v (best so far $best, floor $floor)"
      if python -c "import sys; sys.exit(0 if float('$v') > float('$best') else 1)"; then best=$v; bestck=$C2; fi
    done
  }
  sweep $CK_SWEEP
  # floor guard (2026-10-22): if every checkpoint so far tracks our reference worse than leaving the objects where
  # they start (qa verdict 'harmful'), try more checkpoints of the same run; the submission must stay a learned policy
  if python -c "import sys; sys.exit(0 if float('$best') < float('$floor') else 1)"; then
    echo "[$(date +%T)] floor guard: best sim_vs_ref $best < floor $floor; extra sweep ${CK_SWEEP_EXTRA:-0.2 0.3 0.5 0.7 0.9}"
    sweep ${CK_SWEEP_EXTRA:-0.2 0.3 0.5 0.7 0.9}
  fi
  if [ "$bestck" != "$CK" ]; then
    D2=$RES/sweep/$(basename $bestck .safetensors); mkdir -p $RES/sweep/final
    cp $RES/episode_$E6.json $RES/episode_$E6.parquet $RES/qa_policy.json $RES/sweep/final/
    cp $D2/episode_$E6.json $D2/episode_$E6.parquet $D2/qa_policy.json $RES/; CK=$bestck
  fi
  harm=$(python -c "print('true' if float('$best') < float('$floor') else 'false')")
  echo "{\"chosen\": \"$CK\", \"sim_vs_ref\": $best, \"floor_vs_ref\": $floor, \"harmful\": $harm}" > $RES/selection.json
fi
echo "[$(date +%T)] qa_policy: $(cat $RES/qa_policy.json | tr -d '\n ')"

# 6) score the simulated trajectory against mocap (public episodes only; after inference)
[ $SPLIT = public ] && python $S/score_sim.py $EP $RES 2>&1 | tail -40
# 7) a video and a frame montage of the rollout, for looking at failures (RENDER=0 to skip)
# the whole episode: render_rollout.sh defaults to 181 frames (ep12), which cut longer episodes short (2026-10-21)
NF=$(python -c "import numpy as np; print(len(np.load('$P/poses.npz')['world_T_cam']))" 2>/dev/null || echo 181)
[ "${RENDER:-1}" = 1 ] && { bash $S/render_rollout.sh $CK $RES/render $NF || echo "render failed (not fatal)"; }
echo "[$(date +%T)] ep$EP DONE"
