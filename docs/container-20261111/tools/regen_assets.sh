#!/bin/bash
# Regenerate one box's /content/assets the way ops/jobs/pack_eval.sh (or ev10_nj.sh) did on that box:
#   regen_assets.sh <commit> <out_dir> [piece dirs ...]   (piece dirs relative to the repo, merged first-wins per object)
# make_assets.py and the mesh library (meshes/library_v3) are taken from <commit>; python = avenv (trimesh 5.1.1,
# numpy 2.5.4, scipy 1.18.1: the box /venv/main versions of env snapshot pt2.11-cu130-py313-20261020).
set -euo pipefail
S=/tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad
C=$1; OUT=$2; shift 2
W=$S/container/regen/src_${C:0:7}; rm -rf $W; mkdir -p $W
git -C /home/user/v2d-track3 archive $C pipeline/make_assets.py meshes | tar -x -C $W
ARGS=()
if [ $# -gt 1 ]; then
  PM=$W/pieces_merged; mkdir -p $PM
  for d in "$@"; do for o in $W/$d/*/; do [ -n "$(ls $o/piece_*.obj 2>/dev/null)" ] && [ ! -e $PM/$(basename $o) ] && ln -s $(readlink -f $o) $PM/$(basename $o); done; done
  ARGS=(--pieces $PM)
elif [ $# -eq 1 ]; then
  ARGS=(--pieces $W/$1)
fi
rm -rf $OUT; mkdir -p $(dirname $OUT)
(cd $W && $S/container/avenv/bin/python -I pipeline/make_assets.py meshes/library_v3 $OUT ${ARGS[@]+"${ARGS[@]}"})
