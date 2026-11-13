#!/bin/bash
# T3 AUC guard (PREREG.md section 6). CPU, $0. Run ONLY for CD-O-gate WINs, after PREREG.md is committed and pushed.
# Same rule and the same kit call as C0 (cdo-sprint/C0/scripts/run_auc_guard.sh): pipeline/score_registered.py on our
# perception tracks (sweep poses.npz -> poses_world_vo.npz, C0 recipe W_C @ cam_T_obj) with
#   base   = library_v3 for all 10 public objects (byte-identical to C0's cdo_c0/base; C0's base JSONs are reused for
#            twins C0 ran, after checking the base dir sha256s match, see PREREG),
#   single = base + this object's fitted mesh (fit.glb; already in our object frame = the library frame).
# Each run once; an existing JSON is skipped (resume), never re-run with other settings.
# Usage: bash run_auc.sh OBJ FITTED.glb
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
PY="$S/venv/bin/python -I"
KIT=$S/kit/v2d_submission_kit
C0=$S/cdo_c0
D=$S/cdo_c1/t3/auc
O=$1; FIT=$2
declare -A OTW=([white_pot]="0 2 26 27 41 42 43 44 45" [white_pot_lid]="0 2" [plastic_dish_rack]="12 13 26 27 31"
                [blue_cup]="11 12 13 21 22" [beige_cup]="11" [water_pitcher]="21 22" [mini_sweeper]="18 31"
                [mini_dust_pan]="18 39 40" [wooden_piece_1]="23 24" [wooden_piece_2]="23 24")
mkdir -p $D/single_$O $D/runs/base $D/runs/single_$O $D/tracks $D/t3/mesh
cp $C0/base/*.glb $D/single_$O/ && cp $FIT $D/single_$O/$O.glb
for f in $S/data/scan/*.glb; do                   # the same public scans as C0 (scoring only)
  b=$(basename $f .glb); n=${b%_visual}; mkdir -p $D/t3/mesh/$n; ln -sfn $f $D/t3/mesh/$n/$b.glb
done
for e in ${OTW[$O]}; do
  # parquet (scoring only) and scans: C0's staged copies when present, else download the public parquet
  p=$C0/t3/ep$e.parquet
  if [ ! -e $p ]; then
    f=track_3/public/data/chunk-000/episode_$(printf %06d $e).parquet
    [ -s $D/hf/$f ] || ( cd $D && $S/venv/bin/hf download nvidia/video_to_data_challenge --repo-type dataset \
                          --include "$f" --local-dir $D/hf > /dev/null ) || echo "STAGE FAIL ep$e"
    p=$D/hf/$f
  fi
  ln -sfn $p $D/t3/ep$e.parquet
  # tracks: C0's when present, else the same recipe
  if [ -s $C0/tracks/ep$e/poses_world_vo.npz ]; then trk=$C0/tracks/ep$e/poses_world_vo.npz
  else
    mkdir -p $D/tracks/ep$e; trk=$D/tracks/ep$e/poses_world_vo.npz
    [ -s $trk ] || $PY -c "
import numpy as np
P = np.load('$S/data/sweep/ep$e/poses.npz', allow_pickle=False); W = np.asarray(P['world_T_cam'], np.float64)
np.savez('$trk', **{k[6:]: np.einsum('tij,tjk->tik', W, np.asarray(P[k], np.float64)) for k in P.files if k.startswith('cam_T_')})"
  fi
  for cfg in base single_$O; do
    out=$D/runs/$cfg/ep$e.json
    [ -s $out ] && continue
    if [ $cfg = base ] && [ -s $C0/runs/base/ep$e.json ]; then cp $C0/runs/base/ep$e.json $out; echo "reuse C0 base ep$e"; continue; fi
    mdir=$C0/base; [ $cfg = base ] || mdir=$D/single_$O
    ( cd $D && nice -n 5 $PY $R/pipeline/score_registered.py $e $trk --meshes $mdir --t3 $D/t3 --kit $KIT --out $out ) \
      > ${out%.json}.log 2>&1 && echo "$(date -u +%FT%TZ) OK $cfg ep$e" || echo "$(date -u +%FT%TZ) FAIL $cfg ep$e"
  done
done
