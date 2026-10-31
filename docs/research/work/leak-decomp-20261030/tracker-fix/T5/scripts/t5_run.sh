#!/bin/bash
# T5 first stage (tracker-fix PLAN §3 T5, §4 item 3): robust camera on public ep24, this VM, CPU, $0. Inference part
# (vo_t5.py, GT-free) for every declared run, then the oracle scoring (t5_score.py, reads mocap) after all cameras exist.
# Declared before any scoring (31 Oct ~05:55 UTC); development used GT-free readouts only (RESULTS.md §1):
#   main        base (control), plane (F3 alone, primary plane-only), rvo (F1 alone), rvo_plane (F1 + F3, primary VO)
#               SGBM keyframe maps, KF_OK 120, plane gate 300 samples
#   plane3000   plane with the first, a-priori gate (3000 samples)                       sensitivity
#   sift        rvo, rvo_plane with vo17's sparse SIFT stereo maps                         ablation (vo17 map)
#   k150        rvo, rvo_plane with KF_OK 150 (the first default)                        sensitivity
#   nomask      rvo without object/hand masks                                             ablation (masks)
#   latest      rvo with perc2's latest-keyframe chain                                    ablation (earliest keyframe)
# Inputs: public cam b/c videos of ep24 (dataset pulls, hard-linked out of the 'observation.images' path that
# refine.assert_inference_input refuses), the public camera calibration, Phase-1 P_o poses.npz, refine/in vo.json and
# hands_refined.npz, library_v3 meshes.
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
REPO=/home/user/v2d-track3; T5=$REPO/docs/research/work/leak-decomp-20261030/tracker-fix/T5
PY=$S/map/scoring/venv/bin/python; W=$S/leak/t5/runs; mkdir -p $W/logs
ARGS="--b $S/leak/t5/v/ep24_b.mp4 --c $S/leak/t5/v/ep24_c.mp4 --calib $S/hfds/track_3/public/meta/camera_calibration.json
 --poses $S/leak/p1/runs/20261030-orcP1c-87fc869/results/leak_p1/ep24/perc2/poses.npz --vo $S/refine/in/ep24/vo.json
 --hands $S/refine/in/ep24/hands_refined.npz --meshes $REPO/meshes/library_v3"
(cd $REPO && git rev-parse HEAD && sha256sum $T5/scripts/vo_t5.py $T5/scripts/t5_score.py pipeline/det_rules.py pipeline/refine.py) > $W/code_version.txt
run() { name=$1; shift; mkdir -p $W/$name; $PY -I $T5/scripts/vo_t5.py $ARGS --out $W/$name "$@" > $W/logs/$name.log 2>&1 || echo "FAIL $name"; }
run main --variants base,plane,rvo,rvo_plane &
run plane3000 --variants plane --pl_min 3000 &
run sift --variants rvo,rvo_plane --map sift &
wait
run k150 --variants rvo,rvo_plane --kf_ok 150 &
run nomask --variants rvo --no_mask 1 &
run latest --variants rvo --kf_mode latest &
wait
# ---- ORACLE scoring (mocap), after every camera above exists
$PY -I $T5/scripts/t5_score.py $W $W/t5_scores.json \
  main:base,main:plane,main:rvo,main:rvo_plane,plane3000:plane,sift:rvo,sift:rvo_plane,k150:rvo,k150:rvo_plane,nomask:rvo,latest:rvo \
  > $W/logs/score.log 2>&1 || echo "FAIL score"
cat $W/logs/score.log
