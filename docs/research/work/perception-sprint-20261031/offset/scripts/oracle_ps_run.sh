#!/bin/bash
# ORACLE ARM (diagnostic only, README §2): S11 V1-V3 and the S2 baseline on the Phase-1 P_s tracks (scan templates,
# scan frames) with the public scans as --meshes. Builds poses.npz from P_o's world_T_cam. Never an eval input.
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/offset/oracle; R=$S/refine/in; PO=$S/leak/t1/in_Po; PS=$S/leak/p1/oracle_roots/Ps_scan; T3=$S/map/scoring/t3
PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
mkdir -p $W/scanlib
for d in $T3/mesh/*/; do n=$(basename $d); f=$d/$n.glb; [ -e $f ] || f=$d/${n}_visual.glb; ln -sfn $f $W/scanlib/$n.glb; done
for e in $EPS; do
  d=$W/in_Ps/ep$e; mkdir -p $d
  $PY -I -c "
import numpy as np, sys
W = np.load('$PO/ep$e/poses.npz')['world_T_cam']; V = np.load('$PS/ep$e/poses_world_vo.npz')
np.savez('$d/poses.npz', world_T_cam=W, **{f'cam_T_{n}': np.einsum('tij,tjk->tik', np.linalg.inv(W.astype(np.float64)), V[n].astype(np.float64)).astype(np.float32) for n in V.files})
"
  ln -sfn $R/ep$e/depth0.npy $d/depth0.npy; ln -sfn $(readlink -f $R/ep$e/hands_refined.npz) $d/hands_refined.npz
done
J=$W/jobs.txt; : > $J
for v in S2 V1 V2 V3; do
  mkdir -p $W/runs/Ps/$v/logs
  case $v in
    S2) st="--steps S2";;
    V1) st="--steps S11,S2 --s11_mode mf --s11_apply whole";;
    V2) st="--steps S11,S2 --s11_mode f0 --s11_apply whole";;
    V3) st="--steps S11,S2 --s11_mode f0 --s11_apply prefix";;
  esac
  for e in $EPS; do
    extra="--s11_det $R/ep$e/det_f0.npz"; [ $v = V1 ] && extra="$extra --s11_depth $S/offset/depth/ep$e/depth_grid.npz"
    echo "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 $PY -I $REPO/pipeline/refine.py --in $W/in_Ps/ep$e --out $W/runs/Ps/$v/ep$e --meshes $W/scanlib $st $extra --force > $W/runs/Ps/$v/logs/ep$e.log 2>&1 || echo FAIL Ps $v ep$e" >> $J
  done
done
(grep "/V1/" $J; grep -v "/V1/" $J) > $J.ordered
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J.ordered
grep -l "Traceback" $W/runs/*/*/logs/*.log || echo "no tracebacks"
