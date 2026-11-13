#!/bin/bash
# DR vs no-DR sampled resets on the 5 packed D-eval references (CPU, box patch set VOC + FDR + DR in rs/fc_box).
S=$1; T=/home/user/v2d-track3/tools/recipe_screen_tests/dr_patch_test.py; O=$S/dchk/out; mkdir -p $O
cd $S/src/video_to_data/robotic_grounding/flash_chord
for ep in 14 16 33 25 30; do
  ref=$(ls $S/dchk/ep$ep/processed/*/*/ref.parquet); emb=$( [ $ep = 25 ] || [ $ep = 30 ] && echo "" || echo sharpa_hands_mid )
  for arm in nodr dr; do
    extra=""; [ $arm = dr ] && extra="FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=42"
    env USE_COPY=$S/rs/fc_box W=${W:-32} OMP_NUM_THREADS=2 FC_VOC_INERTIA=1 FC_FDR_OBJ=1 FC_FDR_TIPS=1 ${emb:+EMB=$emb} $extra \
      timeout 1800 $S/fcvenv/bin/python $T $ref $O/ep${ep}_$arm.npz > $O/ep${ep}_$arm.log 2>&1
    echo "ep$ep $arm exit $? $(date -u +%T)"
  done
done
