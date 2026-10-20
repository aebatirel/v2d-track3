#!/bin/bash
# usage: fetch.sh split cam ep...
B=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3
D=/Users/aebatirel/Documents/Code/v2d-research/data/track_3
split=$1; cam=$2; shift 2
for ep in "$@"; do
  f=$(printf "episode_%06d.mp4" $ep)
  out=$D/$split/videos/chunk-000/observation.images.ego_cam_$cam/$f
  [ -s "$out" ] && { echo "have $out"; continue; }
  mkdir -p $(dirname $out)
  curl -sSL -m 300 -o "$out.part.$$" "$B/$split/videos/chunk-000/observation.images.ego_cam_$cam/$f" && mv "$out.part.$$" "$out" && echo "got $out $(stat -f %z $out)"
done
