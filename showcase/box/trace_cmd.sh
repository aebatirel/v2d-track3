# usage (on a box): bash trace_cmd.sh ROBOT   -> /content/results/showcase/ep27_ROBOT/policy_trace.npz (no GL: viewer null)
r=$1; O=/content/results/showcase/ep27_$r; FC=/content/v2d/robotic_grounding/flash_chord
CK=$(python -c "import json; print(json.load(open('$O/selection.json'))['chosen'])")
PQ=$(ls /content/refs/sc/ep27_$r/processed/*/*/*.parquet | head -1)
N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.ParquetFile('$PQ').read().column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
OV="evaluation.checkpoint=$CK task.parquet='$PQ' reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true viewer.backend=none viewer.num_frames=$N markers.keypoints=false markers.contacts=false"
for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
cd $FC && DEV=cuda timeout 1500 .venv/bin/python /content/v2d-track3/tools/trace_rollout.py policy $O/policy_trace.npz $OV > $O/trace_null.log 2>&1
echo "trace rc=$? $(ls -la $O/policy_trace.npz 2>&1 | cut -c1-120)"; tail -2 $O/trace_null.log | cut -c1-200
