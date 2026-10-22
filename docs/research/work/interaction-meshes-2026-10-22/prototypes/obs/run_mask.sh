#!/bin/bash
S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad; O=$S/interact/obs; PY=$S/venv/bin/python; L=/home/user/v2d-track3/meshes; cd $O
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for b in wooden_piece_1 wooden_piece_2; do
nohup $PY -I $O/maskfuse.py --obj $b --grid $O/grids2/${b}_e2324_nobc.npz --mesh $L/library_v4/$b.glb --out $O/grids2/${b}_mask.npz \
 --ep $O/depth/ep23_s2_poses.npz $O/depth/ep23_s2.npy $S/loc/v/ep23_c.mp4 \
 --ep $O/depth/ep24_s2_poses.npz $O/depth/ep24_s2.npy $O/v/ep24_c.mp4 > $O/grids2/${b}_mask.log 2>&1 < /dev/null &
echo $! >> $O/grids2/pids
done
V=12_fill_g0_f0_bin,4_fill_g0_f0_cont,4_adj_g2_f0_cont,6_adj_g2_f0_cont,4c12_adj_g2_f0_cont,6c12_adj_g2_f0_cont
nohup $PY -I $O/obspost2.py $O/grids2/dustpan_e394018.npz $O/out2/dustpan $V > $O/out2/dustpan.post.log 2>&1 < /dev/null &
