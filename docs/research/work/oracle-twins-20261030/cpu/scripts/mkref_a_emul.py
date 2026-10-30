"""CPU emulation of mkref.py stage (a) only (table frame + support check + per-object snap, mkref defaults), on a
poses.npz, using mkref's own fit_table / table_frame. Writes a minimal reference parquet (object track only) so that
tools/ref_vs_mocap.py can score it. Stages after (a) (hands, E2S, contacts, contact_retarget rest_settle) need the GPU
box. Usage: python -I mkref_a_emul.py REPO POSES DEPTH0 CALIB LIB EP T3 OUT.parquet"""
import sys, types, json
import numpy as np, trimesh, pyarrow as pa, pyarrow.parquet as pq
REPO, POSES, DEPTH0, CALIB, LIB, EP, T3D, OUT = sys.argv[1:9]
sys.path.insert(0, f'{REPO}/pipeline'); import mkref as MK
a = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
                          support_fallback=1, snap='per_object', snap_max=0.02, table_z=0.60)
names = [str(o['name']) for o in pq.read_table(f'{T3D}/ep{EP}.parquet', columns=['observation.objects']).column('observation.objects')[0].as_py()]
P = np.load(POSES); W_C = P['world_T_cam'].astype(float); T = len(W_C); B = len(names)
cam_T = {n: P[f'cam_T_{n}'].astype(float) for n in names}
vis = {}
for n in names:
    m = trimesh.load(f'{LIB}/{n}.glb', force='mesh'); vis[n] = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)  # as make_assets
KR = MK.rectified_K(CALIB); depth0 = np.load(DEPTH0, mmap_mode='r'); depth0 = np.asarray(depth0[0] if depth0.ndim == 3 else depth0)
n, d, frac, npts, rms = MK.fit_table(depth0, KR, W_C[0], {nm: cam_T[nm][0] for nm in names}, vis, a)
OBJw = np.stack([np.stack([W_C[t] @ cam_T[nm][t] for nm in names]) for t in range(T)])
centroid = np.mean([OBJw[0, b, :3, :3] @ np.asarray(vis[nm].vertices).mean(0) + OBJw[0, b, :3, 3] for b, nm in enumerate(names)], 0)
T_tab = MK.table_frame(n, d, W_C[0], centroid, a.table_z)
OBJ = np.einsum('ij,tbjk->tbik', T_tab, OBJw)
h = np.array([(np.asarray(vis[nm].vertices) @ OBJ[0, b, :3, :3].T + OBJ[0, b, :3, 3])[:, 2].min() - a.table_z for b, nm in enumerate(names)])
ok = bool(-a.support_tol <= h.min() <= a.support_max)
shifts = np.where(np.abs(h) <= a.snap_max, -h, 0.0)
OBJ[:, :, 2, 3] += shifts[None]
from scipy.spatial.transform import Rotation as Rot
q = Rot.from_matrix(OBJ[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(T, B, 4)[..., [3, 0, 1, 2]]
tab = pa.table({'object_body_names': [names], 'object_body_position': [OBJ[..., :3, 3].tolist()],
                'object_body_wxyz': [q.tolist()], 'robot_left_wrist_position': [np.zeros((T, 3)).tolist()]})
pq.write_table(tab, OUT)
print(json.dumps(dict(support_check_ok=ok, bottoms_cm=dict(zip(names, np.round(h * 100, 2).tolist())),
                      shifts_cm=dict(zip(names, np.round(shifts * 100, 2).tolist())), inlier_frac=round(frac, 3))))
