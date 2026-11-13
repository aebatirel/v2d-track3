#!/bin/bash
# Development runs on public ep31 (NOT the test episode): pick GRASP-mode settings at the CPU budget before the ep13
# pre-registration. One config per call. Usage: S=<scratchpad> dev_ep31.sh TAG [solve args...]
# Fixed: 4 workers x 32 worlds (N 32 candidates x K 4 robust copies), H 16, knot 4, commit 4, 8 rollout batches per replan,
# optimisation on frames 16..48 only (--f0 16 --stop 48), no rollbacks, seed 0. Dev metric: per-replan J_best / J_warm.
set -u; S=${S:?}; TAG=$1; shift
FCD=$S/src/video_to_data/robotic_grounding/flash_chord; P=$(ls $S/inputs/ep31_P/processed/*/*/ref_in.parquet)
O=$S/dev/$TAG; mkdir -p $O; cp $P $O/ref_in.parquet 2> /dev/null; mkdir -p $O/x; D=$(dirname $P)
cd $FCD; export OMP_NUM_THREADS=1 EMB=sharpa_hands_mid
echo "$(date -u +%FT%TZ) code $(git -C /home/user/v2d-track3 rev-parse --short HEAD)+wip solve.py $(md5sum < /home/user/v2d-track3/tools/physics_solve/solve.py | cut -c1-8) grasp_window.py $(md5sum < /home/user/v2d-track3/tools/physics_solve/grasp_window.py | cut -c1-8) args [$*]" > $O/run.log
t0=$(date +%s)
$S/fcvenv/bin/python /home/user/v2d-track3/tools/physics_solve/solve.py $P $D/dev_$TAG.parquet --workers 4 --worlds 32 --robust 4 \
  --horizon 16 --knot 4 --ctrl 4 --iters 8 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.80 \
  --retries 0 --seed 0 --f0 16 --stop 48 "$@" > $O/solve.out 2>&1; echo "rc=$? $(( $(date +%s) - t0 )) s" >> $O/run.log
mv $D/dev_${TAG}_solve.json $D/dev_${TAG}_solve.log $O/ 2> /dev/null
$S/venv/bin/python - $O/dev_${TAG}_solve.json >> $O/run.log << 'PY'
import json, sys, numpy as np
d = json.load(open(sys.argv[1])); r = [x for x in d['replans'] if 'J_best' in x]
ratio = [x['J_best'] / x['J_warm'] for x in r]
print(f"dev: {len(r)} active replans, mean J_best/J_warm {np.mean(ratio):.4f}, improved {sum(q < 0.999 for q in ratio)}/{len(r)}, "
      f"mean real obj cost {np.mean([x['real_obj_cost'] for x in r]):.5f}, final ADD cm {r[-1]['add_cm']}, wall {d['wall_s']} s")
PY
tail -2 $O/run.log
