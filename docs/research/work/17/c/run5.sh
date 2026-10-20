#!/bin/sh
# Stage C resume: spin recovery under a noisier prior (E3 with PN 10,5 and 20,10), eps 21 and 12; waits for run4.
cd /Users/aebatirel/Documents/Code/v2d-research/work/17
P=c/run5.progress; echo "wait $(date +%T)" > $P
while [ ! -f c/run4.done ]; do sleep 20; done
echo "start $(date +%T)" >> $P
for e in 21 12; do
  for pn in 10,5,0.95 20,10,0.95; do
    tg=_s90n$(echo $pn | cut -d, -f1)
    PRIOR=gt PN=$pn SPIN=90 SPINHYP=1 GTFRESH=1 TAG=$tg venv17/bin/python c/trk17.py $e > c/trk_${e}${tg}.log 2>&1
    venv17/bin/python c/ev17.py c/trk_${e}${tg}.npz > c/ev_${e}${tg}.txt 2>&1; echo "$e $tg $(date +%T)" >> $P
  done
done
echo done > c/run5.done
