"""A reference parquet's object track -> pipeline/score_registered.py's perception npz (name -> (T, 4, 4) world poses),
so the reference itself can be scored against mocap (public episodes, evaluation only). Usage: ref_to_npz.py REF OUT.npz"""
import sys
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
t = pq.read_table(sys.argv[1]); g = lambda c: t.column(c)[0].as_py()  # noqa: E731
names = g('object_body_names'); B = len(names); T = len(g('robot_left_wrist_position'))
OP = np.array(g('object_body_position'), float).reshape(T, B, 3); OQ = np.array(g('object_body_wxyz'), float).reshape(T, B, 4)
out = {}
for j, n in enumerate(names):
    M = np.tile(np.eye(4), (T, 1, 1)); M[:, :3, :3] = R.from_quat(OQ[:, j][:, [1, 2, 3, 0]]).as_matrix(); M[:, :3, 3] = OP[:, j]; out[n] = M
np.savez(sys.argv[2], **out)
