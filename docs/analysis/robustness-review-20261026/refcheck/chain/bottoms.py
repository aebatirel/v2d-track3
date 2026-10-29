"""Where do the object bottoms sit at frame 0? (refcheck/chain, 26 Oct 2026; DIAGNOSTIC: reads public mocap.)

mkref's per-object snap puts OUR mesh's lowest point at frame 0 onto the fitted table. Whether that helps depends on
(1) whether the real object rests on the table at frame 0 (mocap: the public scan's lowest point at the mocap pose),
(2) how far our mesh's lowest point sits from the scan's when our mesh is placed where the kit's registration says it
is (registered placement: pose_ours = mocap pose composed with the inverse of the kit's registration), and
(3) the same with the identity placement (our mesh in the scan's frame: what scoring with the public scans assumes).
For every public episode and object: mocap scan bottom z (m, world z up; table ~0.61), and our mesh bottom minus the
scan bottom in both placements (cm; negative = our mesh reaches lower than the scan).
Usage: python -I bottoms.py T3 KIT MESHDIR OUT.json [EP ...]
"""
import json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq

T3d, KIT, MESH, OUT = sys.argv[1:5]
EPS = [int(e) for e in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as K
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from scipy.spatial.transform import Rotation as Rot


def scan_path(n):
    q = f'{T3d}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3d}/mesh/{n}/{n}_visual.glb'


res = {}
for ep in EPS:
    tab = pq.read_table(f'{T3d}/ep{ep}.parquet', columns=['observation.objects']).column(0)[0].as_py()
    lib = MESH + 'x' if (ep == 11 and MESH.endswith('library_v3')) else MESH
    row = {}
    for s, o in enumerate(tab):
        n = o['name']; q = np.array(o['pose'], float); R = Rot.from_quat(np.r_[q[4:7], q[3]]).as_matrix(); t = q[:3]
        sm = trimesh.load(scan_path(n), force='mesh'); sv, sf = np.asarray(sm.vertices, float), np.asarray(sm.faces, np.int64)
        c, _ = _surface_moments(sv, sf)
        zs = float((sv @ R.T + t)[:, 2].min())
        ov, of = budget_mesh(f'{lib}/{n}.glb', 4096, 4096)
        ca, Rb = K._register_object_body((ov, of), (sv, sf), c, 1_000_003 * ep + 101 * s)
        # convert: anchor_pos = p + Rp ca ; R_scan = Rp Rb^T  ->  Rp = R_scan Rb ; p = anchor_pos - Rp ca
        Rp = R @ Rb; p = (t + R @ c) - Rp @ ca
        zr = float((ov @ Rp.T + p)[:, 2].min()); zi = float((ov @ R.T + t)[:, 2].min())
        row[n] = dict(scan_bottom_z_m=round(zs, 4), ours_minus_scan_registered_cm=round((zr - zs) * 100, 2),
                      ours_minus_scan_identity_cm=round((zi - zs) * 100, 2))
    res[ep] = row
    print(ep, row, flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
