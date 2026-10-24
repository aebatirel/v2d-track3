#!/bin/bash
# CPU zero-action replays (FlashCHORD, evaluator-like: VOC 0, frame-0 start, no termination), kp 400 embodiment.
# args: list of ep:variant:frames
FCD=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/src/video_to_data/robotic_grounding/flash_chord
cd $FCD
for spec in "$@"; do
  IFS=: read ep v n <<< "$spec"
  seq=$(printf 't3_ep%03d' $ep)
  ref=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$ep/$v/processed/sequence_id=$seq/robot_name=sharpa_wave/ref_gl_ilc.parquet
  out=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/traces/ep${ep}_${v}.npz
  [ -s $out ] && continue
  env OMP_NUM_THREADS=1 EMB=sharpa_hands_mid DEV=cpu nice -n 10 /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/fcvenv/bin/python /home/user/v2d-track3/tools/trace_rollout.py zero $out $ref $n > /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/traces/ep${ep}_${v}.log 2>&1
  echo "$spec $(tail -1 /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/traces/ep${ep}_${v}.log)" >> /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/traces/done.txt
done
