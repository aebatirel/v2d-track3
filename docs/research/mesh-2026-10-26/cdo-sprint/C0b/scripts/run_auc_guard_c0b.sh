#!/bin/bash
# C0b AUC guard (PREREG C0b section 7): a copy of C0's scripts/run_auc_guard.sh that changes only the mesh dirs
# (cdo_c0b/single/<o>, cdo_c0b/c0b), the output dir (cdo_c0b/runs) and the object list (+ beige_cup, twin 11).
# C0's ground-truth staging (stage0: parquets incl. mocap, public scans) and its base runs are reused; the base reuse
# is checked by check_base_c0b.py before this runs. CPU, $0. Run ONLY after the picks are committed and pushed.
# Each run is executed once; a run whose JSON already exists is skipped (a crash may be re-run unchanged).
# Usage: bash run_auc_guard_c0b.sh [single|joint|all]   (default all)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
D0=$S/cdo_c0                    # C0: tracks, t3 (staged GT for scoring), base mesh dir, base runs
D=$S/cdo_c0b
T3=$D0/t3
OUT=$D/runs
TWINS="0 2 11 12 13 21 22 26 27 31 41 42 43 44 45"
declare -A OTW=([white_pot]="0 2 26 27 41 42 43 44 45" [white_pot_lid]="0 2" [plastic_dish_rack]="12 13 26 27 31"
                [blue_cup]="11 12 13 21 22" [beige_cup]="11")
OBJS=${C0B_OBJS:-"white_pot white_pot_lid plastic_dish_rack blue_cup beige_cup"}
what=${1:-all}
mkdir -p $OUT

one() {   # cfg_dir ep
  local cfg=$1 e=$2 tag=${1//\//_}
  mkdir -p $OUT/$tag
  [ -s $OUT/$tag/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $D0/tracks/ep$e/poses_world_vo.npz --meshes $D/$cfg \
      --t3 $T3 --kit $KIT --out $OUT/$tag/ep$e.json ) > $OUT/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e (see $OUT/$tag/ep$e.log)"
}

if [ "$what" = single ] || [ "$what" = all ]; then
  ( for o in white_pot blue_cup; do case " $OBJS " in *" $o "*) for e in ${OTW[$o]}; do one single/$o $e; done;; esac; done ) &
  ( for o in plastic_dish_rack white_pot_lid beige_cup; do case " $OBJS " in *" $o "*) for e in ${OTW[$o]}; do one single/$o $e; done;; esac; done ) &
  wait
  echo "SINGLE done: $(ls $OUT/single_*/ep*.json 2>/dev/null | wc -l) JSONs"
fi
if [ "$what" = joint ] || [ "$what" = all ]; then
  ( for e in 0 2 11 12 13 21 22; do one c0b $e; done ) &
  ( for e in 26 27 31 41 42 43 44 45; do one c0b $e; done ) &
  wait
  echo "JOINT done: $(ls $OUT/c0b/ep*.json 2>/dev/null | wc -l) JSONs"
fi
