#!/bin/sh
# verifier robustness runs: init/noise seeds and a fine init for E1; noise seed for E2 h10. Waits for chain_v.
cd /Users/aebatirel/Documents/Code/v2d-research/work/17-verify/run
PY=/Users/aebatirel/Documents/Code/v2d-research/work/17/venv17/bin/python
S=/Users/aebatirel/Documents/Code/v2d-research/work/17/c
P=../chain_v2.progress; echo "wait $(date +%T)" > $P
while ! grep -q done ../chain_v.progress; do sleep 10; done
echo "start $(date +%T)" >> $P
for spec in "22 SEED=1 _v2s1" "22 IP=5,2 _v2ip5" "13 SEED=1 _v2s1" "13 IP=5,2 _v2ip5"; do
  set -- $spec; e=$1; tg=$3
  env $2 TAG=$tg $PY $S/trk17.py $e > c/trk_${e}${tg}.log 2>&1; $PY $S/ev17.py c/trk_${e}${tg}.npz > c/ev_${e}${tg}.txt 2>&1; echo "$e $tg $(date +%T)" >> $P
done
for e in 13 22; do
  SEED=1 PRIOR=gt PN=10,5,0.95 TAG=_h10s1 $PY $S/trk17.py $e > c/trk_${e}_h10s1.log 2>&1
  $PY $S/ev17.py c/trk_${e}_h10s1.npz > c/ev_${e}_h10s1.txt 2>&1; $PY $S/ev_carry2.py c/trk_${e}_h10s1.npz > c/carry_${e}_h10s1.txt 2>&1; echo "$e h10s1 $(date +%T)" >> $P
done
echo done >> $P
