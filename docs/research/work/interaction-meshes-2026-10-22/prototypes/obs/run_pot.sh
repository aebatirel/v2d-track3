#!/bin/bash
# white_pot, one grid per episode (summed in the post-pass): eps 41, 44, 2, 27, stride 2, our own meshes as --others
S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad; O=$S/interact/obs; PY=$S/venv/bin/python; L=/home/user/v2d-track3/meshes; cd $O
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
declare -A OTH=([41]=- [44]=- [2]=white_pot_lid=$L/library_v2/white_pot_lid.glb [27]=plastic_dish_rack=$L/library_v2/plastic_dish_rack.glb)
for e in ${EPS:-41 44 2 27}; do
nohup $PY -I $O/obsfuse2.py --obj white_pot --out $O/grids2/pot_ep$e.npz --roi $L/library_v2/white_pot.glb \
 --ep $S/loc/perc/ep$e/poses.npz $S/loc/depth/ep$e/depths_fs0.5.npy $S/loc/refs/ep$e/hands.npz 2 ${OTH[$e]} > $O/grids2/pot_ep$e.log 2>&1 < /dev/null &
echo $! >> $O/grids2/pids
done
