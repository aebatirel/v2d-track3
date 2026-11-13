#!/bin/bash
# Fetch stage-1b inputs for one public episode into $B/C/ep<N> and $DEP/ep<N>.npy (store, read-only).
# Control C: runs/20261102-ptrkA-7fbc3215 or -ptrkB-7fbc3215 results/ptrk/C/ep<N> (ep23: ptrkD-95cecd7 Cr);
# SAM2 masks: runs/20261102-ptrkD-95cecd7/results/ptrk/MRr/ep<N>/vos_masks.npz; depth: cache/depth/public/ep<N>.
# Usage: B=<work dir> DEP=<depth dir> bash fetch_ep.sh N
set -u
N=$1; U=https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main; A=(-sS -L -f -H "Authorization: Bearer dummy")
mkdir -p $B/C/ep$N $DEP
src=""
if [ $N = 23 ]; then src=runs/20261102-ptrkD-95cecd7/results/ptrk/Cr/ep23; else
  for r in 20261102-ptrkA-7fbc3215 20261102-ptrkB-7fbc3215; do
    curl "${A[@]}" -o $B/C/ep$N/poses.npz $U/runs/$r/results/ptrk/C/ep$N/poses.npz 2> /dev/null && { src=runs/$r/results/ptrk/C/ep$N; break; }
  done
fi
[ -n "$src" ] || { echo "ep$N: no control C found"; exit 1; }
for f in poses.npz poses_world_vo.npz det_f0.npz; do curl "${A[@]}" -o $B/C/ep$N/$f $U/$src/$f || { echo "ep$N: $f missing"; exit 1; }; done
curl "${A[@]}" -o $B/C/ep$N/vos_masks.npz $U/runs/20261102-ptrkD-95cecd7/results/ptrk/MRr/ep$N/vos_masks.npz || { echo "ep$N: vos missing"; exit 1; }
echo "$src" > $B/C/ep$N/SOURCE
[ -s $DEP/ep$N.npy ] || curl "${A[@]}" -o $DEP/ep$N.npy $U/cache/depth/public/ep$N/depths_fs0.5.npy || { echo "ep$N: depth missing"; exit 1; }
echo "ep$N inputs OK ($src)"
