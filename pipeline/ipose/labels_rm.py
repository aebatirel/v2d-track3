"""R+M arm ONLY (GT-informed): camera-frame pot labels for the TRAIN episodes from mocap. Never run on test or eval.

label_cam(t) = world_T_cam(t)^-1 . A . S(t) . G^-1, where
  S(t) = mocap pose moved to the scan anchor (score_registered's reference), G = [Rb^T | ca] the kit's registration of
  the submitted TSDF mesh to the public scan (seed 1_000_003*ep + 101*slot, budget_mesh as the scorer), and
  A = world alignment (rotation chordal mean, translation mean over frames) fitted to the control track in its world.
Usage: python -I labels_rm.py OUT.npz --eps 0,26,41,42,43 --t3 T3 --kit KIT [--control DIR]
"""
import argparse, os, sys, json
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser()
p.add_argument('out'); p.add_argument('--eps', default='0,26,41,42,43')
p.add_argument('--t3', default='/content/t3'); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
p.add_argument('--mesh', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../meshes/ipose/white_pot.glb'))
p.add_argument('--control', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../../docs/analysis/ipose-20261103/control'))
a = p.parse_args()
TEST = {2, 27, 44, 45}
eps = [int(e) for e in a.eps.split(',')]
assert not TEST & set(eps), 'test episodes must never get labels'
sys.path.insert(0, a.kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments

OBJ = 'white_pot'
scan = trimesh.load(f'{a.t3}/mesh/{OBJ}/{OBJ}.glb', force='mesh')
sv, sf = np.asarray(scan.vertices, float), np.asarray(scan.faces, np.int64)
anchor, _ = _surface_moments(sv, sf)
cand = budget_mesh(a.mesh, 4096, 4096)


def se3(R, t):
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t; return T


def chordal(Rs):
    U, _, Vt = np.linalg.svd(np.sum(Rs, 0)); R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    return R


out, info = {}, {}
for e in eps:
    tab = pq.read_table(f'{a.t3}/ep{e}.parquet').to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    slot = names.index(OBJ)
    ca, Rb = T3._register_object_body(cand, (sv, sf), anchor, 1_000_003 * e + 101 * slot)
    G = se3(Rb.T, ca)
    Ginv = np.linalg.inv(G)
    S = []
    for objs in tab['observation.objects']:
        q = np.array([o['pose'] for o in objs if o['name'] == OBJ][0], float)
        S.append(se3(Rot.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(), q[:3]) @ se3(np.eye(3), anchor))
    L = np.stack([s @ Ginv for s in S])                         # mocap world, mesh frame
    CP = np.load(f'{a.control}/ep{e}_poses.npz'); WTC = CP['world_T_cam']; Tc = CP[f'cam_T_{OBJ}']
    n = min(len(L), len(Tc)); L, WTC, Tc = L[:n], WTC[:n], Tc[:n]
    Tw = np.stack([WTC[i] @ Tc[i] for i in range(n)])          # control track in its world
    RA = chordal(np.stack([Tw[i, :3, :3] @ L[i, :3, :3].T for i in range(n)]))
    tA = np.mean([Tw[i, :3, 3] - RA @ L[i, :3, 3] for i in range(n)], 0)
    A = se3(RA, tA)
    lab = np.stack([np.linalg.inv(WTC[i]) @ A @ L[i] for i in range(n)])
    out[f'ep{e}'] = lab
    dt = np.linalg.norm(lab[:, :3, 3] - Tc[:, :3, 3], axis=1) * 100
    dr = np.degrees([Rot.from_matrix(lab[i, :3, :3] @ Tc[i, :3, :3].T).magnitude() for i in range(n)])
    info[e] = dict(frames=n, slot=slot, reg_rot_deg=round(float(np.degrees(Rot.from_matrix(Rb).magnitude())), 2),
                   label_vs_track_cm_median=round(float(np.median(dt)), 2), label_vs_track_deg_median=round(float(np.median(dr)), 2))
    print(e, info[e], flush=True)
np.savez(a.out, **out)
json.dump(info, open(a.out.replace('.npz', '.json'), 'w'), indent=1)
