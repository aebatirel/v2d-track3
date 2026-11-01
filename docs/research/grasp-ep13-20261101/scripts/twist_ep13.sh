#!/bin/bash
# Repair (a) test on ep13 (1 Nov 2026, CPU, $0): pipeline/twist_canon.py on the support-filled references BEFORE the lock
# (P_sf, O_sf), then the same two-hand lock + wrist ILC as P2 / O2 (tools/cpu_glock_zero.sh, GL_ARGS = box default minus
# --single_hand 1), then jitter_check --k 17 --seed 0 (same noise draws as every ep13 arm). Compare with P2 / O2.
# Usage: S=<scratchpad> twist_ep13.sh   -> S/twist/ep13_{P,O}/ and S/ep13/{P2T,O2T}_input/jitter.{json,npz}
set -u; S=${S:?}; R=/home/user/v2d-track3
export FCD=$S/src/video_to_data/robotic_grounding/flash_chord PY=$S/fcvenv/bin/python SPY=$S/venv/bin/python KIT=$S/kit/v2d_submission_kit OMP_NUM_THREADS=1
GA="--mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
for X in P O; do (
  IN=$(ls $S/inputs/ep13_${X}_sf/processed/*/*/ref_in.parquet); D=$(dirname $IN)
  $SPY -I $R/pipeline/twist_canon.py $IN $D/ref_tc.parquet > $S/twist_${X}_canon.log 2>&1
  bash $R/tools/cpu_glock_zero.sh $D/ref_tc.parquet $S/twist/ep13_$X "$GA" > /dev/null 2>&1
  O=$S/ep13/${X}2T_input; mkdir -p $O; G=$(ls $S/twist/ep13_$X/processed/*/*/ref_gl_ilc.parquet)
  ( cd $FCD && EMB=sharpa_hands_mid DEV=cpu $PY $R/tools/physics_solve/jitter_check.py $G --device cpu --k 17 --seed 0 --json $O/jitter.json --out $O/jitter.npz ) > $O/jitter.log 2>&1
  echo "$X: $(cat $S/twist_${X}_canon.log | head -1)"; tail -2 $S/twist/ep13_$X/run.log | head -1; tail -1 $O/jitter.log | cut -c1-260
) & done; wait
