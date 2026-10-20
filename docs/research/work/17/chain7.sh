#!/bin/bash
# stage B resume: pot-only holdout ep(s) with s24 init; waits for chain5; reg17 then reg17ms fallback; reg2 (no LOMO); census
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
PY=/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python
while ! grep -q CHAIN5 out/chain5.progress 2>/dev/null; do sleep 20; done
for e in "$@"; do
  [ -f out/vo_public_$e.npy ] || $PY vo17.py $e > out/vo_$e.log 2>&1
  [ -f out/apnp_$e.npz ] || $PY a_pnp.py $e 4 > out/apnp_$e.log 2>&1
  [ -f out/sync_$e.json ] || $PY sync_fit.py $e > out/sync_$e.log 2>&1
  [ -f out/reg_$e.json ] || ($PY -u reg17.py $e 3 2>&1 | grep --line-buffered -v Warn > out/reg_$e.log)
  echo "ep $e reg17 $(tail -1 out/reg_$e.log | head -c 200) $(date)" >> out/chain7.progress
  [ -f out/reg2_$e.json ] || ($PY -u reg2.py $e 15 0 2>&1 | grep --line-buffered -v Warn > out/reg2_$e.log)
  [ -f out/census_$e.npz ] || $PY census17.py $e > out/census_$e.log 2>&1
  echo "ep $e done $(date)" >> out/chain7.progress
done
echo "CHAIN7 DONE $(date)" >> out/chain7.progress
