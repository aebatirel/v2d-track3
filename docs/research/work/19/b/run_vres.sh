#!/bin/bash
# B25 diagnostic: W2 meshes with forced voxel preprocessing at resolution 25 / 100 (V2 = 50), threshold 0.05.
PY=/Users/aebatirel/Documents/Code/v2d-research/work/19/venv/bin/python
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
for n in white_pot_lid white_pot plastic_dish_rack; do
 for r in 100 25; do
  [ -f V2r$r/$n.npz ] && continue
  $PY b_decomp.py W2/$n.npz V2r$r/$n.npz 0.05 on $r > logs/V2r${r}_$n.log 2>&1
 done
done
echo DONE >> logs/V2res.done
