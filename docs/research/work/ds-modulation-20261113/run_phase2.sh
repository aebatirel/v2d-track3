#!/bin/bash
# PHASE 2 of PREREG.md (this folder). CPU only, $0, one job at a time (other agents share the 4 CPUs). Written in phase 1
# and NOT run there. Run only after PREREG.md is committed and the owner says go. GT-free: our references, our meshes.
# Usage: W=<scratch dir with store/ and the FlashCHORD checkout> bash run_phase2.sh
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../../../.." && pwd); HERE=$REPO/docs/research/work/ds-modulation-20261113
W=${W:?set W}; FC=${FC:-$W/fc/v2d/robotic_grounding/flash_chord}; PY=$FC/.venv/bin/python
OUT=${OUT:-$W/dsmod/phase2}; ASSETS=$W/dsmod/assets_v3; EPS=${EPS:-"2 11 12 13 31"}
export FC FLASH_CHORD_CACHE_DIR=$W/dsmod/fc_cache DEV=cpu OMP_NUM_THREADS=1   # own CoACD cache: never write into FC
mkdir -p $OUT $FLASH_CHORD_CACHE_DIR
echo "commit $(git -C $REPO rev-parse HEAD) dirty=$(git -C $REPO status --porcelain | wc -l)" | tee $OUT/run.log
[ -d $ASSETS ] || nice $PY -B $REPO/pipeline/make_assets.py $REPO/meshes/library_v3 $ASSETS | tee -a $OUT/run.log
for e in $EPS; do
  D=$OUT/ep$e; mkdir -p $D
  SRC=$W/store/$(grep "/perc2/ep$e/" $W/work/refsweep_perc2_paths.txt)
  SUB=${SRC#*/processed/}
  # 1. stage: our reference with OUR library_v3 simulator assets (only the two path columns change)
  nice $PY -B $HERE/eval_ds.py stage $SRC $ASSETS $D/orig_tree >> $OUT/run.log
  ln -sf $D/orig_tree/processed/$SUB $D/orig.parquet
  for arm in clear ds; do mkdir -p $D/${arm}_tree; cp -r $D/orig_tree/reconstructed_stage $D/${arm}_tree/; done
  cd $FC
  # 2. DS arm (frozen DEFAULTS of pipeline/ds_modulate.py; phases from the original reference, used by every arm)
  s=$(date +%s)
  nice $PY -B $REPO/pipeline/ds_modulate.py $D/orig.parquet $D/ds_tree/processed/$SUB --meshes $ASSETS/mesh \
      --hand_urdf_dir $FC/src/flash_chord/assets/urdfs/sharpawave --geom fc_hulls \
      --phases_json $D/phases.json --report $D/ds_report.json > $D/ds.log 2>&1
  echo "ep$e ds seconds=$(( $(date +%s) - s ))" | tee -a $OUT/run.log
  ln -sf $D/ds_tree/processed/$SUB $D/ds.parquet
  # 3. existing hand-side clearance tool, its defaults (rounds 3, margin 1 mm, lam 4)
  s=$(date +%s)
  nice $PY -B $REPO/pipeline/robot_clearance.py $D/orig.parquet $D/clear_tree/processed/$SUB > $D/clear.log 2>&1
  echo "ep$e clear seconds=$(( $(date +%s) - s ))" | tee -a $OUT/run.log
  ln -sf $D/clear_tree/processed/$SUB $D/clear.parquet
  # 4. primary metric: the simulator's own collision geometry at every reference frame, for each arm
  for arm in orig clear ds; do
    s=$(date +%s)
    nice $PY -B $HERE/eval_ds.py metric $D/$arm.parquet $D/phases.json $D/metric_$arm.json > $D/metric_$arm.log 2>&1
    echo "ep$e metric $arm seconds=$(( $(date +%s) - s ))" | tee -a $OUT/run.log
  done
  cd - > /dev/null
done
# 5. pooled metrics, guards, verdict (PREREG section 6)
$PY -B $HERE/eval_ds.py summary $OUT $EPS | tee -a $OUT/run.log
# 6. optional, descriptive only (PREREG section 5.4): zero-action replays and bystander displacement
if [ "${REPLAY:-0}" = 1 ]; then
  for e in $EPS; do D=$OUT/ep$e; cd $FC
    for arm in orig clear ds; do
      N=$($PY -c "import numpy as np, pyarrow.parquet as pq, sys; print(len(np.array(pq.read_table(sys.argv[1]).column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))" $D/$arm.parquet)
      nice $PY -B $REPO/tools/trace_rollout.py zero $D/replay_$arm.npz $D/$arm.parquet $N > $D/replay_$arm.log 2>&1
      $PY -B $HERE/eval_ds.py bystander $D/replay_$arm.npz $D/$arm.parquet $D/phases.json | tee -a $OUT/run.log
    done; cd - > /dev/null
  done
fi
