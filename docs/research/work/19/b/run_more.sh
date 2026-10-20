#!/bin/bash
# B26: exact FlashCHORD call for the four objects stage B did not cover.
# V0x = scan as newton loads it (pitcher, dust pan; boards V0 = 15-verify/hulls11); V1w = position-welded closed mesh
# (dust pan, boards; passes the manifold check per B9); V1 = W2 (pitcher).
PY=/Users/aebatirel/Documents/Code/v2d-research/work/19/venv/bin/python
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
run(){ [ -f $2 ] || $PY b_decomp.py $1 $2 > $3 2>&1; }
run scan:mini_dust_pan V0x/mini_dust_pan.npz logs/V0x_mini_dust_pan.log
run WELD/mini_dust_pan.npz V1w/mini_dust_pan.npz logs/V1w_mini_dust_pan.log
run WELD/wooden_piece_1.npz V1w/wooden_piece_1.npz logs/V1w_wooden_piece_1.log
run WELD/wooden_piece_2.npz V1w/wooden_piece_2.npz logs/V1w_wooden_piece_2.log
run scan:water_pitcher V0x/water_pitcher.npz logs/V0x_water_pitcher.log
while [ ! -f W2/water_pitcher.npz ]; do sleep 20; done
run W2/water_pitcher.npz V1/water_pitcher.npz logs/V1_water_pitcher.log
echo DONE > logs/run_more.done
