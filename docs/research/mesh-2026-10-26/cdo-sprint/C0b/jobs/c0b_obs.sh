#!/bin/bash
# One C0b observed-point file (PREREG C0b 3.4): obs_points.py --roi_cube 0.30 [+ --others_pts], then the cube-face
# guard (c0b_prep.py cubeguard); if more than 0.1 % of the kept points lie within 8 mm of a cube face the file is
# rebuilt ONCE at half-side 0.45 m and the rebuilt file is used (its guard is recorded, not acted on).
# Usage: c0b_obs.sh PY PREP OBS_POINTS POSES DEPTH HANDS(or -) CALIB OBJ OTHERS_PTS(or -) OUT GUARD.jsonl
set -u
PY=$1 PREP=$2 OP=$3 POSES=$4 DEPTH=$5 HANDS=$6 CALIB=$7 OBJ=$8 OTH=$9 OUT=${10} GJ=${11}
args=(--poses $POSES --depth $DEPTH --calib $CALIB --obj $OBJ --out $OUT)
[ "$HANDS" != - ] && args+=(--hands $HANDS)
[ "$OTH" != - ] && args+=(--others_pts $OTH)
[ -n "${C0B_STRIDE:-}" ] && args+=(--stride $C0B_STRIDE)                 # dry run only
$PY -I -W ignore $OP "${args[@]}" --roi_cube 0.30 || exit 1
$PY -I $PREP cubeguard $OUT 0.30 >> $GJ
rc=$?
if [ $rc = 3 ]; then
  echo "cube guard: rebuild $OUT at 0.45 m"
  $PY -I -W ignore $OP "${args[@]}" --roi_cube 0.45 || exit 1
  $PY -I $PREP cubeguard $OUT 0.45 >> $GJ
  [ $? -le 3 ] || exit 1
elif [ $rc != 0 ]; then
  exit 1
fi
exit 0
