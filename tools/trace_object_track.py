"""How well objects follow their reference path in a recorded rollout (tools/trace_rollout.py npz): per object the
error per frame, share of frames within 3 cm, max lift vs the reference, and the first frame the object is > 10 cm off
after the reference starts moving it. No ground truth. Usage: trace_object_track.py REF.parquet TRACE.npz[:label] ..."""
import sys
import numpy as np, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py()
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
for spec in sys.argv[2:]:
    path, _, lab = spec.partition(':'); d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q']
    for j, n in enumerate(names):
        b = next(i for i, l in enumerate(L) if l.startswith(f'track3_{n}/')); k = min(T, len(q))
        a = q[:k, b, :3]; r = OP[:k, j]; e = np.linalg.norm(a - r, axis=1)
        mv = np.nonzero(np.linalg.norm(r - r[0], axis=1) > 0.03)[0]; s0 = int(mv[0]) if len(mv) else 0; lost = np.nonzero(e[s0:] > 0.10)[0]
        print(f'{lab or path:12s} {n:13s} within 3 cm {100 * (e < 0.03).mean():5.1f}%  mean err {100 * e.mean():5.1f} cm  '
              f'lift {100 * (a[:, 2] - a[0, 2]).max():5.1f} cm (ref {100 * (r[:, 2] - r[0, 2]).max():4.1f})  lost at {s0 + int(lost[0]) if len(lost) else None}/{k}'
              f'  err cm every 30f {np.round(100 * e[::30], 1).tolist()}')
