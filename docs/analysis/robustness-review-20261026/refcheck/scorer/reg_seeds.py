"""Registration-seed spread of one submitted mesh (GT-free: no poses, no mocap; host = the public scan).

For each seed k in 0..N-1 the kit's _register_object_body(budget_mesh(our glb), host, scan centroid, BASE + k) is run with
the host at full resolution and welded + decimated to the given face counts (the kit decodes the hidden geometry with a
16 MB limit, so the hidden scans are lower resolution than the public ones). Reports the registered rotation as
yaw / pitch / roll about the scan axes (deg) and the candidate anchor (cm), so seed- and host-dependent modes show up.
Usage: python -I reg_seeds.py T3 KIT MESH_GLB OBJ OUT.json N BASE [faces ...]
"""
import json, os, sys, time
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
T3, KIT, GLB, OBJ, OUT = sys.argv[1:6]
N, BASE = int(sys.argv[6]), int(sys.argv[7])
FACES = [int(x) for x in sys.argv[8:]] or [0, 20000, 4096]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
import fast_simplification

q = f'{T3}/mesh/{OBJ}/{OBJ}.glb'
m = trimesh.load(q if os.path.exists(q) else f'{T3}/mesh/{OBJ}/{OBJ}_visual.glb', force='mesh')
v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
anchor, _ = _surface_moments(v, f)
cand = budget_mesh(GLB, 4096, 4096)
hosts = {0: (v, f)}
for k in FACES:
    if k:
        w = trimesh.Trimesh(v, f, process=True)
        dv, df = fast_simplification.simplify(np.asarray(w.vertices, np.float64), np.asarray(w.faces, np.int64),
                                              target_count=k)
        hosts[k] = (np.asarray(dv, np.float64), np.asarray(df, np.int64))
res = {'glb': GLB, 'obj': OBJ, 'base_seed': BASE, 'n': N, 'faces': FACES, 'runs': []}
for k in FACES:
    for s in range(N):
        t0 = time.time()
        ca, R = T._register_object_body(cand, hosts[k], anchor, BASE + s)
        zyx = Rot.from_matrix(R).as_euler('ZYX', degrees=True)
        res['runs'].append(dict(host_faces=k or 'full', seed=BASE + s, yaw=round(float(zyx[0]), 3),
                                pitch=round(float(zyx[1]), 3), roll=round(float(zyx[2]), 3),
                                rot_deg=round(float(np.degrees(Rot.from_matrix(R).magnitude())), 3),
                                quat_xyzw=np.round(Rot.from_matrix(R).as_quat(), 6).tolist(),
                                cand_anchor_cm=np.round(ca * 100, 3).tolist()))
        print(k or 'full', BASE + s, np.round(zyx, 2), f'{time.time() - t0:.1f}s', flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
