"""Design check (CPU): how far apart are our library mesh body frames and the public scan (mocap) body frames?
Uses the kit's own registration (_register_object_body), as pipeline/score_registered.py does with --meshes.
For a mocap pose (R_g, t_g) of the scan frame, our mesh must be placed at R_o = R_g R, t_o = t_g + R_g (c_scan - R ca)
for the registered scorer to see a perfect match. Prints the rotation angle of R and the offset |c_scan - R ca|."""
import sys, json, numpy as np, trimesh
kit, lib, scans = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from scipy.spatial.transform import Rotation as Rot
out = {}
for n in sys.argv[4:]:
    import os; q = f'{scans}/{n}/{n}.glb'; q = q if os.path.exists(q) else f'{scans}/{n}/{n}_visual.glb'; m = trimesh.load(q, force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f)
    cand = budget_mesh(f'{lib}/{n}.glb', 4096, 4096)
    ca, R = T3._register_object_body(cand, (v, f), c, 12345)
    off = c - R @ ca
    out[n] = dict(rot_deg=round(float(np.degrees(Rot.from_matrix(R).magnitude())), 2), offset_cm=round(float(np.linalg.norm(off) * 100), 2),
                  offset_xyz_cm=np.round(off * 100, 2).tolist())
print(json.dumps(out, indent=1))
