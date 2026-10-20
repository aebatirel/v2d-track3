#!/bin/bash
# Fetch all public Track 3 episodes (cams b/c, parquet) + all meshes, then run perc.py on each.
# Usage: setsid nohup bash /content/run_public.sh "0 2 11 ..." > /content/run_public.log 2>&1 < /dev/null &
EPS=${1:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
B=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/public
mkdir -p /content/t3/v /content/perc
for o in beige_cup blue_cup mini_dust_pan mini_sweeper plastic_dish_rack water_pitcher white_pot white_pot_lid wooden_piece_1 wooden_piece_2; do
  mkdir -p /content/t3/mesh/$o
  for g in $o ${o}_visual ${o}_collision; do f=/content/t3/mesh/$o/$g.glb; [ -s $f ] || curl -fsSL -o $f $B/mesh/$o/$g.glb || rm -f $f; done
done
for EP in $EPS; do
  for c in b c; do f=/content/t3/v/ep${EP}_$c.mp4; [ -s $f ] || curl -fsSL -o $f $B/videos/chunk-000/observation.images.ego_cam_$c/episode_$(printf %06d $EP).mp4; done
  f=/content/t3/ep${EP}.parquet; [ -s $f ] || curl -fsSL -o $f $B/data/chunk-000/episode_$(printf %06d $EP).parquet
done
echo FETCH-OK
for EP in $EPS; do
  mkdir -p /content/perc/ep$EP
  EP=$EP python /content/perc.py > /content/perc/ep$EP/log.txt 2>&1 && echo "EP $EP OK" || echo "EP $EP FAIL"
done
echo RUN-DONE
