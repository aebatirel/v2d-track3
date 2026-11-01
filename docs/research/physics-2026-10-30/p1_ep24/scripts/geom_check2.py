"""Lowest point of library_v3 boards and of the r0 piece union at the reference poses; body axes in world; hand distances.
Usage: geom_check2.py REF.parquet R0_DIR LIB_DIR"""
import sys, glob
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
ref, r0, lib = sys.argv[1:4]
row = pq.read_table(ref).to_pylist()[0]
P = np.array(row['object_body_position']); Q = np.array(row['object_body_wxyz'])[..., [1, 2, 3, 0]]
names = list(row['object_body_names'])
pc = {n: np.vstack([trimesh.load(f, force='mesh').vertices for f in sorted(glob.glob(f'{r0}/{n}/piece_*.obj'))]) for n in names}
lb = {n: np.asarray(trimesh.load(f'{lib}/{n}.glb', force='mesh').vertices) for n in names}
RJ = np.array(row['mano_right_joints']); LJ = np.array(row['mano_left_joints'])
def low(V, f, k):
    return (V @ R.from_quat(Q[f, k]).as_matrix().T + P[f, k])[:, 2].min()
def handdist(V, f, k, J):
    W = V @ R.from_quat(Q[f, k]).as_matrix().T + P[f, k]
    from scipy.spatial import cKDTree
    return cKDTree(W).query(J[f])[0].min()
print('frame | pieces low-table mm (b1,b2) | library low-table mm (b1,b2) | body axes in world (b1: x,y,z -> world z comp) | min hand-kp dist to pieces mm R,L (b1; b2)')
for f in list(range(0, 275, 20)) + [218, 246, 274]:
    s = f'f{f:3d} | ' + ' '.join(f'{(low(pc[n], f, k) - 0.6) * 1e3:6.1f}' for k, n in enumerate(names))
    s += ' | ' + ' '.join(f'{(low(lb[n], f, k) - 0.6) * 1e3:6.1f}' for k, n in enumerate(names))
    s += ' | ' + ' '.join(str(np.round(R.from_quat(Q[f, k]).as_matrix()[2], 2)) for k in range(2))
    s += ' | ' + ' ; '.join(f'{handdist(pc[n], f, k, RJ) * 1e3:5.0f},{handdist(pc[n], f, k, LJ) * 1e3:5.0f}' for k, n in enumerate(names))
    print(s)
