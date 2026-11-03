#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/179e384c-3df3-5902-b468-f503474d35e9/scratchpad; cd $S
tag=$1; md=$2; e=$3; mkdir -p cv/$tag; [ -s cv/$tag/ep$e.json ] && exit 0
nice -n 5 venv/bin/python -I /home/user/v2d-track3/pipeline/score_registered.py $e tracksT/ep$e/poses_world_vo.npz --meshes $md --t3 t3 \
  --kit kit/v2d_submission_kit --out cv/$tag/ep$e.json --reg_seeds 10 > cv/$tag/ep$e.log 2>&1 && echo "OK $tag ep$e" || echo "FAIL $tag ep$e"
