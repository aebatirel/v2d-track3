#!/bin/bash
# posefix runner (PREREG.md in this folder). CPU, $0.
#   transform  : variants A (gated), B, C, D (report only) on the 20 public tracks -> SP/out/<V>/ep<e>/poses_world_vo.npz,
#                then sha256 of every written track -> SP/out/<V>/tracks_sha256.txt (BEFORE any scoring step reads it)
#   stage0     : stage the scoring inputs (public parquets incl. mocap, public scans) under SP/t3; only the scorer
#                and pf_diag.py read them
#   score      : score_registered.py on before (original tracks) and A, B, C, D; each run once; existing JSONs skipped
#   diag       : pf_diag.py per episode for A (and B, C, D report only)
# Usage: bash run_posefix.sh transform|stage0|score|diag
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
SP=$S/posefix
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
SC=$R/docs/research/mesh-2026-10-26/posefix/scripts
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
what=${1:-}

if [ "$what" = transform ]; then
  for V in A B C D; do
    ( mkdir -p $SP/out/$V
      nice -n 5 $PY $SC/pf_transform.py $V $SP/tracks $SP/out/$V $EPS > $SP/out/$V/transform.log 2>&1 \
        && echo "$(date -u +%FT%TZ) transform $V OK" || echo "$(date -u +%FT%TZ) transform $V FAIL"
      ( cd $SP/out/$V && sha256sum ep*/poses_world_vo.npz ep*/posefix.json > tracks_sha256.txt ) ) &
  done
  wait
fi

if [ "$what" = stage0 ]; then
  mkdir -p $SP/t3 $SP/hf
  for e in $EPS; do
    f=track_3/public/data/chunk-000/episode_$(printf %06d $e).parquet
    src=""
    for d in $S/cdo_c0/t3 $S/cdo_c1/t3/auc/t3; do [ -e $d/ep$e.parquet ] && { src=$(readlink -f $d/ep$e.parquet); break; }; done
    if [ -z "$src" ]; then
      ( cd $SP && $S/venv/bin/hf download nvidia/video_to_data_challenge --repo-type dataset --include "$f" \
          --local-dir $SP/hf > /dev/null ) || echo "STAGE0 FAIL ep$e"
      src=$SP/hf/$f
    fi
    ln -sfn $src $SP/t3/ep$e.parquet
  done
  ln -sfn $(readlink -f $S/cdo_c0/t3/mesh) $SP/t3/mesh
  sha256sum $SP/t3/ep*.parquet $SP/t3/mesh/*/*.glb > $SP/t3_inputs_sha256.txt
  echo "STAGE0 done: $(ls $SP/t3/*.parquet | wc -l) parquets"
fi

one() {   # tag tracks_root ep
  local tag=$1 root=$2 e=$3
  mkdir -p $SP/runs/$tag
  [ -s $SP/runs/$tag/ep$e.json ] && return 0
  ( cd $SP && nice -n 5 $PY $R/pipeline/score_registered.py $e $root/ep$e/poses_world_vo.npz --meshes $SP/mesh9a \
      --t3 $SP/t3 --kit $KIT --out $SP/runs/$tag/ep$e.json ) > $SP/runs/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e"
}

if [ "$what" = score ]; then
  ( for e in $EPS; do one before $SP/tracks $e; one A $SP/out/A $e; done ) &
  ( for e in $EPS; do one B $SP/out/B $e; one C $SP/out/C $e; one D $SP/out/D $e; done ) &
  wait
  echo "SCORE done: $(ls $SP/runs/*/ep*.json 2>/dev/null | wc -l) of 100 JSONs"
fi

if [ "$what" = diag ]; then
  for V in A B C D; do
    mkdir -p $SP/diag/$V
    for e in $EPS; do
      [ -s $SP/diag/$V/ep$e.json ] && continue
      nice -n 5 $PY $SC/pf_diag.py $e $SP/tracks/ep$e/poses_world_vo.npz $SP/out/$V/ep$e/poses_world_vo.npz \
        $SP/out/$V/ep$e/posefix.json --t3 $SP/t3 --kit $KIT --meshes $SP/mesh9a --out $SP/diag/$V/ep$e.json \
        --scorer_before $SP/runs/before/ep$e.json --scorer_after $SP/runs/$V/ep$e.json > $SP/diag/$V/ep$e.log 2>&1 \
        && echo "$(date -u +%FT%TZ) diag $V ep$e OK" || echo "$(date -u +%FT%TZ) diag $V ep$e FAIL"
    done
  done
fi
