# DIAGNOSTIC with GROUND TRUTH (mocap). Displacement / rotation from f0, lowest point and up-axis tilt per object.
import sys, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
pqf, every, lib = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = pq.read_table(pqf).column('observation.objects').to_pylist(); T = len(rows); names = [o['name'] for o in rows[0]]
P = {n: np.array([[o['pose'] for o in r if o['name'] == n][0] for r in rows]) for n in names}
V = {n: trimesh.load(f'{lib}/{n}.glb', force='mesh').vertices for n in names}
print('frames', T, names)
for f in range(0, T, every):
    s = f'f{f:3d}'
    for n in names:
        p = P[n][f]; r = R.from_quat(p[[4, 5, 6, 3]]); r0 = R.from_quat(P[n][0][[4, 5, 6, 3]])
        d = 100 * np.linalg.norm(p[:3] - P[n][0][:3]); rot = np.degrees((r * r0.inv()).magnitude()); low = (r.apply(V[n]) + p[:3])[:, 2].min()
        s += f' | {n[:12]} d{d:5.1f} r{rot:5.1f} z{p[2]*100:6.1f} low{low*100:6.1f} vis{int([o["visible"] for o in rows[f] if o["name"]==n][0])}'
    print(s)
