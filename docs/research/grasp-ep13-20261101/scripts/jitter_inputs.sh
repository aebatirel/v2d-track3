#!/bin/bash
# Jitter check of the two ep13 INPUT references (the GL+ILC baselines; same --k 17 --seed 0 noise draws as the arms).
set -u; S=${S:?}; T=/home/user/v2d-track3/tools; FCD=$S/src/video_to_data/robotic_grounding/flash_chord
export OMP_NUM_THREADS=1 EMB=sharpa_hands_mid DEV=cpu KIT=$S/kit/v2d_submission_kit; cd $FCD
for REF in ${REFS:-P O P2 O2}; do
  case $REF in P|O) P=$(ls $S/inputs/ep13_$REF/processed/*/*/ref_in.parquet) ;; P2|O2) P=$(ls $S/gl2/ep13_${REF:0:1}/processed/*/*/ref_gl_ilc.parquet) ;; esac
  O=$S/ep13/${REF}_input; mkdir -p $O
  $S/fcvenv/bin/python $T/physics_solve/jitter_check.py $P --device cpu --k 17 --seed 0 --json $O/jitter.json --out $O/jitter.npz > $O/jitter.log 2>&1 &
done; wait; tail -n1 $S/ep13/*_input/jitter.log | cut -c1-300
