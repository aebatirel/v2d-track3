#!/bin/sh
# E3 spin test: prior = GT + small AR(1) noise + constant spin error about the symmetry axis; spin hypotheses on
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
for e in 21 12; do
  for sp in 90 180; do
    PRIOR=gt PN=5,3,0.95 SPIN=$sp SPINHYP=1 GTFRESH=1 TAG=_s$sp venv17/bin/python c/trk17.py $e > c/trk_${e}_s$sp.log 2>&1
    venv17/bin/python c/ev17.py c/trk_${e}_s$sp.npz > c/ev_${e}_s$sp.txt 2>&1
  done
done
echo done > c/run3.done
