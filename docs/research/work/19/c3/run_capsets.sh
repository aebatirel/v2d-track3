#!/bin/zsh
cd /Users/aebatirel/Documents/Code/v2d-research/work/19
PY=venv/bin/python; B=/Users/aebatirel/Documents/Code/v2d-research/work/19
$PY c3/c3_capset.py $B/c3/cap/V0 $B/../15-verify/hulls11
$PY c3/c3_capset.py $B/c3/cap/V1 $B/b/V1,$B/b/V1w
$PY c3/c3_capset.py $B/c3/cap/REC $B/c2/REC
$PY c3/c3_capset.py $B/c3/cap/S60r120 $B/b/MIX_S60r120
echo done > c3/logs/capsets.done
