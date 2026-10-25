#!/bin/bash
# CPU grasp-lock arm (2026-10-25; generalises docs/research/grasp/audit-starts-scripts/run_glock_cpu.sh to the repo
# code and one output tree per arm): grasp_lock.py -> wrist_ilc.py (kp 400, 4 iterations) -> zero-action replay
# (tools/trace_rollout.py) -> sim_vs_ref (tools/trace_score.py). No ground truth.
#   tools/cpu_glock_zero.sh IN_PARQUET ARM_DIR "GL_ARGS"
# IN_PARQUET sits in a reference tree (processed/<seq>/<robot>/x.parquet + reconstructed_stage/); ARM_DIR gets its own
# copy of that layout (reconstructed_stage linked), ref_gl.parquet, ref_gl_grasp_lock.json, ref_gl_ilc.parquet,
# zero.npz and the logs. Env: FCD (FlashCHORD dir), PY (its python), SPY (a python with pandas for scoring), KIT.
set -u
IN=$1; ARM=$2; GA=$3
S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad
FCD=${FCD:-$S/src/video_to_data/robotic_grounding/flash_chord}; PY=${PY:-$S/fcvenv/bin/python}
REPO=$(cd "$(dirname "$0")/.." && pwd)
SUB=$(echo "$IN" | grep -o 'processed/.*' | xargs dirname); ROOT=${IN%%/processed/*}
D=$ARM/$SUB; mkdir -p $D; cp -f "$IN" $D/ref_in.parquet
[ -e $ARM/reconstructed_stage ] || ln -s $ROOT/reconstructed_stage $ARM/reconstructed_stage
cd $FCD; export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
echo "$(date -u +%FT%TZ) code $(git -C $REPO rev-parse --short HEAD) in $IN args [$GA]" > $ARM/run.log
( FC=$FCD GL_WRIST_KP=400 nice -n 10 $PY $REPO/pipeline/grasp_lock.py $D/ref_in.parquet $D/ref_gl.parquet $GA ) > $ARM/gl.log 2>&1 \
  || { echo GL_FAIL >> $ARM/run.log; echo GL_FAIL; exit 1; }
( EMB=sharpa_hands_mid nice -n 10 $PY $REPO/pipeline/wrist_ilc.py $D/ref_gl.parquet $D/ref_gl_ilc.parquet --iters 4 --device cpu ) > $ARM/ilc.log 2>&1 \
  || { echo ILC_FAIL >> $ARM/run.log; echo ILC_FAIL; exit 1; }
N=$($PY -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$IN').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
( EMB=sharpa_hands_mid DEV=cpu nice -n 10 $PY $REPO/tools/trace_rollout.py zero $ARM/zero.npz $D/ref_gl_ilc.parquet $N ) > $ARM/zero.log 2>&1 \
  || { echo ZERO_FAIL >> $ARM/run.log; echo ZERO_FAIL; exit 1; }
KIT=${KIT:-$S/kit/v2d_submission_kit} ${SPY:-$S/venv/bin/python} $REPO/tools/trace_score.py $D/ref_gl_ilc.parquet $ARM/zero.npz:zero >> $ARM/run.log 2>&1
echo "$(date -u +%FT%TZ) DONE" >> $ARM/run.log; tail -2 $ARM/run.log
