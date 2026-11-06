#!/bin/bash
# C2/R AUC guard (PREREG C2/R-rack section 7): a copy of C0's scripts/run_auc_guard.sh that changes only the mesh dir
# (cdo_c2r/single/plastic_dish_rack, built by check_base_c2r.py), the output dir (cdo_c2r/runs) and the object list
# (rack only, twins 12 13 26 27 31). C0's ground-truth staging (stage0) and, if check_base_c2r.py allows, its base
# runs are reused; otherwise the 5 base runs are run here unchanged. CPU, $0. Run ONLY after the pick is committed
# and pushed. Each run is executed once; a run whose JSON exists is skipped (a crash may be re-run unchanged).
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
D0=$S/cdo_c0
D=$S/cdo_c2r
T3=$D0/t3
OUT=$D/runs
EPS="12 13 26 27 31"
mkdir -p $OUT
one() {   # cfg_dir ep (cfg base -> C0's base dir)
  local cfg=$1 e=$2 tag=${1//\//_} md
  [ $1 = base ] && md=$D0/base || md=$D/$1
  mkdir -p $OUT/$tag
  [ -s $OUT/$tag/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $D0/tracks/ep$e/poses_world_vo.npz --meshes $md \
      --t3 $T3 --kit $KIT --out $OUT/$tag/ep$e.json ) > $OUT/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e (see $OUT/$tag/ep$e.log)"
}
( for e in 12 13 26; do one single/plastic_dish_rack $e; one base $e; done ) &
( for e in 27 31; do one single/plastic_dish_rack $e; one base $e; done ) &
wait
echo "RUNS done: single $(ls $OUT/single_plastic_dish_rack/ep*.json 2>/dev/null | wc -l)/5, base $(ls $OUT/base/ep*.json 2>/dev/null | wc -l)/5"
