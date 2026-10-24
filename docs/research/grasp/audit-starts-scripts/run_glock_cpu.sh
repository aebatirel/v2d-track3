#!/bin/bash
# grasp-lock reference built on CPU with the run's code (e49e83d): grasp_lock -> wrist ILC (kp 400) -> zero-action replay.
# args: TREE (with processed/.../ref_sf.parquet) NAME "GL_ARGS"
TREE=$1; NAME=$2; GA=$3
FCD=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/src/video_to_data/robotic_grounding/flash_chord; PY=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/fcvenv/bin/python; C=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/code
IN=$(ls $TREE/processed/*/*/ref_sf.parquet); D=$(dirname $IN)
cd $FCD
export OMP_NUM_THREADS=1
( FC=$FCD GL_WRIST_KP=400 nice -n 10 $PY $C/pipeline/grasp_lock.py $IN $D/ref_gl.parquet $GA ) > $TREE/gl.log 2>&1 || { echo GL_FAIL; exit 1; }
( EMB=sharpa_hands_mid nice -n 10 $PY $C/pipeline/wrist_ilc.py $D/ref_gl.parquet $D/ref_gl_ilc.parquet --iters 4 --device cpu ) > $TREE/ilc.log 2>&1 || { echo ILC_FAIL; exit 1; }
N=$($PY -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$IN').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
( EMB=sharpa_hands_mid DEV=cpu nice -n 10 $PY $C/tools/trace_rollout.py zero /tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts/sim/traces/$NAME.npz $D/ref_gl_ilc.parquet $N ) > $TREE/zero.log 2>&1
echo DONE $NAME
