#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad; O=$S/interact/obs; PY=$S/venv/bin/python; L=/home/user/v2d-track3/meshes; cd $O
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for pair in "wooden_piece_1 wooden_piece_2" "wooden_piece_2 wooden_piece_1"; do set -- $pair
nohup $PY -I $O/obsfuse2.py --obj $1 --out $O/grids2/$1_e2324.npz --roi $L/library_v4/$1.glb \
 --ep $O/depth/ep23_s2_poses.npz $O/depth/ep23_s2.npy $O/depth/ep23_s2_hands.npz 1 $2=$L/library_v4/$2.glb \
 --ep $O/depth/ep24_s2_poses.npz $O/depth/ep24_s2.npy $O/depth/ep24_s2_hands.npz 1 $2=$L/library_v4/$2.glb > $O/grids2/$1_e2324.log 2>&1 < /dev/null &
done
nohup $PY -I $O/obsfuse2.py --obj white_pot_lid --out $O/grids2/lid_ep2.npz --roi $L/library_v2/white_pot_lid.glb \
