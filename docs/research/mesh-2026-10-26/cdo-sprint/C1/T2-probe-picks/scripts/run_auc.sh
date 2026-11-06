#!/bin/bash
# C1/T2 AUC guard (PREREG.md s6). CPU, $0. Run ONLY after PREREG.md is committed and pushed, and only for objects that
# are a WIN on at least one eval pair (score_t2.py gates). Stage 0 stages the ground truth (public parquets incl.
# mocap, public scans) for scoring; nothing else here reads it. Each run is executed once; a run whose JSON exists is
# skipped (a crashed run may be re-run unchanged). C0's base runs are reused where auc_prep.json says reusable.
# Usage: bash run_auc.sh stage0 | bash run_auc.sh runs OBJ [OBJ ...]
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
D=$S/cdo_c1/t2/auc
T3=$D/t3
OUT=$D/runs
declare -A OTW=([water_pitcher]="21 22" [mini_dust_pan]="18 39 40" [beige_cup]="11")
what=$1; shift

if [ "$what" = stage0 ]; then
  mkdir -p $D/hf $T3/mesh $OUT
  for e in 11 21 22; do                           # C0 already downloaded these (same HF dataset file)
    ln -sfn $S/cdo_c0/hf/track_3/public/data/chunk-000/episode_$(printf %06d $e).parquet $T3/ep$e.parquet
  done
  for e in 18 39 40; do
    f=track_3/public/data/chunk-000/episode_$(printf %06d $e).parquet
    [ -s $D/hf/$f ] || ( cd $D && $S/venv/bin/hf download nvidia/video_to_data_challenge --repo-type dataset \
                          --include "$f" --local-dir $D/hf > /dev/null ) || echo "STAGE0 FAIL ep$e"
    ln -sfn $D/hf/$f $T3/ep$e.parquet
  done
  for f in $S/data/scan/*.glb; do                 # the same public scans as C0 / T1 and the [D] CD-O numbers
    b=$(basename $f .glb); n=${b%_visual}; mkdir -p $T3/mesh/$n; ln -sfn $f $T3/mesh/$n/$b.glb
  done
  sha256sum $T3/ep*.parquet $T3/mesh/*/*.glb > $OUT/inputs_sha256.txt 2>&1
  ( cd $D && sha256sum base/*.glb single_*/*.glb ) >> $OUT/inputs_sha256.txt
  echo "STAGE0 done: $(ls $T3/*.parquet | wc -l) parquets, $(ls $T3/mesh | wc -l) scans"
fi

one() {   # cfg ep track
  local cfg=$1 e=$2 trk=$3
  mkdir -p $OUT/$cfg
  [ -s $OUT/$cfg/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $trk --meshes $D/$cfg \
      --t3 $T3 --kit $KIT --out $OUT/$cfg/ep$e.json ) > $OUT/$cfg/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $cfg ep$e" || echo "$(date -u +%FT%TZ) FAIL $cfg ep$e (see $OUT/$cfg/ep$e.log)"
}

if [ "$what" = runs ]; then
  for o in "$@"; do
    for e in ${OTW[$o]}; do
      trk=$($S/venv/bin/python -I -c "import json,sys; print(json.load(open(sys.argv[1]))['tracks'][sys.argv[2]]['path'])" $D/auc_prep.json $e)
      reuse=$($S/venv/bin/python -I -c "import json,sys; print(int(json.load(open(sys.argv[1]))['c0_reuse'][sys.argv[2]]['reusable']))" $D/auc_prep.json $e)
      [ "$reuse" = 1 ] || one base $e $trk
      one single_$o $e $trk
    done
  done
  echo "RUNS done"
fi
