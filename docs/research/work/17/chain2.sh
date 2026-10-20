#!/bin/bash
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
PY=/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python
for e in 21 0; do $PY reg17.py $e 3 2>&1 | grep -v Warn > out/reg_$e.log; done
for e in 26 21 0; do $PY reg2.py $e 15 1 2>&1 | grep -v Warn > out/reg2_$e.log; done
echo CHAIN2 DONE > out/chain2.done
