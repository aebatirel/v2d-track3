"""Simulator-side check (no ground truth): CoACD with FlashCHORD's parameters (threshold 0.05, max_convex_hull -1,
preprocess 'auto'; flash_chord/assets/mesh.py) on two meshes, then the overlap of the two unions of convex pieces at our
tracked relative poses (what the simulator would start from). venv.
Usage: coacd_check.py MESH_A MESH_B POSES.npz OBJ_A OBJ_B a:b:s OUT.json"""
import json, sys, time
import numpy as np, trimesh, coacd
coacd.set_log_level('error')
ma, mb, pp, oa, ob, fr, out = sys.argv[1:8]


def hulls(path):
    m = trimesh.load(path, force='mesh', process=True); t0 = time.time()
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(m.vertices, float), np.asarray(m.faces, int)), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    H = []
    for v, f in parts:
        h = trimesh.Trimesh(v, f, process=True).convex_hull
        H.append((h.face_normals.copy(), np.einsum('ij,ij->i', h.face_normals, h.triangles[:, 0]), h.bounds.copy()))
    return m, H, time.time() - t0


def inside(H, P):
    ins = np.zeros(len(P), bool)
    for A, b, bd in H:
        k = np.flatnonzero(np.all((P >= bd[0] - 1e-6) & (P <= bd[1] + 1e-6), 1))
        if len(k):
            ins[k] |= np.all(P[k] @ A.T - b <= 1e-9, axis=1)
    return ins


mA, HA, ta = hulls(ma); mB, HB, tb = hulls(mb)
h = 0.0015
lo, hi = mA.bounds[0] - 0.01, mA.bounds[1] + 0.01
G = np.stack(np.meshgrid(*[np.arange(lo[k], hi[k], h) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
GA = G[inside(HA, G)]
P = np.load(pp); TA = P[f'cam_T_{oa}']; TB = P[f'cam_T_{ob}']
a, b, s = map(int, fr.split(':')); rows = []
for t in range(a, min(b, len(TA)), s):
    T = np.linalg.inv(TB[t]) @ TA[t]
    rows.append((t, round(float(inside(HB, GA @ T[:3, :3].T + T[:3, 3]).sum() * h ** 3 * 1e6), 3)))
ov = np.array([r[1] for r in rows])
res = dict(meshA=ma, meshB=mb, hullsA=len(HA), hullsB=len(HB), coacd_sec=[round(ta), round(tb)],
           hull_volA_cm3=round(len(GA) * h ** 3 * 1e6, 1), mesh_volA_cm3=round(float(mA.volume) * 1e6, 1),
           overlap_max_cm3=float(ov.max()), overlap_median_cm3=float(np.median(ov)), overlap_final_cm3=float(ov[-1]), per_frame=rows)
json.dump(res, open(out, 'w')); print(json.dumps({k: v for k, v in res.items() if k != 'per_frame'}))
