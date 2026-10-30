#!/bin/bash
# GROUND-TRUTH SIDE (calibration labels). Run only after every public audit exists.
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/daudit; SC=$S/map/scoring; REPO=/home/user/v2d-track3
mkdir -p $W/work/gt/lab $W/work/gt/lab_s2 $W/work/gt/logs
for e in 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45; do
  echo "$SC/venv/bin/python -I $REPO/pipeline/score_registered.py $e $S/refine/in/ep$e/poses_world_vo.npz --t3 $SC/t3 --kit $SC/kit/v2d_submission_kit --meshes $REPO/meshes/library_v3 --out $W/work/gt/lab/ep${e}_lib.json --per_frame $W/work/gt/lab/ep${e}_pf.npz > $W/work/gt/logs/lab_ep$e.log 2>&1"
  echo "$SC/venv/bin/python -I $REPO/pipeline/score_registered.py $e $W/work/s2/ep$e/poses_world_vo.npz --t3 $SC/t3 --kit $SC/kit/v2d_submission_kit --meshes $REPO/meshes/library_v3 --out $W/work/gt/lab_s2/ep${e}_lib.json --per_frame $W/work/gt/lab_s2/ep${e}_pf.npz > $W/work/gt/logs/lab_s2_ep$e.log 2>&1"
done > $W/work/gt/jobs.txt
cd $W/work/gt && xargs -P 4 -I{} bash -c {} < $W/work/gt/jobs.txt
