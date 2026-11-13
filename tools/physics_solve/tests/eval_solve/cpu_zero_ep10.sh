#!/bin/bash
# CPU check (2026-10-31) that eval 10's /content/assets as eval_solve.sh builds them (make_assets library_v3 + pieces
# meshes/carve/ev10, current code) behave like the packed training's: the official zero-action replay of the packed ep10
# reference (md5 1a5003d9) on CPU vs the training box's stored zero_score.txt (gl10A2: 0.5790, GPU). Test-only change:
# object_urdf_paths of a copy point at the locally built assets (no /content here). Also eval 37 (its stored asset copy):
# CPU replay vs pack-31ef267's stored 0.9209. No ground truth. Usage: S=<scratchpad> MIRROR=<store mirror> ASSETS=<built
# /content/assets> bash cpu_zero_ep10.sh OUTDIR
set -u
S=${S:?}; MIRROR=${MIRROR:?}; ASSETS=${ASSETS:?}; OUT=${1:?}; REPO=/home/user/v2d-track3; T=$REPO/tools
FCD=$S/src/video_to_data/robotic_grounding/flash_chord; FPY=$S/fcvenv/bin/python; BPY=$S/venv/bin/python
export KIT=$S/dl/kit/x/v2d_submission_kit EMB=sharpa_hands_mid OMP_NUM_THREADS=1 DEV=cpu
rm -rf $OUT; mkdir -p $OUT
for spec in "10:20261026-gl10A2-5e0e100:$ASSETS" "37:20261024-pack-31ef267:$MIRROR/runs/20261024-pack-31ef267/refs/sf/ep37/assets"; do
  IFS=: read -r e run aroot <<< "$spec"; E3=$(printf %03d $e); H=processed/sequence_id=t3_ep$E3/robot_name=sharpa_wave
  B=$OUT/ep$e; mkdir -p $B/$H $B/reconstructed_stage; cp $MIRROR/runs/$run/refs/glockt/ep$e/reconstructed_stage/*.usda $B/reconstructed_stage/
  $BPY -I - $MIRROR/runs/$run/refs/glockt/ep$e/$H/ref_gl_ilc.parquet $B/$H/ref.parquet $aroot << 'PY'
import os, sys, pyarrow as pa, pyarrow.parquet as pq
src, dst, ar = sys.argv[1:]
t = pq.read_table(src); i = t.column_names.index('object_urdf_paths'); u = t.column(i)[0].as_py()
u2 = [os.path.join(ar, 'urdf', os.path.basename(p)) for p in u]
pq.write_table(t.set_column(i, 'object_urdf_paths', pa.array([u2], type=t.schema.field(i).type)), dst)
print('urdf paths', u, '->', u2)
PY
  N=$($BPY -c "import pyarrow.parquet as pq; print(len(pq.read_table('$B/$H/ref.parquet').column('robot_left_wrist_position')[0].as_py()))")
  ( cd $FCD && $FPY $T/trace_rollout.py zero $B/zero.npz $B/$H/ref.parquet $N ) > $B/zero.log 2>&1
  echo "ep$e CPU replay rc=$?: $(cd $REPO && $BPY $T/trace_score.py $B/$H/ref.parquet $B/zero.npz:zero_action | tr '\n' ' ') | stored (training box, GPU): $(tr '\n' ' ' < $MIRROR/runs/$run/results/glock_public/ep$e/zero_score.txt)"
  echo "ep$e CPU rest_check: $($BPY $T/rest_check.py $B/zero.npz $B/$H/ref.parquet | tr -d '\n ' | cut -c1-260) | stored: $(tr -d '\n ' < $MIRROR/runs/$run/results/glock_public/ep$e/rest_check.json | cut -c1-260)"
done
