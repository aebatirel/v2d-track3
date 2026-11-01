#!/bin/bash
# C2/P: the C0b observed points (C0b PREREG 3.4, commit 8174998; code 00e8584) of the pitcher on one public episode,
# built exactly as the C0b box builds them (C0b/jobs/c0b_obs.sh, c0b_tasks.py stages obsA/obsB):
#   pass A: water_pitcher and blue_cup, --roi_cube 0.30, no co-object carving;
#   pass B: water_pitcher with --others_pts blue_cup=<pass-A blue cup> (20,000 random pass-A points, seed 0).
# Inputs: sweep base track (store run 20261025-sweep-a894083), G1 MediaPipe hands (20261025-g1-022fece),
# FoundationStereo depth (store cache/depth/public), calib md5 56c32942. No scan, mocap, parquet pose, library mesh.
# Usage: obs_c0b.sh EP
set -u
E=$1
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
J=$R/docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs
OP=$R/docs/research/mesh-2026-10-26/scripts/obs_points.py
W=$S/cdo_c2/P
PY=$S/venv/bin/python
D=$W/depth/cache/depth/public/ep$E/depths_fs0.5.npy
mkdir -p $W/pts/A $W/pts/B $W/guard $W/logs
run() {  # obj others dst
  local t=$(date +%s)
  nice -n 5 bash $J/c0b_obs.sh $PY $J/c0b_prep.py $OP $S/data/sweep/ep$E/poses.npz $D $S/data/sweep/ep$E/hands.npz \
    $S/data/calib.json $1 $2 $3 $W/guard/$(basename $3 .npz)_$(basename $(dirname $3)).jsonl \
    > $W/logs/obs_$(basename $(dirname $3))_ep${E}_$1.log 2>&1 && echo "OK $1 $(basename $(dirname $3)) ep$E $(( $(date +%s) - t ))s" \
    || echo "FAIL $1 $(basename $(dirname $3)) ep$E"
}
run water_pitcher - $W/pts/A/ep${E}_water_pitcher.npz &
run blue_cup - $W/pts/A/ep${E}_blue_cup.npz &
wait
run water_pitcher blue_cup=$W/pts/A/ep${E}_blue_cup.npz $W/pts/B/ep${E}_water_pitcher.npz
