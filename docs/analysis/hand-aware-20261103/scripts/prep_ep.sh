#!/bin/bash
# prep_ep.sh EP: depth cache (store) -> MediaPipe hands (tasks API) -> hand_refine. GT-free. Logs to prep/ep<EP>.log
e=$1; cd /home/user/work; . venv/bin/activate; mkdir -p depth/ep$e handsC/ep$e prep
[ -s depth/ep$e/depths_fs0.5.npy ] || curl -sSfL -o depth/ep$e/depths_fs0.5.npy "https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/cache/depth/public/ep$e/depths_fs0.5.npy"
if [ ! -s handsC/ep$e/hands_refined.npz ]; then
  python /home/user/v2d-track3/pipeline/hands_mp.py --ep $e --t3 t3 --depth depth/ep$e/depths_fs0.5.npy --poses ctrlC/C/ep$e/poses.npz --video_a t3/v/ep${e}_a.mp4 --out handsC/ep$e --api tasks --task_model ckpt/hand_landmarker.task > prep/ep$e.hands.log 2>&1
  python /home/user/v2d-track3/pipeline/hand_refine.py --hands handsC/ep$e/hands.npz --poses ctrlC/C/ep$e/poses.npz --out handsC/ep$e/hands_refined.npz > prep/ep$e.refine.log 2>&1
fi
[ -s handsC/ep$e/hands_refined.npz ] && echo "PREP-OK $e" || echo "PREP-FAIL $e"
