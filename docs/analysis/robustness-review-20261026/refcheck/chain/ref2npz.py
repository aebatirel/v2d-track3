"""Convert the object path of a FlashCHORD reference parquet into a poses_world_vo.npz-style file (refcheck/chain).

A FlashCHORD reference parquet (mkref output e2s_reference.parquet, or the processed/ parquet after contact retarget)
holds one row; object_body_names (B), object_body_position (T, B, 3) and object_body_wxyz (T, B, 4) are the body poses
in mkref's TABLE frame (z = table normal, table top at TABLE_Z, xy origin under the objects). The body frame is the
tracking mesh's frame (verified in refcheck/resolve/verify_feed.py: R_t = A W_t with B = identity, residual 0.001 mm).
The table frame differs from the perception world frame (rectified-left camera at frame 0) by one rigid transform per
episode, which the kit's frame-0 scene alignment removes; per-object z snaps / overlap lifts are NOT removed (they are
part of what mkref does to the object path). Output: one (T, 4, 4) array per object name, like poses_world_vo.npz.
No ground truth is read. Usage: python -I ref2npz.py REF.parquet OUT.npz
"""
import sys
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

src, out = sys.argv[1], sys.argv[2]
t = pq.read_table(src, columns=['object_body_names', 'object_body_position', 'object_body_wxyz', 'fps'])
names = t.column('object_body_names')[0].as_py()
pos = np.array(t.column('object_body_position')[0].as_py(), float)          # T, B, 3
wxyz = np.array(t.column('object_body_wxyz')[0].as_py(), float)            # T, B, 4
assert pos.shape[:2] == wxyz.shape[:2] and pos.shape[1] == len(names), (pos.shape, wxyz.shape, names)
arr = {}
for i, n in enumerate(names):
    M = np.tile(np.eye(4), (len(pos), 1, 1))
    q = wxyz[:, i] / np.linalg.norm(wxyz[:, i], axis=1, keepdims=True)
    M[:, :3, :3] = Rot.from_quat(q[:, [1, 2, 3, 0]]).as_matrix()
    M[:, :3, 3] = pos[:, i]
    arr[n] = M
np.savez(out, **arr, _names=np.array(names), _fps=np.array(t.column('fps')[0].as_py()))
print(out, names, pos.shape, 'fps', t.column('fps')[0].as_py())
