#!/bin/bash
# C2/P AUC guard (PREREG.md section 6): a copy of C0's scripts/run_auc_guard.sh that changes only the mesh dir
# (cdo_c2/P/auc/single/water_pitcher = C0's base dir, library_v3, with water_pitcher.glb replaced by the pick, placed as
# built), the output dir (cdo_c2/P/auc/runs) and the object list (water_pitcher, twins 21 22). C0's ground-truth staging
# (stage0: parquets incl. mocap, public scans) and its base runs are reused only if check_base_p.py passes (it copies
# them to cdo_c2/P/auc/runs/base); otherwise the base runs are run here unchanged. CPU, $0.
# Run ONLY after PREREG.md and the pick are committed and pushed.
# Each run is executed once; a run whose JSON already exists is skipped (a crash may be re-run unchanged).
# Usage: bash run_auc_guard_p.sh [base|single|all]   (default all)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
D0=$S/cdo_c0                    # C0: tracks, t3 (staged GT for scoring), base mesh dir, base runs
D=$S/cdo_c2/P/auc
T3=$D0/t3
OUT=$D/runs
TW="21 22"
what=${1:-all}
mkdir -p $OUT

one() {   # cfg_dir(relative to D, or abs) ep
  local cfg=$1 e=$2 tag=${1//\//_}
  case $cfg in /*) mdir=$cfg; tag=base;; *) mdir=$D/$cfg;; esac
  mkdir -p $OUT/$tag
  [ -s $OUT/$tag/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $D0/tracks/ep$e/poses_world_vo.npz --meshes $mdir \
      --t3 $T3 --kit $KIT --out $OUT/$tag/ep$e.json ) > $OUT/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e (see $OUT/$tag/ep$e.log)"
}

if [ "$what" = base ] || [ "$what" = all ]; then
  for e in $TW; do one $D0/base $e; done        # skipped when check_base_p.py copied C0's base JSONs
fi
if [ "$what" = single ] || [ "$what" = all ]; then
  ( one single/water_pitcher 21 ) &
  ( one single/water_pitcher 22 ) &
  wait
  echo "SINGLE done: $(ls $OUT/single_water_pitcher/ep*.json 2>/dev/null | wc -l) JSONs"
fi
