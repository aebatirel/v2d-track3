"""Penetration of the beige cup's collision pieces into the blue cup's along OUR reference (kinematic, GT-free)."""
import glob, sys, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
ref, A, B = sys.argv[1], sys.argv[2], sys.argv[3]          # ref parquet, pieces dir of the moving cup, pieces dir of the partner
shrink = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # extra radial shrink (m) of the moving cup's samples, about its axis
row = pq.read_table(ref).to_pylist()[0]; names = list(row['object_body_names'])
pos = np.array(row['object_body_position'], float); qq = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
ia, ib = names.index('beige_cup'), names.index('blue_cup')
pa = [trimesh.load(f, force='mesh') for f in sorted(glob.glob(f'{A}/piece_*.obj'))]
pb = [ConvexHull(trimesh.load(f, force='mesh').vertices) for f in sorted(glob.glob(f'{B}/piece_*.obj'))]
S = np.vstack([p.sample(400) for p in pa] + [p.vertices for p in pa])       # surface samples of the moving cup's pieces
if shrink:
    ax = np.linalg.svd(S - S.mean(0))[2][0]; c = S.mean(0); r = (S - c) - np.outer((S - c) @ ax, ax)
    S = S - shrink * r / np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-6)
def depth(X):                                                # max over pieces of min over faces of (-signed distance)
    best = np.zeros(len(X))
    for h in pb:
        sd = X @ h.equations[:, :3].T + h.equations[:, 3]    # <= 0 inside every face
        d = -sd.max(1); best = np.maximum(best, d)
    return best
out = []
for f in range(0, len(pos), 2):
    Ta = R.from_quat(qq[f, ia]); Tb = R.from_quat(qq[f, ib])
    X = Tb.inv().apply(Ta.apply(S) + pos[f, ia] - pos[f, ib])  # moving-cup samples in the partner's frame
    d = depth(X); out.append((f, float(d.max() * 1000), int((d > 0.002).sum())))
for f, dm, n in out:
    if f % 6 == 0 or dm > 5: print(f'f{f:3d} max penetration {dm:5.1f} mm, samples > 2 mm: {n}')
