#!/bin/bash
# holdout.sh EP: prep -> HRC F1 -> 10-seed + per-frame scoring of V; deletes the depth cache after. Logs ho/<EP>.log
e=$1; cd /home/user/work; . venv/bin/activate; M=m14p/meshes/m14p_public; mkdir -p ho
./prep_ep.sh $e
python /home/user/v2d-track3/pipeline/hrc.py --t3 t3 --ep $e --track ctrlC/C/ep$e --depth depth/ep$e/depths_fs0.5.npy \
  --lib /home/user/v2d-track3/meshes/library_v3 --hands handsC/ep$e/hands_refined.npz --band 0.25 --tau 0.020 --gate near \
  --skip water_pitcher --out ho/V/ep$e > ho/hrc_ep$e.log 2>&1 && rm -rf depth/ep$e
python score_registered.py $e ho/V/ep$e/poses_world_vo.npz --meshes $M --t3 t3 --kit kit/v2d_submission_kit --reg_seeds 10 --scores_only --out ho/V_ep$e.json > /dev/null 2>&1
python score_registered.py $e ho/V/ep$e/poses_world_vo.npz --meshes $M --t3 t3 --kit kit/v2d_submission_kit --out ho/V1_ep$e.json --per_frame ho/V_ep${e}_pf.npz > /dev/null 2>&1
[ -s ho/V_ep$e.json ] && echo "HO-OK $e" || echo "HO-FAIL $e"
