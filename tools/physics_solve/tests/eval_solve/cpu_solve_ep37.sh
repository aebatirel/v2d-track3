#!/bin/bash
# CPU test (2026-10-31) of the eval-solve chain on ONE real eval reference: eval 37's packed grasp-lock reference
# (runs/20261024-pack-31ef267/refs/glockt/ep37/.../ref_gl_ilc.parquet, md5 b78747bb) with its stored asset copy
# (refs/sf/ep37/assets), at a tiny solver scale, with the same tool commands as ops/jobs/eval_solve.sh steps 3-8 (DEV=cpu).
# The ONLY test-side change: a copy of the reference whose object_urdf_paths point at the local asset copy instead of
# /content/... (this machine has no /content); every other column is byte-for-byte the stored one (checked below).
# No ground truth is read. Usage: S=<scratchpad> MIRROR=<local store mirror> bash cpu_solve_ep37.sh OUTDIR
set -u
S=${S:?}; MIRROR=${MIRROR:?}; OUT=${1:?}; REPO=/home/user/v2d-track3; T=$REPO/tools
FCD=$S/src/video_to_data/robotic_grounding/flash_chord; FPY=$S/fcvenv/bin/python; BPY=$S/venv/bin/python
export KIT=$S/dl/kit/x/v2d_submission_kit EMB=sharpa_hands_mid OMP_NUM_THREADS=1 DEV=cpu
SRC=$MIRROR/runs/20261024-pack-31ef267; H=processed/sequence_id=t3_ep037/robot_name=sharpa_wave
rm -rf $OUT; mkdir -p $OUT/root/refs/sf/ep37 $OUT/O/ep37; RT=$OUT/root; O=$OUT/O
cp -r $SRC/refs/sf/ep37/assets $RT/refs/sf/ep37/
B=$RT/refs/evsolve/ep37; W=$B/$H; mkdir -p $W $B/reconstructed_stage
cp $SRC/refs/glockt/ep37/reconstructed_stage/t3_ep037_support.usda $B/reconstructed_stage/
echo "$(date -u +%FT%TZ) code $(git -C $REPO rev-parse --short HEAD)+wip solve.py $(md5sum < $T/physics_solve/solve.py | cut -c1-8) jitter_check.py $(md5sum < $T/physics_solve/jitter_check.py | cut -c1-8) eval_inputs.py $(md5sum < $T/physics_solve/eval_inputs.py | cut -c1-8) eval_solve_summary.py $(md5sum < $T/physics_solve/eval_solve_summary.py | cut -c1-8)"
echo "stored reference md5 $(md5sum < $SRC/refs/glockt/ep37/$H/ref_gl_ilc.parquet | cut -c1-32) (table: b78747bb1d941fa56121886cc15ec225)"
$BPY -I - $SRC/refs/glockt/ep37/$H/ref_gl_ilc.parquet $W/ref_in.parquet $RT << 'PY'
import sys, pyarrow as pa, pyarrow.parquet as pq
src, dst, rt = sys.argv[1:]
t = pq.read_table(src); i = t.column_names.index('object_urdf_paths')
u = [p.replace('/content/', rt + '/', 1) for p in t.column(i)[0].as_py()]
t2 = t.set_column(i, 'object_urdf_paths', pa.array([u], type=t.schema.field(i).type)); pq.write_table(t2, dst)
t3 = pq.read_table(dst)
diff = [c for c in t.column_names if not t.column(c).equals(t3.column(c))]
print('test copy: columns differing from the stored reference:', diff, '->', u)
PY
# eval_inputs check on the test copy (asset root = the test root; override mode as the md5 differs by construction)
$BPY -I $T/physics_solve/eval_inputs.py check $REPO/docs/research/physics-2026-10-30/eval_solve/packed_refs.json 37 $W/ref_in.parquet --root $RT --override --out $O/ep37/inputs.json; echo "check rc=$?"
echo $W > $O/ep37/work.txt; echo runs/20261024-pack-31ef267/refs/glockt/ep37/$H/ref_gl_ilc.parquet > $O/ep37/input_store_path.txt
N=$($BPY -c "import pyarrow.parquet as pq; print(len(pq.read_table('$W/ref_in.parquet').column('robot_left_wrist_position')[0].as_py()))")
JK=${JK:-4}; ARGS=${ARGS:-"--workers 0 --worlds 8 --robust 2 --horizon 8 --knot 4 --ctrl 4 --iters 2 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.9518 --retries 1 --retry 0.05 --back 1 --rob_pos 0.0005 --rob_fin 0.005 --early_rel 0.02 --early_n 2 --min_iters 2 --seed 0"}
t0=$(date +%s)
( cd $FCD && $FPY $T/physics_solve/jitter_check.py $W/ref_in.parquet --device cpu --k $JK --seed 0 --json $O/ep37/jitter_in.json ) > $O/ep37/jitter_in.log 2>&1; echo "jitter in rc=$? $(( $(date +%s) - t0 )) s: $(tail -1 $O/ep37/jitter_in.log | cut -c1-200)"
t0=$(date +%s)
( cd $FCD && $FPY $T/physics_solve/solve.py $W/ref_in.parquet $W/ref_ps.parquet --device cpu $ARGS --deadline_s $(( N * ${DLPF:-18} )) --pace_s ${PACE:-14.4} ) > $O/ep37/solve.out 2>&1; echo "solve rc=$? $(( $(date +%s) - t0 )) s"
grep -a -E 'moving objects|deadline|rollback|bit-identical|wrote' $O/ep37/solve.out | cut -c1-250
cp $W/ref_ps_solve.json $W/ref_ps_solve.log $O/ep37/ 2> /dev/null
t0=$(date +%s)
( cd $FCD && $FPY $T/trace_rollout.py zero $O/ep37/zero_ps.npz $W/ref_ps.parquet $N ) > $O/ep37/zero_ps.log 2>&1; echo "zero replay rc=$? $(( $(date +%s) - t0 )) s"
( cd $REPO && $BPY $T/trace_score.py $W/ref_ps.parquet $O/ep37/zero_ps.npz:zero_action $W/ref_ps_solve.npz:truth ) > $O/ep37/zero_score_ps.txt 2>&1; echo "trace_score rc=$?: $(tr '\n' ' ' < $O/ep37/zero_score_ps.txt)"
$BPY $T/rest_check.py $O/ep37/zero_ps.npz $W/ref_ps.parquet > $O/ep37/rest_check_ps.json 2>&1; echo "rest_check rc=$?: $(tr -d '\n ' < $O/ep37/rest_check_ps.json | cut -c1-300)"
t0=$(date +%s)
( cd $FCD && $FPY $T/physics_solve/jitter_check.py $W/ref_ps.parquet --device cpu --k $JK --seed 0 --json $O/ep37/jitter_ps.json ) > $O/ep37/jitter_ps.log 2>&1; echo "jitter ps rc=$? $(( $(date +%s) - t0 )) s: $(tail -1 $O/ep37/jitter_ps.log | cut -c1-200)"
$BPY $T/physics_solve/eval_solve_summary.py $O 37 --run 20261031-evsolvetest-cpu --root $RT > /dev/null; echo "summary rc=$?"
cat $O/handoff.tsv
$BPY -c "import json; d=json.load(open('$O/summary.json')); e=d['episodes']['ep37']; print(json.dumps({k: e.get(k) for k in ('status','delta_jittered','jitter_in','jitter_ps','solve','zero_ps')}, indent=None)); print('solved:', json.dumps(e.get('solved'))); print('rest_check_ps:', json.dumps(e.get('rest_check_ps')))"
echo "$(date -u +%FT%TZ) DONE"
