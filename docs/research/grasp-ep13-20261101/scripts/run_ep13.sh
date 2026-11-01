#!/bin/bash
# Pre-registered ep13 arm (docs/research/grasp-ep13-20261101/PREREG.md): one solve + checks + jitter check.
# Usage: S=<scratchpad> run_ep13.sh REF(P|O|P2|O2) METHOD(anneal|grasp)
#   P, O:   the twins' references, S/inputs/ep13_<REF>/processed/<seq>/<robot>/ref_in.parquet (prep_inputs.py)
#   P2, O2: the two-hand rebuilds, S/gl2/ep13_<P|O>/processed/<seq>/<robot>/ref_gl_ilc.parquet (tools/cpu_glock_zero.sh)
#   -> S/ep13/<REF>_<METHOD>/
# Steps: solve.py (settings below, identical for both methods except --method and the GRASP options) -> official
# zero-action replay of the written parquet (tools/trace_rollout.py zero) -> trace_score (replay and the solver's own truth
# trajectory) -> bit-identity of replay vs truth -> jitter_check.py --k 17 --seed 0 (the gate metric). CPU only, no
# ground truth (the oracle reference O is a stored diagnostic input on a public episode).
set -u; S=${S:?}; REF=$1; METHOD=$2; T=/home/user/v2d-track3/tools
FCD=$S/src/video_to_data/robotic_grounding/flash_chord; FPY=$S/fcvenv/bin/python; BPY=$S/venv/bin/python
export OMP_NUM_THREADS=1 EMB=sharpa_hands_mid DEV=cpu KIT=$S/kit/v2d_submission_kit
case $REF in P|O) P=$(ls $S/inputs/ep13_$REF/processed/*/*/ref_in.parquet) ;; P2|O2) P=$(ls $S/gl2/ep13_${REF:0:1}/processed/*/*/ref_gl_ilc.parquet) ;; *) exit 2 ;; esac
D=$(dirname $P); O=$S/ep13/${REF}_$METHOD; mkdir -p $O
OUTP=$D/ps_$METHOD.parquet; N=190
COMMON="--workers 4 --worlds 32 --robust 4 --horizon 16 --knot 4 --ctrl 4 --iters 8 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 \
--sig_fin 0.15 --anneal 0.80 --retries 4 --retry 0.05 --back 3 --rob_pos 0.0005 --rob_fin 0.005 --seed 0"
GRASP=${GRASP_ARGS:?set GRASP_ARGS (frozen in PREREG.md)}
[ "$METHOD" = grasp ] && EXTRA="--method grasp $GRASP" || EXTRA="--method anneal"
{ echo "$(date -u +%FT%TZ) ep13 $REF $METHOD code $(git -C /home/user/v2d-track3 rev-parse --short HEAD)$(git -C /home/user/v2d-track3 diff --quiet HEAD -- tools || echo +wip) \
solve.py $(md5sum < $T/physics_solve/solve.py | cut -c1-8) grasp_window.py $(md5sum < $T/physics_solve/grasp_window.py | cut -c1-8) \
jitter_check.py $(md5sum < $T/physics_solve/jitter_check.py | cut -c1-8) input md5 $(md5sum < $P | cut -c1-8)"
  echo "args: $COMMON $EXTRA"; } > $O/run.log
cd $FCD; t0=$(date +%s)
$FPY $T/physics_solve/solve.py $P $OUTP $COMMON $EXTRA > $O/solve.out 2>&1; echo "solve rc=$? $(( $(date +%s) - t0 )) s" >> $O/run.log
cp ${OUTP%.parquet}_solve.json ${OUTP%.parquet}_solve.log ${OUTP%.parquet}_solve.npz $O/ 2> /dev/null
$FPY $T/trace_rollout.py zero $O/zero.npz $OUTP $N > $O/zero.log 2>&1; echo "zero replay rc=$?" >> $O/run.log
$BPY $T/trace_score.py $OUTP $O/zero.npz:zero_action ${OUTP%.parquet}_solve.npz:truth >> $O/run.log 2>&1
$BPY -c "
import numpy as np; a = np.load('$O/zero.npz'); b = np.load('${OUTP%.parquet}_solve.npz'); n = min(len(a['q']), len(b['q']))
print('replay vs solver truth: frames', n, 'max |dq|', float(np.abs(a['q'][:n].astype(np.float64) - b['q'][:n].astype(np.float64)).max()),
      'bit-identical', bool(np.array_equal(a['q'][:n], b['q'][:n])))" >> $O/run.log 2>&1
grep -a "bit-identical to the truth" $O/solve.out | cut -c1-200 >> $O/run.log
t1=$(date +%s); $FPY $T/physics_solve/jitter_check.py $OUTP --device cpu --k 17 --seed 0 --json $O/jitter.json --out $O/jitter.npz > $O/jitter.log 2>&1
echo "jitter rc=$? $(( $(date +%s) - t1 )) s: $(tail -1 $O/jitter.log | cut -c1-300)" >> $O/run.log
echo "$(date -u +%FT%TZ) DONE" >> $O/run.log; tail -7 $O/run.log
