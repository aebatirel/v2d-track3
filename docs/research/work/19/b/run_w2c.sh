#!/bin/bash
# B27: coarse-grid W2 (h 2/3 mm) as a decimation that keeps raw-MC topology (no edge collapses).
PY=/Users/aebatirel/Documents/Code/v2d-research/work/19/venv/bin/python
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
for n in white_pot_lid white_pot plastic_dish_rack blue_cup; do
 for hd in "2 0.3" "2 0.6" "3 0.6" "3 1.0"; do set -- $hd
  [ -f W2c/${n}_h$1_d$2.npz ] || $PY b_remesh2.py $n $1 $2 3 W2c/${n}_h$1_d$2.npz 2>&1 | cut -c1-330 >> logs/remesh_W2c.out
 done
done
