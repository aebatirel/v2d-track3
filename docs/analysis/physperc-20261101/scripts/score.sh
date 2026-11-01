#!/bin/bash
# score.sh TAG TRACKS_ROOT [EPS...]: pipeline/score_registered.py (9a+ meshes, public scans) on every episode; skip existing.
S=/tmp/claude-0/-home-user-v2d-track3/a12274fe-3848-57a7-b0a0-aa73b1334318/scratchpad
R=/home/user/v2d-track3
tag=$1; root=$2; shift 2
EPS=${@:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
mkdir -p $S/runs/$tag; cd $S
for e in $EPS; do
  [ -s runs/$tag/ep$e.json ] && continue
  nice -n 5 venv/bin/python -I $R/pipeline/score_registered.py $e $root/ep$e/poses_world_vo.npz --meshes mesh9a --t3 t3 \
    --kit kit/v2d_submission_kit --out runs/$tag/ep$e.json > runs/$tag/ep$e.log 2>&1 && echo "OK $tag ep$e" || echo "FAIL $tag ep$e"
done
