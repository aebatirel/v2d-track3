"""ORACLE: direction of the sweeper's frame-0 rotation error in camera coordinates (view axis vs out-of-plane)."""
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); import diag31 as D
from scipy.spatial.transform import Rotation as Rot
names, gt, N, tr = D.load_tracks(); XF = D.XF; T3 = D.T3
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
for arm, T in tr.items():
    ach, ref = D.prep(names, T, gt, H)
    Rb, tb = D.best_world(ach, ref, H)
    # error in perception (camera f0) frame: perceived R_p vs truth mapped into perception: R_b^T R_m
    Rp = T3._rotation_matrix(ach[0, 0, 0, 3:]); Rm = Rb.T @ T3._rotation_matrix(ref[0, 0, 0, 3:])
    rv = np.degrees(Rot.from_matrix(Rp @ Rm.T).as_rotvec())   # world(=cam0)-frame rotation taking truth to perceived
    print(arm, 'f0 sweeper error rotvec in cam0 frame (x right, y down, z view) deg', np.round(rv, 2), '| about view axis %.2f, out-of-plane %.2f' % (abs(rv[2]), np.linalg.norm(rv[:2])))
    # translation error of the anchor in cam frame
    pm = Rb.T @ (ref[0, 0, 0, :3] - tb); pp = ach[0, 0, 0, :3]
    print('    anchor error cam frame cm', np.round((pp - pm) * 100, 2), 'depth of anchor m %.3f' % pp[2])
    # top of handle (body +z end) displacement in camera frame
    top = np.array([0, 0, 0.07])
    print('    handle-top point (body z +7cm) error cam cm', np.round(((Rp @ top + pp) - (Rm @ top + pm)) * 100, 2))
    bot = np.array([0, 0, -0.07])
    print('    bristle-end point (body z -7cm) error cam cm', np.round(((Rp @ bot + pp) - (Rm @ bot + pm)) * 100, 2))
    # rack too
    Rp = T3._rotation_matrix(ach[0, 0, 1, 3:]); Rm = Rb.T @ T3._rotation_matrix(ref[0, 0, 1, 3:])
    rv = np.degrees(Rot.from_matrix(Rp @ Rm.T).as_rotvec())
    pm = Rb.T @ (ref[0, 0, 1, :3] - tb); pp = ach[0, 0, 1, :3]
    print('    rack f0 err rotvec cam deg', np.round(rv, 2), 'anchor err cam cm', np.round((pp - pm) * 100, 2))
