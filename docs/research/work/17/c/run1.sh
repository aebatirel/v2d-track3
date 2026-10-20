#!/bin/sh
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
for e in 12 0 21 26; do
  [ -f c/clf_$e.pkl ] || venv17/bin/python c/train_loeo.py $e
  TAG=_v1 venv17/bin/python c/trk17.py $e > c/trk_${e}_v1.log 2>&1
  venv17/bin/python c/ev17.py c/trk_${e}_v1.npz > c/ev_${e}_v1.txt 2>&1
  MODE=regD venv17/bin/python c/ev17.py c/trk_${e}_v1.npz >> c/ev_${e}_v1.txt 2>&1
done
echo done > c/run1.done
