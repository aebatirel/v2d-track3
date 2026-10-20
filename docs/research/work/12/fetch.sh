#!/bin/bash
# fetch public videos: args: split ep cam
base=/Users/aebatirel/Documents/Code/v2d-research/data/track_3
for spec in "$@"; do
  IFS=: read split ep cam <<< "$spec"
  e=$(printf "%06d" $ep)
  d=$base/$split/videos/chunk-000/observation.images.ego_cam_$cam
  mkdir -p $d
  f=$d/episode_$e.mp4
  if [ -s $f ]; then echo "have $f"; continue; fi
  url=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/$split/videos/chunk-000/observation.images.ego_cam_$cam/episode_$e.mp4
  curl -sSL -m 300 -o $f.part.12 "$url" && mv $f.part.12 $f && echo "got $f $(stat -f%z $f)"
done
