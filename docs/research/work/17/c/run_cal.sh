#!/bin/sh
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
for e in 0 12 26 21; do venv17/bin/python c/calib17.py $e 2 14 > c/calib_$e.log 2>&1; done
venv17/bin/python c/ev17.py c/trk_21_v1.npz > c/ev_21_v1.txt 2>&1
echo done > c/run_cal.done
