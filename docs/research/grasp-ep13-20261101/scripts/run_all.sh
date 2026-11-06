#!/bin/bash
# All pre-registered ep13 arms, one after another (PREREG.md): the inputs' jitter checks, test B (two-hand rebuilds P2,
# O2), test A (the twins' references P, O), then the gate. Usage: S=<scratchpad> GRASP_ARGS="..." run_all.sh
set -u; S=${S:?}; export S GRASP_ARGS=${GRASP_ARGS:?}; H=$(cd "$(dirname "$0")" && pwd); L=$S/ep13/run_all.log; mkdir -p $S/ep13
echo "$(date -u +%FT%TZ) run_all start; GRASP_ARGS [$GRASP_ARGS]" >> $L
bash $H/jitter_inputs.sh >> $L 2>&1
for arm in "P2 anneal" "P2 grasp" "O2 anneal" "O2 grasp" "P anneal" "P grasp" "O anneal" "O grasp"; do
  set -- $arm; [ -s $S/ep13/${1}_$2/jitter.json ] && { echo "skip $arm (done)" >> $L; continue; }
  echo "$(date -u +%FT%TZ) arm $arm" >> $L; bash $H/run_ep13.sh $1 $2 >> $L 2>&1
done
$S/venv/bin/python -I $H/gate.py $S/ep13 $S/inputs $S/ep13/gate.json >> $L 2>&1
echo "$(date -u +%FT%TZ) run_all DONE" >> $L
