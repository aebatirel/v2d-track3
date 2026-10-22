#!/bin/bash
# colour every finished library mesh with its fusion episodes' videos and copy it into the repo (meshes/library_v1)
PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/venv/bin/python; LIB=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/library; OUT=/home/user/v2d-track3/meshes/library_v1; mkdir -p $OUT
printf 'white_pot|41 44 2 27|\n' > man0.txt
cat man0.txt man1.txt man2.txt | while IFS='|' read -r obj eps extra; do
  [ -s $LIB/${obj}_full.glb ] || continue
  [ -s $OUT/$obj.glb ] && [ $OUT/$obj.glb -nt $LIB/${obj}_full.glb ] && continue
  P=""; V=""
  for e in $eps; do
    [ -s /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/v/ep${e}_c.mp4 ] || curl -sSfL -o /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/v/ep${e}_c.mp4 "https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/public/videos/chunk-000/observation.images.ego_cam_c/episode_$(printf %06d $e).mp4"
    P="${P:+$P,}/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/perc/ep$e/poses.npz"; V="${V:+$V,}/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/v/ep${e}_c.mp4"
  done
  $PY -I /home/user/v2d-track3/pipeline/mesh_color.py --mesh $LIB/${obj}_full.glb --obj $obj --poses $P --video $V --calib /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/t3/calib.json --out $OUT/$obj.glb < /dev/null | tail -1
  cp $LIB/$obj.json $OUT/$obj.recon.json
done
cp -n /home/user/v2d-track3/spoon/wooden_spoon.glb $OUT/wooden_spoon.glb
ls -la $OUT
