#!/bin/bash
# B26: W2 watertight remesh (1 mm grid, iso +0.3 mm, 3 mm shell) for the four objects stage B did not cover,
# then field grids (FG) for contact mining.
PY=/Users/aebatirel/Documents/Code/v2d-research/work/19/venv/bin/python
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
for n in mini_dust_pan wooden_piece_1 wooden_piece_2 water_pitcher; do
  [ -f W2/$n.npz ] || $PY b_remesh2.py $n 1 0.3 3 W2/$n.npz >> logs/remesh_W2_more.out 2>&1
  [ -f FG/$n.npz ] || $PY b_fgrid.py $n >> logs/fgrid_more.out 2>&1
done
echo DONE >> logs/remesh_W2_more.out
