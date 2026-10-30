#!/bin/bash
# Score a refine arm against public mocap (SCORER SIDE: reads ground truth; run only after pipeline/refine.py has written
# ARM/ep<N>/). Same command as the 2026-10-29 baseline (scratchpad refine/baseline/jobs.txt): pipeline/score_registered.py
# registered with our meshes (lib) and with the public scan (scan), 4 jobs in parallel.
# Usage: W=<scoring dir with venv, t3, kit> [LIB=meshes/library_v3] [JOBS=4] score_arm.sh ARM "0 2 11 ..."
#   -> ARM/score/ep<N>_{lib,scan}.json, ARM/score/ep<N>_{lib,scan}_pf.npz, ARM/score/logs/, ARM/score/jobs.txt
set -u
ARM=$(readlink -f "$1"); EPS=${2:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
W=${W:?W = scoring dir (venv, t3, kit)}; REPO=${REPO:-$(cd "$(dirname "$0")/../../../.." && pwd)}
LIB=${LIB:-$REPO/meshes/library_v3}; JOBS=${JOBS:-4}
mkdir -p $ARM/score/logs; : > $ARM/score/jobs.txt
for e in $EPS; do
  [ -s $ARM/ep$e/poses_world_vo.npz ] || { echo "missing $ARM/ep$e/poses_world_vo.npz" >&2; continue; }
  [ -e $W/t3/ep$e.parquet ] || { echo "missing $W/t3/ep$e.parquet" >&2; continue; }
  B="$W/venv/bin/python -I $REPO/pipeline/score_registered.py $e $ARM/ep$e/poses_world_vo.npz --t3 $W/t3 --kit $W/kit/v2d_submission_kit"
  echo "$B --meshes $LIB --out $ARM/score/ep${e}_lib.json --per_frame $ARM/score/ep${e}_lib_pf.npz > $ARM/score/logs/ep${e}_lib.log 2>&1" >> $ARM/score/jobs.txt
  echo "$B --out $ARM/score/ep${e}_scan.json --per_frame $ARM/score/ep${e}_scan_pf.npz > $ARM/score/logs/ep${e}_scan.log 2>&1" >> $ARM/score/jobs.txt
done
cd /tmp && xargs -P $JOBS -I{} bash -c '{}' < $ARM/score/jobs.txt
echo "scored $(ls $ARM/score/*_lib.json 2>/dev/null | wc -l) lib + $(ls $ARM/score/*_scan.json 2>/dev/null | wc -l) scan files in $ARM/score"
