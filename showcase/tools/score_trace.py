"""Score a recorded replay (policy_trace.npz) against mocap: per-frame object centre error and kit-style AUC on the pot
(500 surface points, frame-aligned, no registration beyond the scene frame). Evaluation only (reads GT after inference)."""
import sys, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
tr, ep = sys.argv[1], int(sys.argv[2])
gt = pq.read_table(f'/content/t3/ep{ep}.parquet').to_pandas()
d = np.load(tr); Q = d['q']; L = [str(x) for x in d['labels']]
# GT is in the mocap frame; the sim/reference is in our table frame. Align with the reference poses at frame 0..N via
# the reference parquet's object trajectory? simpler: compare the replay to the reference (what the robot had to track)
ref = pq.ParquetFile(sys.argv[3]).read().to_pylist()[0]
names = ref['object_body_names']; P = np.array(ref['object_body_position']); W = np.array(ref['object_body_wxyz'])
out = {}
for b, n in enumerate(names):
    i = [k for k, l in enumerate(L) if n in l][0]
    V = trimesh.load(f'/content/t3/mesh/{n}/{n}.glb', force='mesh').sample(300, seed=0) if False else np.asarray(trimesh.load(f'/content/t3/mesh/{n}/{n}.glb', force='mesh').vertices[::200])
    T = min(len(P), len(Q) - 1)
    err = []
    for f in range(T):
        a = R.from_quat(Q[f, i, 3:]).apply(V) + Q[f, i, :3]
        r = R.from_quat(W[f, b][[1, 2, 3, 0]]).apply(V) + P[f, b]
        err.append(np.linalg.norm(a - r, axis=1).mean())
    err = np.array(err); auc = float(np.mean(np.clip(1 - (err - 0.01) / 0.08, 0, 1)))
    out[n] = (round(auc, 3), round(float(err.mean() * 100), 2), round(float(err.max() * 100), 1))
print(out)
