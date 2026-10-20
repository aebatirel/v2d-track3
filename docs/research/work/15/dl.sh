#!/bin/bash
# usage: dl.sh split cam ep...
split=$1; cam=$2; shift 2
base=/Users/aebatirel/Documents/Code/v2d-research/data/track_3/$split/videos/chunk-000/observation.images.ego_cam_$cam
mkdir -p "$base"
for e in "$@"; do
  f=$(printf "episode_%06d.mp4" $e)
  if [ -s "$base/$f" ]; then echo "have $f"; continue; fi
  url="https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/$split/videos/chunk-000/observation.images.ego_cam_$cam/$f"
  tmp="$base/$f.part.15.$$"
  if curl -sSL -m 300 -f -o "$tmp" "$url"; then
    if [ -s "$base/$f" ]; then rm -f "$tmp"; else mv "$tmp" "$base/$f"; fi
    echo "got $f $(stat -f %z "$base/$f")"
  else echo "FAIL $f"; rm -f "$tmp"; fi
done
