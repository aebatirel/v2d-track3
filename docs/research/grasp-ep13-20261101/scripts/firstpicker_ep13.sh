#!/bin/bash
# First-picker lock on ep13 (1 Nov 2026, CPU, $0): pipeline/grasp_lock.py --single_hand 2 on the support-filled inputs
# (P_sf, O_sf), then wrist ILC (tools/cpu_glock_zero.sh, the box's GL_ARGS with --single_hand 2 instead of 1), then
# jitter_check --k 17 --seed 0 (the noise draws of every ep13 arm). Compare with P / O (single 1) and P2 / O2 (two-hand).
set -u; S=${S:?}; R=/home/user/v2d-track3
export FCD=$S/src/video_to_data/robotic_grounding/flash_chord PY=$S/fcvenv/bin/python SPY=$S/venv/bin/python KIT=$S/kit/v2d_submission_kit OMP_NUM_THREADS=1
GA="--single_hand 2 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
for X in P O; do (
  IN=$(ls $S/inputs/ep13_${X}_sf/processed/*/*/ref_in.parquet)
  bash $R/tools/cpu_glock_zero.sh $IN $S/fp/ep13_$X "$GA" > /dev/null 2>&1 || { echo "$X: lock FAILED"; exit 1; }
  O=$S/ep13/${X}1F_input; mkdir -p $O; G=$(ls $S/fp/ep13_$X/processed/*/*/ref_gl_ilc.parquet)
  ( cd $FCD && EMB=sharpa_hands_mid DEV=cpu $PY $R/tools/physics_solve/jitter_check.py $G --device cpu --k 17 --seed 0 --json $O/jitter.json --out $O/jitter.npz ) > $O/jitter.log 2>&1
  echo "$X: $(grep -a 'single-hand carry' $S/fp/ep13_$X/gl.log | head -1)"; tail -2 $S/fp/ep13_$X/run.log | head -1; tail -1 $O/jitter.log | cut -c1-260
) & done; wait
