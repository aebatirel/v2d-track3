#!/bin/bash
# mask10, eval side (GT-free): refine S12 variants on eval 10's STORED perception track (the one behind packs 6-8; same
# inputs and sha256 as T1's t1_eval10.sh: $S/leak/t1/eval10/in). Eval has no ground truth: nothing here reads mocap,
# scans or observation.objects; refine.assert_inference_input checks every input. No eval reference is written or
# changed: outputs go to $W/eval10/ only. Depth for the veto: our stored eval-10 depth frames 0/30/60/150 (29 Oct
# recomputation, pulled by the eval screen), at half resolution in a grid npz.
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/mask10; E=$W/eval10; IN=$S/leak/t1/eval10/in; PY=$S/map/scoring/venv/bin/python; FPY=$S/carve/fcvenv/bin/python
REPO=/home/user/v2d-track3; PCS=$REPO/meshes/carve/ev10; RF="$PY -I $REPO/pipeline/refine.py"
mkdir -p $E/logs
$PY -I -c "
import sys, numpy as np
sys.path.insert(0, '$REPO/pipeline'); from refine import assert_inference_input
f = '$S/screen/dl_depth/ev10_f0_30_60_150.npy'; assert_inference_input(f)
d = np.load(f)[:, ::2, ::2].astype(np.float32)
np.savez('$E/ev10_depth4.npz', frames=np.array([0, 30, 60, 150]), depth=d, T=161); print('depth grid', d.shape)"
sha256sum $IN/* $E/ev10_depth4.npz > $E/inputs_sha256.txt
sha256sum $REPO/pipeline/refine.py $REPO/pipeline/nest.py $REPO/tools/nest_physics.py >> $E/inputs_sha256.txt
H=$(readlink -f $IN/hands_refined.npz)
$RF --in $IN --out $E/S2 --steps S2 > $E/logs/S2.log 2>&1 || echo FAIL S2
$RF --in $IN --out $E/V1 --steps S12,S2 > $E/logs/V1.log 2>&1 || echo FAIL V1
$RF --in $IN --out $E/V1h --steps S12,S2 --s12_mode height > $E/logs/V1h.log 2>&1 || echo FAIL V1h
$RF --in $IN --out $E/V1d --steps S12,S2 --s12_depth $E/ev10_depth4.npz > $E/logs/V1d.log 2>&1 || echo FAIL V1d
$RF --in $IN --out $E/V2 --steps S12,S2 --s12_inner floor --s12_pieces $PCS > $E/logs/V2.log 2>&1 || echo FAIL V2
$RF --in $IN --out $E/pre --steps S12 > $E/logs/pre.log 2>&1 || echo FAIL pre
$FPY -I $REPO/tools/nest_physics.py --in $E/pre --popt $E/pre/pose_opt.json --pieces $PCS --hands $H --mode inner --out $E/pre_phys > $E/logs/phys.log 2>&1 || echo FAIL phys
$RF --in $E/pre_phys --out $E/V3 --steps S2 --hands $H --depth $(readlink -f $IN/depth0.npy) > $E/logs/V3.log 2>&1 || echo FAIL V3
$FPY -I $REPO/tools/nest_physics.py --in $IN --popt $E/pre/pose_opt.json --pieces $PCS --hands $H --mode both --out $E/raw_phys > $E/logs/physb.log 2>&1 || echo FAIL physb
$RF --in $E/raw_phys --out $E/V3p --steps S2 --hands $H --depth $(readlink -f $IN/depth0.npy) > $E/logs/V3p.log 2>&1 || echo FAIL V3p
grep -h "S12 window\|S12: no\|depth veto\|G1" $E/logs/V1.log $E/logs/V1d.log | cut -c1-300
grep -h "nest_physics" $E/logs/phys.log $E/logs/physb.log
