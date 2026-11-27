#!/bin/bash
# Build the eval-video bundle for the deck from the renders (render_all.sh): one clip per eval episode, the 20-episode
# grid, key-frame stills and the small data files. Usage: B=<bundle dir> bash make_bundle.sh [OUT=/content/ev]
set -eu
B=${B:?B missing}; OUT=${OUT:-/content/ev}; HERE=$(cd "$(dirname "$0")" && pwd)
EPS="1 3 5 6 8 10 14 15 16 19 20 25 28 30 32 33 35 36 37 38"
mkdir -p $B/videos/per_episode $B/stills $B/data
for ep in $EPS; do
  o=$B/videos/per_episode/eval_$(printf %02d $ep).mp4
  [ -s $o ] || python3 $HERE/compose_eval.py episode $ep $o --out_dir $OUT
  n=$(ffprobe -v error -count_frames -show_entries stream=nb_read_frames -of csv=p=0 $o)
  ffmpeg -loglevel error -y -i $o -vf "select=eq(n\,$((n * 55 / 100)))" -frames:v 1 $B/stills/eval_$(printf %02d $ep).png
done
G=$B/videos/01_grid_eval20_real_vs_policy.mp4
[ -s $G ] || python3 $HERE/compose_eval.py grid $G --out_dir $OUT
for t in 3 7 11; do ffmpeg -loglevel error -y -ss $t -i $G -frames:v 1 $B/stills/grid_eval20_${t}s.png; done
cp $HERE/results/replay_vs_packed_cpu.json $HERE/results/table_fits.json $HERE/pack14p_policies.json $B/data/
echo "bundle: $(find $B -type f | wc -l) files, $(du -sh $B | cut -f1)"
