#!/bin/sh
# Stage C resume (2026-10-07 ~07:50): fresh-holdout tracker runs on eps 13 (blue_cup+rack) and 22 (blue_cup+pitcher).
# Detector models trained once on the 5 stage-B eps (12/26/21/0/31); 13/22 never in training. Order: E2 h10, E3 s90, E1 v2.
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
P=c/run4.progress
echo "start $(date +%T)" > $P
venv17/bin/python c/train_loeo.py 13 22 > c/train_hold.log 2>&1; echo "train $(date +%T)" >> $P
for e in 13 22; do
  PRIOR=gt PN=10,5,0.95 TAG=_h10 venv17/bin/python c/trk17.py $e > c/trk_${e}_h10.log 2>&1
  venv17/bin/python c/ev17.py c/trk_${e}_h10.npz > c/ev_${e}_h10.txt 2>&1; echo "$e h10 $(date +%T)" >> $P
done
for e in 13 22; do
  PRIOR=gt PN=5,3,0.95 SPIN=90 SPINHYP=1 GTFRESH=1 TAG=_s90 venv17/bin/python c/trk17.py $e > c/trk_${e}_s90.log 2>&1
  venv17/bin/python c/ev17.py c/trk_${e}_s90.npz > c/ev_${e}_s90.txt 2>&1; echo "$e s90 $(date +%T)" >> $P
done
for e in 13 22; do
  TAG=_v2 venv17/bin/python c/trk17.py $e > c/trk_${e}_v2.log 2>&1
  venv17/bin/python c/ev17.py c/trk_${e}_v2.npz > c/ev_${e}_v2.txt 2>&1; echo "$e v2 $(date +%T)" >> $P
done
echo done > c/run4.done
