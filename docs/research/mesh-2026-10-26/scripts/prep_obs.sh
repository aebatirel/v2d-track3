#!/bin/bash
# Observed object-frame points for the primitive-fit round (2026-10-27), no GT:
# per public episode: latest-detection tracks (store run 20261025-sweep-a894083, results/sweep/base/ep<N>/poses.npz),
# MediaPipe hands (G1 refs if stored), FoundationStereo depth cache -> obs_points.py for every listed object -> the
# depth cache is deleted to save disk. Usage: prep_obs.sh SCRATCH "EP:obj,obj EP:obj ..." (writes SCRATCH/obs_all)
S=$1; shift; R=$(cd "$(dirname "$0")/../../../.." && pwd); L=$R/meshes/library_v3
ST=https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main
cd $S
for spec in $1; do
  e=${spec%%:*}; objs=${spec#*:}
  d=data/sweep/ep$e; mkdir -p $d data/depth/ep$e
  curl -sSLf -o $d/poses.npz $ST/runs/20261025-sweep-a894083/results/sweep/base/ep$e/poses.npz || { echo "ep$e: no sweep poses"; continue; }
  H=""; curl -sSLf -o $d/hands.npz $ST/runs/20261025-g1-022fece/refs/perc2m/ep$e/hands.npz && H="--hands $d/hands.npz"
  [ -s data/depth/ep$e/depths_fs0.5.npy ] || curl -sSLf -o data/depth/ep$e/depths_fs0.5.npy $ST/cache/depth/public/ep$e/depths_fs0.5.npy || { echo "ep$e: no depth"; continue; }
  all=$(python3 -c "import numpy as np; print(' '.join(k[6:] for k in np.load('$d/poses.npz').files if k.startswith('cam_T_')))")
  for o in ${objs//,/ }; do
    oth=$(for x in $all; do [ $x != $o ] && printf "%s=%s/%s.glb," $x $L $x; done); oth=${oth%,}
    venv/bin/python -W ignore $R/docs/research/mesh-2026-10-26/scripts/obs_points.py --poses $d/poses.npz \
      --depth data/depth/ep$e/depths_fs0.5.npy $H --calib data/calib.json --obj $o --roi $L/$o.glb \
      ${oth:+--others $oth} --out obs_all/ep${e}_$o.npz > obs_all/ep${e}_$o.log 2>&1 && echo "ep$e $o $(tail -1 obs_all/ep${e}_$o.log)" || echo "ep$e $o FAIL"
  done
  rm -f data/depth/ep$e/depths_fs0.5.npy
done
echo PREP-DONE
