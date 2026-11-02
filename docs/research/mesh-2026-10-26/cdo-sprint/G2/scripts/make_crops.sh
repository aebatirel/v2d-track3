#!/bin/bash
# G2 (PREREG s7, addendum 2) generation inputs, local CPU, GT-free. crops.py exactly as for the 29 Oct probe:
#   --frames every 3rd frame, --n 2 (crops.py's own top-2 ranking), --hands when the episode has hands.npz,
#   our sweep tracks (data/sweep/ep<E>/poses.npz), our calibration, library_v3 (silhouette seed only).
# Reads: our tracks, hands, calibration, cam_a video, library_v3. No scan, mocap, parquet pose or *_align.
# Pairs (PREREG s7 plan): pot ep41/43/44, blue cup ep22/21/12, rack ep31/12/26, pitcher ep22/21.
# Output: $OUT/crops/ep<E>/<obj>_k<k>.png (+ _crops.json, overlays, logs) and $OUT/crops_flat/ep<E>_<obj>_k<k>.png
# (unique tags across episodes; the generator scripts use the file name as the tag).
# Usage: bash make_crops.sh OUT
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
REPO=/home/user/v2d-track3; OUT=$1
FR=$(seq -s, 0 3 600)
mkdir -p $OUT/crops $OUT/crops_flat
video() { for v in $S/data/store/ep$1_a.mp4 $(printf "$S/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_%06d.mp4" $1); do
  [ -s $v ] && { echo $v; return; }; done; }
run() {  # $1 episode, $2 object
  local e=$1 o=$2 h=""; [ -s $S/data/sweep/ep$e/hands.npz ] && h="--hands $S/data/sweep/ep$e/hands.npz"
  mkdir -p $OUT/crops/ep$e
  echo "$(date -u +%FT%TZ) ep$e $o video $(video $e) hands ${h:-none}"
  OMP_NUM_THREADS=1 nice -n 10 $S/venv/bin/python -W ignore $REPO/docs/research/mesh-2026-10-26/scripts/crops.py \
    --video $(video $e) --poses $S/data/sweep/ep$e/poses.npz --calib $S/data/calib.json --lib $REPO/meshes/library_v3 \
    --obj $o --out $OUT/crops/ep$e --frames $FR --n 2 $h > $OUT/crops/log_ep${e}_$o.txt 2>&1 \
    && echo "$(date -u +%FT%TZ) OK ep$e $o" || echo "$(date -u +%FT%TZ) FAIL ep$e $o"
}
PAIRS="41:white_pot 43:white_pot 44:white_pot 22:blue_cup 21:blue_cup 12:blue_cup 31:plastic_dish_rack 12:plastic_dish_rack
26:plastic_dish_rack 22:water_pitcher 21:water_pitcher"
i=0
for p in $PAIRS; do run ${p%%:*} ${p#*:} & i=$((i + 1)); [ $((i % 2)) = 0 ] && wait; done; wait
for p in $PAIRS; do
  e=${p%%:*}; o=${p#*:}
  for f in $OUT/crops/ep$e/${o}_k*.png; do [ -e "$f" ] && cp $f $OUT/crops_flat/ep${e}_$(basename $f); done
done
ls $OUT/crops_flat | sed 's/^/crop /'
echo "$(date -u +%FT%TZ) CROPS-DONE $(ls $OUT/crops_flat | wc -l) crops"
