#!/bin/bash
# POST-HOC DIAGNOSTIC (not in the C0 PREREG): registered AUC of C0a (focused-pascal's C0 rigidly ICP-aligned onto
# library_v3, meshes/c0a_20261031 at origin/claude/focused-pascal-2nz9s1 9c2d00e) as single-object swaps vs library_v3,
# on the same public twins, the same tracks, the same base runs and the same scorer call as the C0 guard
# (cdo-sprint/C0/scripts/run_auc_guard.sh). Only the mesh dir changes. Requested by focused-pascal for their MESH_RULE.
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"; KIT=$S/kit/v2d_submission_kit; D=$S/cdo_c0; T3=$D/t3; OUT=$D/runs_c0a
declare -A OTW=([white_pot]="0 2 26 27 41 42 43 44 45" [white_pot_lid]="0 2" [plastic_dish_rack]="12 13 26 27 31"
                [blue_cup]="11 12 13 21 22")
mkdir -p $OUT
for o in white_pot white_pot_lid plastic_dish_rack blue_cup; do
  d=$D/single_c0a/$o; mkdir -p $d; cp $D/base/*.glb $d/
  git -C $R show origin/claude/focused-pascal-2nz9s1:meshes/c0a_20261031/$o.glb > $d/$o.glb
done
sha256sum $D/single_c0a/*/*.glb > $OUT/mesh_sha256.txt
one() { local o=$1 e=$2 tag=single_c0a_$1; mkdir -p $OUT/$tag; [ -s $OUT/$tag/ep$e.json ] && return 0
  ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $D/tracks/ep$e/poses_world_vo.npz --meshes $D/single_c0a/$o \
      --t3 $T3 --kit $KIT --out $OUT/$tag/ep$e.json ) > $OUT/$tag/ep$e.log 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $tag ep$e" || echo "$(date -u +%FT%TZ) FAIL $tag ep$e"; }
( for o in white_pot white_pot_lid; do for e in ${OTW[$o]}; do one $o $e; done; done ) &
( for o in plastic_dish_rack blue_cup; do for e in ${OTW[$o]}; do one $o $e; done; done ) &
wait
echo "C0A RUNS done: $(ls $OUT/*/ep*.json 2>/dev/null | wc -l) of 21"
