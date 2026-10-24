#!/bin/bash
# sim_settle (CPU, kp 400 embodiment) on the localised grasp-lock input, then the grasp-lock pipeline on the settled start.
EP=$1; NAME=$2; GA=$3
FCD=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/src/video_to_data/robotic_grounding/flash_chord; PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/fcvenv/bin/python; C=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/code
IN=$(ls /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle_in/processed/*/*/ref_sf.parquet); HIVE=$(dirname ${IN#/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle_in/})
OUTT=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle_out; mkdir -p $OUTT/$HIVE; cp -r /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle_in/reconstructed_stage $OUTT/ 2>/dev/null
cd $FCD; export OMP_NUM_THREADS=1
( EMB=sharpa_hands_mid DEV=cpu nice -n 10 $PY $C/tools/sim_settle.py $IN $OUTT/$HIVE/ref_settled.parquet ) > /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle.log 2>&1 || { echo SETTLE_FAIL; exit 1; }
G=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/gl_settle; mkdir -p $G/$HIVE; cp -r /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/ep$EP/settle_in/reconstructed_stage $G/; cp $OUTT/$HIVE/ref_settled.parquet $G/$HIVE/ref_sf.parquet
bash /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/scripts/run_glock_cpu.sh $G $NAME "$GA"
