#!/bin/zsh
# Union depth (verifier round-2 estimator, unchanged) on the MuJoCo-capped hull sets.
cd /Users/aebatirel/Documents/Code/v2d-research/work/19
PY=venv/bin/python; S=../19-verify/r2
for L in REC V1 V0 S60r120; do
  [ -f c3/logs/ud_cap_$L.out ] && grep -q 'ep31 f238' c3/logs/ud_cap_$L.out && continue
  $PY $S/y_ud.py ${L}cap=c3/cap/$L > c3/logs/ud_cap_$L.out 2>&1
done
echo done > c3/logs/ud_cap.done
