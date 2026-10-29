"""DIAGNOSTIC (uses a GT-consistent pose from depen6.py): in a localised grasp-lock INPUT tree, set OBJ's pose to POSE
for frames < MOVE and blend into the original path over BLEND frames (position lerp, rotation slerp).
Usage: setstart.py TREE OBJ DEPEN6_JSON KEY MOVE [BLEND=10]"""
import sys, glob, json, numpy as np, pyarrow as pa, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R, Slerp
tree, o, js, key, mv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]); bl = int(sys.argv[6]) if len(sys.argv) > 6 else 10
p = glob.glob(f'{tree}/processed/*/*/ref_sf.parquet')[0]; t = pq.read_table(p)
names = t.column('object_body_names')[0].as_py(); B = len(names); T = len(t.column('robot_left_wrist_position')[0].as_py()); j = names.index(o)
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
pz = json.load(open(js))[key]['pose']; P0, Q0 = np.array(pz[:3]), np.array(pz[3:7])
for f in range(min(T, mv + bl)):
    if f < mv:
        OP[f, j], OQ[f, j] = P0, Q0
    else:
        w = (f - mv + 1) / (bl + 1); OP[f, j] = (1 - w) * P0 + w * OP[f, j]; OQ[f, j] = Slerp([0, 1], R.from_quat([Q0, OQ[f, j]]))([w]).as_quat()[0]
t = t.set_column(t.column_names.index('object_body_position'), 'object_body_position', pa.array([OP.tolist()], type=t.schema.field('object_body_position').type))
t = t.set_column(t.column_names.index('object_body_wxyz'), 'object_body_wxyz', pa.array([OQ[..., [3, 0, 1, 2]].tolist()], type=t.schema.field('object_body_wxyz').type))
pq.write_table(t, p); print('set', o, 'frames <', mv, 'blend', bl, 'in', p)
