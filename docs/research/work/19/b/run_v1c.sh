#!/bin/bash
# B27: exact FlashCHORD call on the coarse-grid W2 meshes (h2_d0.6 for all four; h3_d1.0 for lid and rack).
PY=/Users/aebatirel/Documents/Code/v2d-research/work/19/venv/bin/python
cd /Users/aebatirel/Documents/Code/v2d-research/work/19/b
for v in white_pot_lid_h2_d0.6 blue_cup_h2_d0.6 white_pot_h2_d0.6 plastic_dish_rack_h2_d0.6 white_pot_lid_h3_d1.0 plastic_dish_rack_h3_d1.0; do
  [ -f V1c/$v.npz ] || $PY b_decomp.py W2c/$v.npz V1c/$v.npz > logs/V1c_$v.log 2>&1
done
echo DONE > logs/run_v1c.done
