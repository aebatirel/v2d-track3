#!/bin/bash
# stage B resume: fresh-holdout detector on eps 13/22 (waits for chain5's census), models trained on eps 12 26 21 0 31
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
PY=/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python; PYS=/Users/aebatirel/Documents/Code/v2d-research/work/17/venv17/bin/python
for e in 13 22; do
  while [ ! -f out/census_$e.npz ]; do sleep 20; done
  [ -f out/det_$e.npz ] || $PY -u det17run.py $e 3 > out/det_$e.log 2>&1
  [ -f out/feat2_$e.npy ] || $PY featpass.py $e >> out/featpass_hold.log 2>&1
  echo "det $e done $(date)" >> out/chain6.progress
done
$PYS -u det17score_hold.py "12 26 21 0 31" 13 22 > out/score_hold.log 2>&1
$PY det17eval.py 13 22 > out/det_eval_hold_thr05.txt 2>&1
$PY guided_learned.py 15 0.05 13 22 > out/guided_learned_hold.txt 2>&1
THR=0.3 $PY shift_obj.py 13 22 > out/shift_obj_hold.txt 2>&1
echo "CHAIN6 DONE $(date)" >> out/chain6.progress
