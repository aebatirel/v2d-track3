#!/bin/sh
# verifier reruns (read-only use of work/17 code; outputs in 17-verify/run/c)
cd /Users/aebatirel/Documents/Code/v2d-research/work/17-verify/run
PY=/Users/aebatirel/Documents/Code/v2d-research/work/17/venv17/bin/python
S=/Users/aebatirel/Documents/Code/v2d-research/work/17/c
P=../chain_v.progress; echo "start $(date +%T)" > $P
TAG=_vfy $PY $S/trk17.py 22 > c/trk_22_vfy.log 2>&1; echo "22 v2 $(date +%T)" >> $P
$PY $S/ev17.py c/trk_22_vfy.npz > c/ev_22_vfy.txt 2>&1
PRIOR=gt PN=10,5,0.95 TAG=_h10vfy $PY $S/trk17.py 13 > c/trk_13_h10vfy.log 2>&1; echo "13 h10 $(date +%T)" >> $P
$PY $S/ev17.py c/trk_13_h10vfy.npz > c/ev_13_h10vfy.txt 2>&1
$PY $S/ev_carry2.py c/trk_13_h10vfy.npz > c/carry_13_h10vfy.txt 2>&1
echo done >> $P
