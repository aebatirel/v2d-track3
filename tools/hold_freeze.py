"""Keep the carrier hand on an object to the end, on an existing (packed) grasp-lock reference (2 Nov 2026,
perfect-following lane; docs/research/work/pf-release-20261102/PREREG_B.md). GT-free.

From frame FROM to the end, the robot hand SIDE's wrist pose, finger joints and frame poses are held at their values of
frame FROM-1 (the last frame of the hold, the hand still closed on the object). Use it only where our reference keeps the
object still after the release (eval 16: the spoon moves <= 1 cm per 4 frames from f107 on), so a hand frozen in place
keeps holding it where the reference says it rests. Object poses, the other hand and every other column are unchanged;
robot-hand tracks are not scored.
Usage: hold_freeze.py IN.parquet OUT.parquet --side right --from 107
"""
import argparse
import numpy as np, pyarrow as pa, pyarrow.parquet as pq

ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out')
ap.add_argument('--side', required=True, choices=['left', 'right']); ap.add_argument('--from', dest='f0', type=int, required=True)
a = ap.parse_args()
t = pq.read_table(a.inp); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
assert 0 < a.f0 < T
for c in (f'robot_{a.side}_wrist_position', f'robot_{a.side}_wrist_wxyz', f'robot_{a.side}_finger_joints', f'robot_{a.side}_frames'):
    v = np.array(t.column(c)[0].as_py(), float); sh = v.shape; v = v.reshape(T, -1)
    v[a.f0:] = v[a.f0 - 1]
    i = t.column_names.index(c); t = t.set_column(i, c, pa.array([v.reshape(sh).tolist()], type=t.schema.field(c).type))
    print(c, 'frozen from', a.f0, 'at frame', a.f0 - 1)
pq.write_table(t, a.out)
