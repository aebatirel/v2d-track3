#!/bin/bash
# same command as run_posefix.sh diag, variant A only (run while B/C/D are still being scored)
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad; SP=$S/posefix; R=/home/user/v2d-track3
SC=$R/docs/research/mesh-2026-10-26/posefix/scripts; KIT=$S/kit/v2d_submission_kit; V=${1:-A}
mkdir -p $SP/diag/$V
for e in 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45; do
  [ -s $SP/diag/$V/ep$e.json ] && continue
  nice -n 5 $S/venv/bin/python -I $SC/pf_diag.py $e $SP/tracks/ep$e/poses_world_vo.npz $SP/out/$V/ep$e/poses_world_vo.npz \
    $SP/out/$V/ep$e/posefix.json --t3 $SP/t3 --kit $KIT --meshes $SP/mesh9a --out $SP/diag/$V/ep$e.json \
    --scorer_before $SP/runs/before/ep$e.json --scorer_after $SP/runs/$V/ep$e.json > $SP/diag/$V/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) diag $V ep$e OK" || echo "$(date -u +%FT%TZ) diag $V ep$e FAIL"
done
