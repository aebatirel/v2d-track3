#!/bin/bash
# stage B resume: ep 41 (pot only) multi-start registration (s24 failed), then reg2 (no LOMO) + census
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
PY=/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python
e=41
[ -f out/reg_$e.json ] || ($PY -u reg17ms.py $e 3 2>&1 | grep --line-buffered -v Warn > out/reg_$e.log)
echo "ep $e reg17ms: $(grep -E 'final|best' out/reg_$e.log | tail -2 | tr '\n' ' ') $(date)" >> out/chain8.progress
[ -f out/reg_$e.json ] && { [ -f out/reg2_$e.json ] || ($PY -u reg2.py $e 15 0 2>&1 | grep --line-buffered -v Warn > out/reg2_$e.log); }
[ -f out/reg2_$e.json ] && { [ -f out/census_$e.npz ] || $PY census17.py $e > out/census_$e.log 2>&1; }
echo "CHAIN8 DONE $(date)" >> out/chain8.progress
