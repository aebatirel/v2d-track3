#!/bin/bash
# CPU replays of the final pack's (14p) submitted policies, played like the official evaluator: frame 0 to the end,
# VOC 0, no assist, no early termination (tools/trace_rollout.py policy). Setups from setup_replays.py.
# A replay is a fresh rollout, not the packed one; compare_packed.py measures how far its objects are from the packed
# rows. CPU replays are deterministic (ep27 check, 2026-11-27).
#   FC=<flash_chord dir> bash replay_all.sh [OUT=/content/ev] [EPS="1 3 ..."] [PAR=2]
set -u
FC=${FC:?FC missing}; OUT=${OUT:-/content/ev}; PAR=${PAR:-2}; REPO=$(cd "$(dirname "$0")/../.." && pwd)
EPS=${EPS:-$(ls -d $OUT/ep* | sed 's#.*/ep##' | sort -n | tr '\n' ' ')}
one() {
  local ep=$1 D=$OUT/ep$1 T CK N OV
  [ -s $D/replay_cpu.npz ] && return 0
  T=$(python3 -c "import json; print(json.load(open('$D/setup.json'))['task'])"); CK=$D/policy.safetensors
  N=$(cd $FC && .venv/bin/python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.ParquetFile('$T').read().column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  OV="evaluation.checkpoint=$CK task.parquet='$T' reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
  for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
  OV="$OV viewer.backend=none viewer.num_frames=$N markers.keypoints=false markers.contacts=false training.device=cpu"
  echo "$OV" > $D/replay_overrides.txt
  local t0=$(date +%s)
  ( cd $FC && timeout 3600 env DEV=cpu .venv/bin/python $REPO/tools/trace_rollout.py policy $D/replay_cpu.npz $OV ) > $D/replay.log 2>&1
  echo "ep$ep: frames $N, rc $?, $(( $(date +%s) - t0 )) s, $( [ -s $D/replay_cpu.npz ] && echo ok || echo FAILED )"
}
pids=()
for ep in $EPS; do
  one $ep & pids+=($!)
  [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"; exit 0
