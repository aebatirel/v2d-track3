"""Per-object error of a recorded rollout (tools/trace_rollout.py npz) against OUR reference, over time (2026-10-30,
physics study). No ground truth. Prints, per object: position error (cm) and rotation error (deg) at a few frames, the
first frame the object is > 3 cm off, the share of frames within 3 cm, and the final error.
Usage: trace_objects.py REF.parquet TRACE.npz [TRACE.npz ...]"""
import sys
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
for path in sys.argv[2:]:
    d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'][:T].astype(float); n = len(q)
    print(f'== {path}  ({n} of {T} frames)')
    for j, nm in enumerate(names):
        i = next(k for k, l in enumerate(L) if l.startswith(f'track3_{nm}/') or l.split('/')[0].endswith(nm))
        dp = 100 * np.linalg.norm(q[:, i, :3] - OP[:n, j], axis=1)
        dr = np.degrees((Rot.from_quat(q[:, i, 3:7]) * Rot.from_quat(OQ[:n, j]).inv()).magnitude())
        moved = 100 * np.linalg.norm(OP[:, j] - OP[:1, j], axis=1).max()
        off = np.nonzero(dp > 3)[0]
        marks = [f for f in (0, n // 4, n // 2, 3 * n // 4, n - 1)]
        print(f'  {nm:18s} ref moves {moved:5.1f} cm | within 3 cm {100 * (dp <= 3).mean():5.1f} % | first >3 cm '
              f'{off[0] if len(off) else "-":>4} | ' + ' '.join(f'f{f}:{dp[f]:.1f}cm/{dr[f]:.0f}d' for f in marks))
