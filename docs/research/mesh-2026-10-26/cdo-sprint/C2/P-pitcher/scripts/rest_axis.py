"""C2/P PREREG amendment A1 (GT-free): the pitcher's observed resting 'up' direction in its object frame.
A vessel stands on its base, so the axis of its body is the support normal at rest. From our own data only:
  - world_T_obj[t] = world_T_cam[t] @ cam_T_obj[t] (our sweep track);
  - table normal n (world) = the frame-0 plane of our depth (table_plane_ep.py, recon_mesh.table_plane, as obs_points);
  - resting frames = support_fill.rest_frames (still windows of MIN_REST = 10 frames within 3 mm / 2 deg; frame 0 and
    the last frame), kept when the object origin's height above the table is within REST_DH = 10 mm (2.5 vote voxels)
    of its lowest value over the episode (on the table, not held still in the air);
  - up_obj[t] = R_obj[t]^T n; a_rest = normalised mean of up_obj over the kept frames (all episodes given).
Prints and writes the direction and the per-frame spread (deg). No scan, mocap, parquet pose or library mesh.
Usage: rest_axis.py OUT.json POSES_1.npz:TABLE_1.json [POSES_2.npz:TABLE_2.json ...]
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..', '..', 'pipeline')))
import support_fill as SF  # noqa: E402

REST_DH = 0.010
OBJ = 'water_pitcher'
out = sys.argv[1]
ups, rows = [], []
for spec in sys.argv[2:]:
    poses, tablej = spec.split(':')
    P = np.load(poses)
    W_C = P['world_T_cam'].astype(np.float64); T_co = P[f'cam_T_{OBJ}'].astype(np.float64)
    N = min(len(W_C), len(T_co))
    W_O = np.einsum('tij,tjk->tik', W_C[:N], T_co[:N])
    tb = json.load(open(tablej)); n = np.array(tb['n_world']); n /= np.linalg.norm(n); c = tb['c_world']
    hgt = W_O[:, :3, 3] @ n + c
    quat = Rot.from_matrix(W_O[:, :3, :3]).as_quat()
    rest = SF.rest_frames(W_O[:, :3, 3], quat, np.zeros(N, bool))
    keep = [f for f in rest if hgt[f] <= hgt.min() + REST_DH]
    U = np.array([W_O[f, :3, :3].T @ n for f in keep])
    ups.append(U)
    rows.append(dict(poses=poses, table=tablej, rest_frames=[int(f) for f in rest], kept=[int(f) for f in keep],
                     origin_height_mm={int(f): round(float(hgt[f]) * 1e3, 1) for f in rest},
                     min_origin_height_mm=round(float(hgt.min()) * 1e3, 1)))
U = np.concatenate(ups)
a = U.mean(0); a /= np.linalg.norm(a)
spread = np.degrees(np.arccos(np.clip(U @ a, -1, 1)))
res = dict(rule='mean of R^T n over resting frames on the table (PREREG A1)', axis_dir=a.tolist(),
           n_frames=int(len(U)), spread_deg=dict(max=round(float(spread.max()), 2), median=round(float(np.median(spread)), 2)),
           episodes=rows)
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'episodes'}))
for r in rows:
    print(r['poses'], 'rest', r['rest_frames'], 'kept', r['kept'])
