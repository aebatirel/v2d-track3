"""Where do the robot hand links touch the plate (reference = designed grasp, or a simulated trace)? Per link within
CONTACT mm (hull SDF): share of frames, mean closest-point position in the plate's PCA frame (same sign convention as
mano_where.py) and the face (+axis3 / -axis3 / edge) of the mesh at that point. Also prints the world direction of
+axis3 at the first frame (up or down). Usage: robot_where.py REF.parquet SIDE OBJ F0 F1 [TRACE.npz] [CONTACT_MM]"""
import sys
import numpy as np, trimesh
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from audit_lib import HullSDF, hand_points, load_ref, load_trace, link_world, to_obj
from scipy.spatial.transform import Rotation as R
ref = load_ref(sys.argv[1]); side, obj, f0, f1 = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
tr = load_trace(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != '-' else None; CM = float(sys.argv[7]) / 1000 if len(sys.argv) > 7 else 0.003
j = ref['names'].index(obj); sdf = HullSDF(obj); hp = hand_points(side)
m = trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{obj}.glb', force='mesh'); V = m.vertices; c = V.mean(0)
W = np.linalg.svd(V - c, full_matrices=False)[2]; P = (V - c) @ W.T
lo = P[P[:, 0] < np.percentile(P[:, 0], 15)]; hi = P[P[:, 0] > np.percentile(P[:, 0], 85)]
if np.ptp(lo[:, 1]) > np.ptp(hi[:, 1]):
    W[0] *= -1; W[1] *= -1
pq_ = trimesh.proximity.ProximityQuery(m)
op = (lambda f: tr['obj'][obj][f]) if tr else (lambda f: ref['obj'][f, j])
lk = tr['links'] if tr else ref['links']
up = R.from_quat(op(f0)[3:7]).apply(W[2]); print(f'{"sim" if tr else "ref"} {side} on {obj} f{f0}-{f1}: +axis3 in world at f{f0} = {np.round(up, 2)} ({"UP" if up[2] > 0.5 else "DOWN" if up[2] < -0.5 else "sideways"})')
acc = {}
for f in range(f0, f1):
    for ln, Pl in hp.items():
        X = to_obj(op(f), link_world(lk[ln][f], Pl)); d = sdf(X); k = int(np.argmin(d))
        if d[k] <= CM:
            cp, _, tri = pq_.on_surface([X[k]]); nz = float(m.face_normals[tri[0]] @ W[2])
            acc.setdefault(ln, []).append(np.r_[(cp[0] - c) @ W.T, nz, d[k]])
for ln in sorted(acc, key=lambda k: -len(acc[k])):
    a = np.array(acc[ln]); s = ln.split('_', 1)[1]
    print(f'  {s:12s} share {len(a) / (f1 - f0):.2f}  pos ({100 * a[:, 0].mean():5.1f}, {100 * a[:, 1].mean():5.1f}, {100 * a[:, 2].mean():5.1f}) cm  '
          f'+face {np.mean(a[:, 3] > 0.5):.2f} -face {np.mean(a[:, 3] < -0.5):.2f} edge {np.mean(np.abs(a[:, 3]) <= 0.5):.2f}  depth p50 {1000 * np.median(a[:, 4]):5.1f} mm')
