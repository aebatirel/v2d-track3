#!/bin/sh
# E1 free-running v2 (scan catalogue), then E2 hybrid emulation at two prior-noise levels
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
for e in 12 0 21 26; do
  TAG=_v2 venv17/bin/python c/trk17.py $e > c/trk_${e}_v2.log 2>&1
  venv17/bin/python c/ev17.py c/trk_${e}_v2.npz > c/ev_${e}_v2.txt 2>&1
done
for e in 12 0 21 26; do
  for pn in 10,5,0.95 20,10,0.95; do
    tg=_h$(echo $pn | cut -d, -f1)
    PRIOR=gt PN=$pn TAG=$tg venv17/bin/python c/trk17.py $e > c/trk_${e}${tg}.log 2>&1
    venv17/bin/python c/ev17.py c/trk_${e}${tg}.npz > c/ev_${e}${tg}.txt 2>&1
  done
done
echo done > c/run2.done
