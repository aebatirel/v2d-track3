#!/bin/bash
# T1, eval side (tracker-fix PLAN §4 item 1): pipeline/refine.py S6 GT-free on eval 10's STORED perception track, the one
# the packed eval-10 policy's reference was built from (gl10A2 trained on 20261024-evB-664e5fd refs/perc2mck/ep10 +
# perc2/ep10; the pack-6 copies have the same store sha256: poses fb9103fa…, det_f0 3f034015…, hands_refined cdd52386…).
# Eval has no ground truth: nothing here reads mocap, scans or observation.objects; refine.assert_inference_input checks
# every input. Nothing on eval is tuned, and no eval reference is changed: outputs go to $W/eval10/ only.
# Inputs (already local from the eval screen's targeted pulls; no new store download):
#   poses.npz, vo.json        runs/20261026-pack6-5203d42/perc2/ep10/
#   hands_refined.npz (KR)    runs/20261026-pack6-5203d42/refs/perc2mck/ep10/
#   depth0.npy                perc2's own frame-0 depth: det_f0.npz 'depth' (= depth[::2, ::2], float16) repeated 2x2,
#                             so refine's [::2, ::2] + K/2 sees exactly perc2's TRACK_GUARD input
#   cross-check               frame 0 of the 29 Oct recomputed eval depth (cache/depth/eval/ep10, rows f0/30/60/150)
# Usage: t1_eval10.sh   -> $W/eval10/{in,S6S2,S6S2_d29,S2}/ and logs
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/leak/t1; E=$W/eval10; PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
P6=runs/20261026-pack6-5203d42
mkdir -p $E/in $E/logs
ln -sfn $S/daudit/dl_evposes/$P6/perc2/ep10/poses.npz $E/in/poses.npz
ln -sfn $S/screen/dl/$P6/perc2/ep10/vo.json $E/in/vo.json
ln -sfn $S/screen/dl/$P6/refs/perc2mck/ep10/hands_refined.npz $E/in/hands_refined.npz
$PY -I -c "
import sys, numpy as np
sys.path.insert(0, '$REPO/pipeline'); from refine import assert_inference_input
f = '$S/screen/dl/$P6/perc2/ep10/det_f0.npz'; assert_inference_input(f)
d = np.load(f)['depth'].astype(np.float32)
np.save('$E/in/depth0.npy', np.repeat(np.repeat(d, 2, 0), 2, 1)); print('depth0', d.shape, '-> 2x')"
sha256sum $E/in/* > $E/inputs_sha256.txt; sha256sum $REPO/pipeline/refine.py >> $E/inputs_sha256.txt
(cd $REPO && git rev-parse HEAD && git status --short pipeline/refine.py) >> $E/inputs_sha256.txt
$PY -I $REPO/pipeline/refine.py --in $E/in --out $E/S6S2 --steps S6,S2 > $E/logs/S6S2.log 2>&1 || echo FAIL S6S2
$PY -I $REPO/pipeline/refine.py --in $E/in --out $E/S6S2_d29 --steps S6,S2 \
  --depth $S/screen/dl_depth/ev10_f0_30_60_150.npy > $E/logs/S6S2_d29.log 2>&1 || echo FAIL S6S2_d29
$PY -I $REPO/pipeline/refine.py --in $E/in --out $E/S2 --steps S2 > $E/logs/S2.log 2>&1 || echo FAIL S2
grep -h "S6 \|plane" $E/logs/S6S2.log $E/logs/S6S2_d29.log | cut -c1-260
