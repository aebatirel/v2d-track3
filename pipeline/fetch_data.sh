#!/bin/bash
# Fetch the whole Track 3 dataset (1.47 GB on 2026-10-20: 20 public + 20 eval episodes, 3 cameras each, meshes, URDFs,
# calibration) and lay it out the way the pipeline scripts expect under /content/t3. Adds our wooden-spoon model.
# Usage: bash fetch_data.sh            (idempotent; files already present are kept)
# Layout:
#   /content/t3/v/ep{N}_{a,b,c}.mp4        public videos          /content/t3/ep{N}.parquet   public data (GT inside!)
#   /content/t3/eval/v/ep{N}_{a,b,c}.mp4   eval videos (no data)  /content/t3/calib.json      camera calibration
#   /content/t3/mesh/<obj>/*.glb           meshes                 /content/t3/urdf/<obj>_rigid.urdf
set -eu
ROOT=${ROOT:-/content}; T3=$ROOT/t3; HFD=$ROOT/hfds
REPO_DIR=${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}
mkdir -p $T3/v $T3/eval/v $T3/mesh $T3/urdf $HFD

if command -v hf > /dev/null; then
  hf download nvidia/video_to_data_challenge --repo-type dataset --include 'track_3/*' --local-dir $HFD > /dev/null
else
  huggingface-cli download nvidia/video_to_data_challenge --repo-type dataset --include 'track_3/*' --local-dir $HFD > /dev/null
fi
S=$HFD/track_3

lnk() { [ -s "$2" ] || ln -f "$1" "$2" 2> /dev/null || cp "$1" "$2"; }   # hard link when possible
for split in public evaluation; do
  out=$T3/v; [ $split = evaluation ] && out=$T3/eval/v
  for f in $S/$split/videos/chunk-000/observation.images.ego_cam_*/episode_*.mp4; do
    cam=$(basename $(dirname $f)); cam=${cam##*_}
    n=$(basename $f .mp4); n=$((10#${n#episode_}))
    lnk $f $out/ep${n}_$cam.mp4
  done
done
for f in $S/public/data/chunk-000/episode_*.parquet; do n=$(basename $f .parquet); n=$((10#${n#episode_})); lnk $f $T3/ep$n.parquet; done
lnk $S/public/meta/camera_calibration.json $T3/calib.json
cp -rn $S/public/mesh/. $T3/mesh/
cp -n $S/public/urdf/*.urdf $T3/urdf/
mkdir -p $T3/mesh/wooden_spoon
cp -n $REPO_DIR/spoon/wooden_spoon.glb $REPO_DIR/spoon/wooden_spoon.obj $T3/mesh/wooden_spoon/
cp -n $REPO_DIR/spoon/wooden_spoon_rigid.urdf $T3/urdf/

echo "public videos: $(ls $T3/v | wc -l)  eval videos: $(ls $T3/eval/v | wc -l)  parquets: $(ls $T3/*.parquet | wc -l)" \
     " meshes: $(ls $T3/mesh | wc -l)  urdfs: $(ls $T3/urdf | wc -l)"
[ $(ls $T3/v | wc -l) -eq 60 ] && [ $(ls $T3/eval/v | wc -l) -eq 60 ] && echo DATA-OK || echo DATA-INCOMPLETE
