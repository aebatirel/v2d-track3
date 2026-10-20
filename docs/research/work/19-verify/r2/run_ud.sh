#!/bin/zsh
cd /Users/aebatirel/Documents/Code/v2d-research/work/19
PY=venv/bin/python; S=../19-verify/r2
$PY $S/y_ud.py REC=c2/REC > $S/y_ud_REC.out 2>&1
$PY $S/y_ud.py V1=b/V1,b/V1w > $S/y_ud_V1.out 2>&1
$PY $S/y_ud.py V0=../15-verify/hulls11 > $S/y_ud_V0.out 2>&1
$PY $S/y_ud.py V2=b/V2 > $S/y_ud_V2.out 2>&1
$PY $S/y_ud.py S60r120=b/MIX_S60r120 > $S/y_ud_S60r120.out 2>&1
echo done > $S/run_ud.done
