#!/bin/bash
# run_solve.sh TAG [solve args...] : physics solve on the ref_in.parquet of scratchpad/phys/solve/TAG, then the official
# zero-action replay (tools/trace_rollout.py zero) and sim_vs_ref (tools/trace_score.py). CPU, no ground truth.
S=${S:?set S to the scratchpad dir (phys/solve/TAG/processed/<seq>/<robot>/ref_in.parquet, fcvenv, venv, dl/kit)}; TAG=$1; shift
D=$(ls -d $S/phys/solve/$TAG/processed/*/*); FCD=$S/src/video_to_data/robotic_grounding/flash_chord
cd $FCD; export OMP_NUM_THREADS=1 EMB=sharpa_hands_mid
echo "$(date -u +%FT%TZ) code $(git -C /home/user/v2d-track3 rev-parse --short HEAD)+wip solve.py md5 $(md5sum /home/user/v2d-track3/tools/physics_solve/solve.py | cut -c1-8) args [$*]" > $S/phys/solve/$TAG/run.log
start=$(date +%s)
$S/fcvenv/bin/python /home/user/v2d-track3/tools/physics_solve/solve.py $D/ref_in.parquet $D/ref_ps.parquet "$@" > $S/phys/solve/$TAG/solve.out 2>&1 || { echo SOLVE_FAIL >> $S/phys/solve/$TAG/run.log; exit 1; }
echo "SOLVE_S $(( $(date +%s) - start ))" >> $S/phys/solve/$TAG/run.log
N=$($S/fcvenv/bin/python -c "import pyarrow.parquet as pq; print(len(pq.read_table('$D/ref_in.parquet').column('robot_left_wrist_position')[0].as_py()))")
DEV=cpu $S/fcvenv/bin/python /home/user/v2d-track3/tools/trace_rollout.py zero $S/phys/solve/$TAG/zero_ps.npz $D/ref_ps.parquet $N > $S/phys/solve/$TAG/zero.log 2>&1 || { echo ZERO_FAIL >> $S/phys/solve/$TAG/run.log; exit 1; }
KIT=$S/dl/kit/x/v2d_submission_kit $S/venv/bin/python /home/user/v2d-track3/tools/trace_score.py $D/ref_ps.parquet $S/phys/solve/$TAG/zero_ps.npz:zero_ps $D/ref_ps_solve.npz:truth >> $S/phys/solve/$TAG/run.log 2>&1
echo "ELAPSED $(( $(date +%s) - start )) s" >> $S/phys/solve/$TAG/run.log; echo "$(date -u +%FT%TZ) DONE" >> $S/phys/solve/$TAG/run.log
