#!/bin/bash
# run_hrc.sh TAG "HRC ARGS" EP...: HRC on control C, then single-seed registered score (m14p meshes) -> hrc/<TAG>_ep<e>.json
TAG=$1; ARGS=$2; shift 2; cd /home/user/work; . venv/bin/activate; M=m14p/meshes/m14p_public
for e in "$@"; do
  python /home/user/v2d-track3/pipeline/hrc.py --t3 t3 --ep $e --track ctrlC/C/ep$e --depth depth/ep$e/depths_fs0.5.npy \
    --lib /home/user/v2d-track3/meshes/library_v3 --hands handsC/ep$e/hands_refined.npz $ARGS --out hrc/$TAG/ep$e > hrc/$TAG.ep$e.log 2>&1 \
  && python score_registered.py $e hrc/$TAG/ep$e/poses_world_vo.npz --meshes $M --t3 t3 --kit kit/v2d_submission_kit \
       --out hrc/${TAG}_ep$e.json --per_frame hrc/${TAG}_ep${e}_pf.npz > /dev/null 2>&1 || echo "FAIL $TAG $e"
done
