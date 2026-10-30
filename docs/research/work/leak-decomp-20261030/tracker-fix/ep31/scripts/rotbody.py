"""ORACLE: sweeper rotation error in its own body frame, per frame (bw alignment), plus scan PCA extents."""
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1]); import diag31 as D
from scipy.spatial.transform import Rotation as Rot
import trimesh
names, gt, N, tr = D.load_tracks(); XF = D.XF; T3 = D.T3
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
m = trimesh.load(XF.scan_path(D.T3D, 'mini_sweeper'), force='mesh'); v = np.asarray(m.vertices)
print('sweeper scan bbox cm', np.round((v.max(0) - v.min(0)) * 100, 1), 'anchor cm', np.round(H[0]['anchor'] * 100, 2))
c = v - H[0]['anchor']; w, U = np.linalg.eigh(np.cov(c.T)); print('pca sd cm', np.round(np.sqrt(w) * 100, 2)); print('pca axes (cols)', np.round(U, 3))
# mocap: sweeper body axes in world at f0
R0 = gt['mini_sweeper'][0][:3, :3]
for k, e in enumerate(np.eye(3)): print('body axis', k, 'world', np.round(R0 @ e, 3), 'angle to +z deg %.1f' % np.degrees(np.arccos(abs((R0 @ e)[2]))))
rk = gt['plastic_dish_rack'][0][:3, :3]
for k, e in enumerate(np.eye(3)): print('rack axis', k, 'world', np.round(rk @ e, 3))
out = {}
for arm, T in tr.items():
    ach, ref = D.prep(names, T, gt, H)
    Rb, tb = D.best_world(ach, ref, H); al = D.apply_world(ach, Rb, tb)
    Ra = T3._rotation_matrix(al[:, 0, 0, 3:]); Rr = T3._rotation_matrix(ref[:, 0, 0, 3:])
    dB = np.einsum('nji,njk->nik', Rr, Ra)   # Rr^T Ra : body-frame error
    rv = np.degrees(Rot.from_matrix(dB).as_rotvec())
    mag = np.linalg.norm(rv, axis=1)
    print(arm, 'f0 body rotvec deg', np.round(rv[0], 2), '|.| %.2f' % mag[0])
    for a, b in [(0, 5), (5, 27), (27, 45), (45, 62), (62, 105), (105, 185), (185, 236), (236, 290)]:
        print('   f%d-%d med body rotvec' % (a, b - 1), np.round(np.median(rv[a:b], 0), 2), 'med |.| %.2f' % np.median(mag[a:b]))
    out[arm] = rv.tolist()
    # tilt of perceived sweeper vs gravity: body axis 2 (scan z) in world vs mocap
    zA = Ra @ np.array([0, 0, 1.0]); zR = Rr @ np.array([0, 0, 1.0])
    print('   f0 scan-z axis: perceived angle to world z %.2f, mocap %.2f' % (np.degrees(np.arccos(abs(zA[0, 2]))), np.degrees(np.arccos(abs(zR[0, 2])))))
json.dump(out, open('rotbody.json', 'w'))
