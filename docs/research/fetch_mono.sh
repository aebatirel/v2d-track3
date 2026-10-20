#!/bin/bash
# Resumable sequential fetch of Track 3 ego clips (mono b/c for all eps, colour a for public).
B=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3
D=/Users/aebatirel/Documents/Code/v2d-research/data/track_3
EVAL="1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"
PUB="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
want() { for s in $2; do for c in $3; do printf "%s ego_cam_%s %06d\n" "$1" "$c" "$s"; done; done; }
{ want evaluation "$EVAL" "b c"; want public "$PUB" "b c a"; } | while read split cam ep; do
  rel="$split/videos/chunk-000/observation.images.$cam/episode_$ep.mp4"
  out="$D/$rel"; mkdir -p "$(dirname "$out")"
  # reuse a copy any agent saved elsewhere
  if [ ! -s "$out" ]; then alt=$(find /Users/aebatirel/Documents/Code/v2d-research/work -path "*$cam*" -name "episode_$ep.mp4" -size +1M 2>/dev/null | head -1); [ -n "$alt" ] && cp "$alt" "$out"; fi
  [ -s "$out" ] && continue
  for try in 1 2 3 4 5; do
    curl -sSL -m 600 -C - -o "$out.part" "$B/$rel" && mv "$out.part" "$out" && break
    sleep 20
  done
  [ -s "$out" ] && echo "ok $rel" || echo "FAIL $rel"
done
echo DONE
