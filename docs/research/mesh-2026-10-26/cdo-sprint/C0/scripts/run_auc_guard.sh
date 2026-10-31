#!/bin/bash
# C0 AUC guard (PREREG.md, CD-O sprint stage 2). CPU, $0. Run ONLY after PREREG.md is committed and pushed.
# Stage 0 stages the ground truth (public parquets incl. mocap) for scoring; nothing else here reads it.
# Each run is executed once. A run whose JSON already exists is skipped (so a crashed or killed batch is resumed
# unchanged); no run is repeated with changed settings.
# Usage: bash run_auc_guard.sh [stage0|runs|all]   (default all)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
D=$S/cdo_c0
T3=$D/t3
OUT=$D/runs
TWINS="0 2 11 12 13 21 22 26 27 31 41 42 43 44 45"
declare -A OTW=([white_pot]="0 2 26 27 41 42 43 44 45" [white_pot_lid]="0 2" [plastic_dish_rack]="12 13 26 27 31"
                [blue_cup]="11 12 13 21 22")
what=${1:-all}

if [ "$what" = stage0 ] || [ "$what" = all ]; then
  mkdir -p $D/hf $T3/mesh $OUT
  for e in $TWINS; do
    f=track_3/public/data/chunk-000/episode_$(printf %06d $e).parquet
    [ -s $D/hf/$f ] || ( cd $D && $S/venv/bin/hf download nvidia/video_to_data_challenge --repo-type dataset \
                          --include "$f" --local-dir $D/hf > /dev/null ) || echo "STAGE0 FAIL ep$e"
    ln -sfn $D/hf/$f $T3/ep$e.parquet
  done
  for f in $S/data/scan/*.glb; do                 # the same public scans the [D] CD-O numbers used
    b=$(basename $f .glb); n=${b%_visual}; mkdir -p $T3/mesh/$n; ln -sfn $f $T3/mesh/$n/$b.glb
  done
  sha256sum $T3/ep*.parquet $T3/mesh/*/*.glb > $OUT/inputs_sha256.txt 2>&1
  echo "STAGE0 done: $(ls $T3/*.parquet | wc -l) parquets, $(ls $T3/mesh | wc -l) scans"
fi

one() {   # cfg_dir ep
  local cfg=$1 e=$2 tag=${1//\//_}
  mkdir -p $OUT/$tag
  [ -s $OUT/$tag/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $D/tracks/ep$e/poses_world_vo.npz --meshes $D/$cfg \
      --t3 $T3 --kit $KIT --out $OUT/$tag/ep$e.json ) > $OUT/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e (see $OUT/$tag/ep$e.log)"
}

if [ "$what" = runs ] || [ "$what" = all ]; then
  ( for e in $TWINS; do one base $e; one c0 $e; done ) &                                   # stream 1
  ( for o in white_pot white_pot_lid plastic_dish_rack blue_cup; do for e in ${OTW[$o]}; do one single/$o $e; done
    done ) &                                                                              # stream 2
  wait
  echo "RUNS done: $(ls $OUT/*/ep*.json 2>/dev/null | wc -l) of 51 JSONs"
fi
