#!/bin/bash
# clean-up round: rack over T_WALL x CUP_LEAN (pre-registered, work log 2026-10-27)
cd /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
S=/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts
one() { t=$1; l=$2; o=prim/clean/rack/t${t}_lean$l
  PRIM_T_WALL=$(python3 -c "print($t/1000)") PRIM_CUP_LEAN=$l venv/bin/python -W ignore $S/prim_rack.py run --obs_dir obs_all --out $o > $o.log 2>&1 && echo "OK $t $l" || echo "FAIL $t $l"; }
one 2.5 0 & one 2.5 1 & wait
one 1.5 0 & one 1.5 1 & wait
one 4.0 0 & one 4.0 1 & wait
echo RACK-DONE
