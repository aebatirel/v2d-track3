#!/bin/bash
# stage B: multi-start registration for eps whose s24 init failed; then reg2 (no LOMO)
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
PY=/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python
for e in "$@"; do
  [ -f out/vo_public_$e.npy ] || $PY vo17.py $e > out/vo_$e.log 2>&1
  [ -f out/apnp_$e.npz ] || $PY a_pnp.py $e 4 > out/apnp_$e.log 2>&1
  [ -f out/sync_$e.json ] || $PY sync_fit.py $e > out/sync_$e.log 2>&1
  [ -f out/reg_$e.json ] || ($PY -u reg17ms.py $e 3 2>&1 | grep --line-buffered -v Warn > out/reg_$e.log)
  [ -f out/reg2_$e.json ] || ($PY -u reg2.py $e 15 0 2>&1 | grep --line-buffered -v Warn > out/reg2_$e.log)
  echo "ep $e done $(date)" >> out/chain4.progress
done
