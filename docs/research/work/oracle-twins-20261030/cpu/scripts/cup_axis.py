"""Is the beige-cup registration rotation a spin about the cup axis (harmless under the scorer's axial symmetry) or a flip?"""
import sys, os, numpy as np, trimesh
kit, lib, scans = sys.argv[1:4]
sys.path.insert(0, kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
from scipy.spatial.transform import Rotation as Rot
for n in sys.argv[4:]:
    m = trimesh.load(f'{scans}/{n}/{n}.glb', force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f); pts = _sample_mesh_surface(v, f, 1000, 7) - c
    w, U = np.linalg.eigh(np.cov(pts.T)); k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); ax = U[:, k]
    cand = budget_mesh(f'{lib}/{n}.glb', 4096, 4096)
    ca, R = T3._register_object_body(cand, (v, f), c, 12345)
    rv = Rot.from_matrix(R).as_rotvec(); ang = np.degrees(np.linalg.norm(rv)); axr = rv / max(np.linalg.norm(rv), 1e-9)
    # residual rotation after removing the best spin about the scan axis (axis expressed in the scan frame)
    best = min(np.degrees((Rot.from_rotvec(ax * t) * Rot.from_matrix(R)).magnitude()) for t in np.radians(np.arange(0, 360, 0.5)))
    print(n, 'rot', round(ang, 1), 'deg; |cos(rotation axis, cup axis)|', round(abs(float(axr @ ax)), 3), '; residual after removing spin', round(best, 2), 'deg')
