#!/bin/bash
# Rack round R (C4 PREREG s14, addendum 9) generation inputs, local CPU, GT-free. Copy of G3 make_crops.sh (= G2's) with
# the R pairs and --n 6: crops.py exactly as for the 29 Oct probe / G2 / G3 (every 3rd frame, --hands when the episode
# has hands.npz, our sweep tracks, our calibration, library_v3 silhouette seed). crops.py's own ranking; ranks 1-2 are
# the G2 / G3 crops (already used), so only ranks 3-6 are copied to crops_flat.
# Reads: our tracks, hands, calibration, cam_a video, library_v3. No scan, mocap, parquet pose or *_align.
# Pairs (PREREG s14): plastic_dish_rack on every public rack episode with our track: 12, 13, 26, 27, 31
# (pipeline/mesh_v5.json lists exactly these five as the rack's public episodes).
# Output: $OUT/crops/ep<E>/<obj>_k<k>.png (+ _crops.json, overlays, logs) and $OUT/crops_flat/ep<E>_<obj>_k<k>.png
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
    --obj $o --out $OUT/crops/ep$e --frames $FR --n 6 $h > $OUT/crops/log_ep${e}_$o.txt 2>&1 \
    && echo "$(date -u +%FT%TZ) OK ep$e $o" || echo "$(date -u +%FT%TZ) FAIL ep$e $o"
}
PAIRS="12:plastic_dish_rack 13:plastic_dish_rack 26:plastic_dish_rack 27:plastic_dish_rack 31:plastic_dish_rack"
i=0
for p in $PAIRS; do run ${p%%:*} ${p#*:} & i=$((i + 1)); [ $((i % ${PAR:-4})) = 0 ] && wait; done; wait
for p in $PAIRS; do   # ranks 3-6 of crops.py's own ranking (chosen[2:6])
  e=${p%%:*}; o=${p#*:}
  for k in $($S/venv/bin/python -c "import json; print(' '.join(str(c['k']) for c in json.load(open('$OUT/crops/ep$e/${o}_crops.json'))['chosen'][2:6]))"); do
    cp $OUT/crops/ep$e/${o}_k$k.png $OUT/crops_flat/ep${e}_${o}_k$k.png
  done
done
ls $OUT/crops_flat | sed 's/^/crop /'
echo "$(date -u +%FT%TZ) CROPS-DONE $(ls $OUT/crops_flat | wc -l) crops"
