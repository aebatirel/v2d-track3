#!/bin/bash
# One public episode: download its depth cache into an own new dir, audit (python -I), delete the cache.
set -u
e=$1
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/daudit
REPO=/home/user/v2d-track3
OUT=$REPO/docs/research/work/depth-audit-20261030/audit/public/ep$e
I=$S/refine/in/ep$e
DL=$W/dl_depth_pub_ep$e
LOG=$W/work/logs/pub_ep$e.log
mkdir -p $W/work/logs
cd $W/scripts
echo "[$(date -u +%FT%TZ)] ep$e start" >> $LOG
rm -rf $DL; mkdir -p $DL
python3 -I $W/scripts/dl.py $DL cache/depth/public/ep$e/depths_fs0.5.npy >> $LOG 2>&1 || { echo "ep$e download FAILED" >> $LOG; exit 1; }
OMP_NUM_THREADS=2 $S/map/scoring/venv/bin/python -I $REPO/pipeline/depth_audit.py --poses $I/poses.npz \
  --depth $DL/cache/depth/public/ep$e/depths_fs0.5.npy --hands $I/hands_refined.npz --meshes $REPO/meshes/library_v3 \
  --out $OUT --pylib $W/pylib --selftest 0 --force >> $LOG 2>&1
rc=$?
rm -rf $DL
echo "[$(date -u +%FT%TZ)] ep$e done rc=$rc" >> $LOG
exit $rc
