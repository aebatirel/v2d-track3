#!/bin/bash
# usage: dl.sh split cam ep...
split=$1; cam=$2; shift 2
base=/Users/aebatirel/Documents/Code/v2d-research/data/track_3/$split/videos/chunk-000/observation.images.ego_cam_$cam
mkdir -p $base
for ep in "$@"; do
  f=$(printf "episode_%06d.mp4" $ep)
  if [ -s $base/$f ]; then echo "have $f"; continue; fi
  url=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/$split/videos/chunk-000/observation.images.ego_cam_$cam/$f
  curl -sSL -m 300 -o $base/$f.part.13 "$url" && mv $base/$f.part.13 $base/$f && echo "got $cam $f $(stat -f %z $base/$f)"
done
