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
  python $S/oracle_poses.py $EP /content/perc2/ep$EP $P > $P.oracle_log.txt 2>&1 || { echo "oracle FAILED"; cat $P.oracle_log.txt; exit 1; }
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

# 3) reference (table frame, Sharpa IK via unchanged E2S, contacts, FlashCHORD validation)
if ! ls $R/processed/sequence_id=$SEQ/robot_name=sharpa_wave/*.parquet > /dev/null 2>&1; then
  DEP=$(readlink -f $P/depths_fs0.5.npy)
  PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding /content/rtvenv/bin/python $S/mkref.py \
    --ep $EP --poses $P/poses.npz --depth $DEP --hands $R/hands.npz --out $R ${MKREF_ARGS:-} > $R/mkref_log.txt 2>&1 \
    || { echo "mkref FAILED"; tail -8 $R/mkref_log.txt; exit 1; }
fi
REFDIR=$R/processed/sequence_id=$SEQ/robot_name=sharpa_wave
echo "[$(date +%T)] reference: $REFDIR (code $(git -C $S rev-parse --short HEAD 2>/dev/null))"
[ "${STOP_AFTER:-}" = reference ] && exit 0

# 4) train (timing rule: fps 20 written in the parquet, motion_speed 1.0, sim=rl at 20 fps).
#    Checkpoints every 5M env steps (policy_<step> + state_<step>); a rerun resumes from the newest state_ file
#    (FlashCHORD training.resume; the replay buffer is not saved by default, so it refills after a resume).
if ! ls $RUN/policy_*.safetensors > /dev/null 2>&1 || [ ! -e $RUN/.done ]; then
  LAST=$(ls -v $RUN/state_*.safetensors 2> /dev/null | tail -1); RESUME=()
  [ -n "$LAST" ] && RESUME=(training.resume=true training.checkpoint_path=$LAST) && echo "[$(date +%T)] resuming from $LAST"
  cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py \
    experiment=sharpa_flash_sac "task.parquet='$REFDIR'" task.motion_speed=1.0 reset.seed=$SEED \
    logging.mode=disabled output_dir=$RUN training.total_environment_steps=$STEPS ${TRAIN_ARGS:-} "${RESUME[@]}" >> $RUN/train.log 2>&1 \
    && touch $RUN/.done || { echo "train FAILED"; tail -15 $RUN/train.log; exit 1; }
fi
CK=$(ls -v $RUN/policy_*.safetensors | tail -1)
echo "[$(date +%T)] trained: $CK (code $(git -C $S rev-parse --short HEAD 2>/dev/null))"

# 5) official evaluator, 1 world, trajectory export
cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
  evaluation.checkpoint=$CK evaluation.world_count=1 evaluation.reset_mode=explicit \
  evaluation.metrics_output=$RES/episode_$(printf %06d $EP).json \
  evaluation.object_trajectories_output=$RES/episode_$(printf %06d $EP).parquet \
  hydra.run.dir=$RES/hydra logging.mode=disabled > $RES/eval.log 2>&1 || { echo "eval FAILED"; tail -15 $RES/eval.log; exit 1; }
echo "[$(date +%T)] evaluated"

# 6) score the simulated trajectory against mocap (public episodes only; after inference)
[ $SPLIT = public ] && python $S/score_sim.py $EP $RES 2>&1 | tail -40
# 7) a video and a frame montage of the rollout, for looking at failures (RENDER=0 to skip)
[ "${RENDER:-1}" = 1 ] && { bash $S/render_rollout.sh $CK $RES/render || echo "render failed (not fatal)"; }
echo "[$(date +%T)] ep$EP DONE"
