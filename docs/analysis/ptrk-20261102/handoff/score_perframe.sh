#!/bin/bash
# score13.sh TAG TRACKS_ROOT MESHDIR [EPS...]: score_registered.py with a given mesh dir (per-episode subdirs allowed)
S=/tmp/claude-0/-home-user-v2d-track3/179e384c-3df3-5902-b468-f503474d35e9/scratchpad
R=/home/user/v2d-track3
tag=$1; root=$2; md=$3; shift 3
EPS=${@:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
mkdir -p $S/runs/$tag; cd $S
for e in $EPS; do
  [ -s runs/$tag/ep$e.json ] && continue
  nice -n 5 venv/bin/python -I $R/pipeline/score_registered.py $e $root/ep$e/poses_world_vo.npz --meshes $md --t3 t3 \
    --kit kit/v2d_submission_kit --out runs/$tag/ep$e.json --per_frame runs/$tag/ep${e}_pf.npz > runs/$tag/ep$e.log 2>&1 && echo "OK $tag ep$e" || echo "FAIL $tag ep$e"
done
