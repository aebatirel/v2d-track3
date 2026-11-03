#!/bin/bash
# G3 (PREREG s12) Pixal3D-MV view sets, local CPU, GT-free: gen/mv_views.py with the 29 Oct per-object flags
# (S/gen/run_views2.sh): non-skin-coloured objects (dust pan, lid) take at-rest frames plus held frames gated by a skin
# test (--skin 1 --held_speed_mm 8 --min_deg 15); the others (beige, sweeper, boards) at-rest frames only (--min_deg 8).
# Reads: our tracks, hands (or the stub below), calibration, cam_a video, library_v3 (silhouette seed, centre, extent).
# No scan, mocap, parquet pose or *_align.
# ep18 / ep24 have no hands.npz: mv_views.py needs one for a_offset (1 in every episode that has one) and the hand
# gate, so a stub with a_offset 1 and no valid hand is used there (= crops.py without --hands: rest/skin gates only).
# Then assemble_g3.py applies the 29 Oct assemble_views.py rule -> $OUT/views_final/ep<E>_<obj>.
# Usage: bash make_views.sh OUT
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
REPO=/home/user/v2d-track3; OUT=$1; G=$REPO/docs/research/mesh-2026-10-26/gen/mv_views.py
mkdir -p $OUT/views_sk $OUT/views_rest $OUT/hands_stub
video() { for v in $S/data/store/ep$1_a.mp4 $(printf "$S/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_%06d.mp4" $1); do
  [ -s $v ] && { echo $v; return; }; done; }
hands() {
  if [ -s $S/data/sweep/ep$1/hands.npz ]; then echo $S/data/sweep/ep$1/hands.npz; return; fi
  mkdir -p $OUT/hands_stub/ep$1
  $S/venv/bin/python - $S/data/sweep/ep$1/poses.npz $OUT/hands_stub/ep$1/hands.npz <<'PY'
import sys, numpy as np
n = len(np.load(sys.argv[1])['world_T_cam'])
z = np.zeros(n, bool); uv = np.zeros((n, 21, 2))
np.savez(sys.argv[2], a_offset=1, valid_left=z, valid_right=z, uv_a_left=uv, uv_a_right=uv, stub=True)
PY
  echo $OUT/hands_stub/ep$1/hands.npz; }
run() {  # $1 set dir, $2 episode, $3 object, rest: flags
  local d=$1 e=$2 o=$3; shift 3
  echo "$(date -u +%FT%TZ) $d ep$e $o $*: $(OMP_NUM_THREADS=1 nice -n 10 $S/venv/bin/python -W ignore $G --video $(video $e) \
    --poses $S/data/sweep/ep$e/poses.npz --hands $(hands $e) --calib $S/data/calib.json --lib $REPO/meshes/library_v3 \
    --obj $o --out $OUT/$d/ep${e}_$o "$@" 2>&1 | tail -1)"
}
SK="--skin 1 --held_speed_mm 8 --min_deg 15"; NS="--min_deg 8"
for e in 18 24; do hands $e > /dev/null; done
(run views_sk 18 mini_dust_pan $SK; run views_sk 39 mini_dust_pan $SK) &
(run views_sk 40 mini_dust_pan $SK; run views_sk 0 white_pot_lid $SK) &
(run views_sk 2 white_pot_lid $SK; run views_rest 11 beige_cup $NS; run views_rest 24 wooden_piece_1 $NS) &
(run views_rest 18 mini_sweeper $NS; run views_rest 31 mini_sweeper $NS; run views_rest 24 wooden_piece_2 $NS) &
wait
# at-rest fallback for a skin-gated set whose view 0 mask / silhouette IoU < 0.75 (assemble rule)
for d in $OUT/views_sk/ep*; do
  b=$(basename $d); e=${b%%_*}; e=${e#ep}; o=${b#*_}
  ok=$($S/venv/bin/python -c "import json; m=json.load(open('$d/probe_meta.json')); print(int(m['chosen'][0]['iou_sil_mask'] >= 0.75))" 2> /dev/null || echo 0)
  [ "$ok" = 1 ] || run views_rest $e $o --skin 1 --min_deg 15
done
$S/venv/bin/python $(dirname $0)/assemble_g3.py $OUT
echo "$(date -u +%FT%TZ) VIEWS-DONE $(ls -d $OUT/views_final/ep* | wc -l) view sets"
