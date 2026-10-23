"""sim_vs_ref of a recorded rollout (tools/trace_rollout.py npz), with exactly pipeline/qa.py's metric (kit AUC
functions, 500 points on a 5 cm sphere per object, warped to the reference start) and the static floor. Our reference
only (no ground truth). Usage: trace_score.py REF.parquet TRACE.npz[:label] ...   (KIT env = the kit dir, as qa.py)"""
import os, sys
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../pipeline')
import qa  # noqa: E402
sys.path.insert(0, qa.KIT); sys.path.insert(0, f'{qa.KIT}/metric_code/track_3')
import importlib  # noqa: E402
A = importlib.import_module('AUC')
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
ref = np.concatenate([OP, OQ], 2)
rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True); V = np.repeat(pts[None], B, 0)


def auc(a, r):
    a, r = a[:, None], r[:, None]; a = A._warp_to_reference_start(a, r); return float(A._add_auc(A._object_add(a, r, V)))


print(f'floor_vs_ref {auc(np.repeat(ref[:1], T, 0), ref):.4f}')
for spec in sys.argv[2:]:
    path, _, lab = spec.partition(':'); d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'][:T].astype(float)
    ids = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{n}/')) for n in names]
    sim = q[:, ids, :7]; n = min(len(sim), T)
    print(f'{lab or path}: sim_vs_ref {auc(sim[:n], ref[:n]):.4f}')
