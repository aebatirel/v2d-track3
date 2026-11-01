"""GT-free per-frame census of the ep11 beige cup along OUR track (no scan, mocap, parquet pose or *_align.npz).
Per frame t: world distance between the beige- and blue-cup track origins and the nearest point of the blue-cup
library_v3 surface to the beige-cup origin (nesting), the nearest MediaPipe hand joint (any hand) to the beige-cup
library_v3 surface (hand contact), and the number of kept observed points from that frame in the obs npz.
Usage: frame_census.py POSES.npz HANDS.npz OBS.npz LIB_DIR OUT.json
"""
import json, sys
import numpy as np, trimesh
from scipy.spatial import cKDTree

poses, hands, obs, lib, out = sys.argv[1:6]
P = np.load(poses); W = P['world_T_cam'].astype(float)
Tb = P['cam_T_beige_cup'].astype(float); Tu = P['cam_T_blue_cup'].astype(float)
H = np.load(hands)
mb = trimesh.load(f'{lib}/beige_cup.glb', force='mesh'); mu = trimesh.load(f'{lib}/blue_cup.glb', force='mesh')
Sb = trimesh.sample.sample_surface(mb, 20000, seed=0)[0]; Su = trimesh.sample.sample_surface(mu, 20000, seed=0)[0]
Z = np.load(obs); fr = Z['frame']
cnt = np.bincount(fr, minlength=len(W))
rows = []
for t in range(len(W)):
    Wb = W[t] @ Tb[t]; Wu = W[t] @ Tu[t]
    d_org = float(np.linalg.norm(Wb[:3, 3] - Wu[:3, 3]))
    # beige surface in world, blue surface in world: min distance and the share of beige samples within 12 mm of blue
    Bw = Sb @ Wb[:3, :3].T + Wb[:3, 3]; Uw = Su @ Wu[:3, :3].T + Wu[:3, 3]
    dd = cKDTree(Uw).query(Bw[::10])[0]
    near_blue = float(np.mean(dd < 0.012))
    # beige origin inside blue's bounding box (blue frame)?
    ob = np.linalg.inv(Wu) @ Wb[:, 3]
    lo, hi = mu.bounds
    inside_box = bool(np.all(ob[:3] > lo) and np.all(ob[:3] < hi))
    dh = np.inf
    for side in ('left', 'right'):
        if H[f'valid_{side}'][t]:
            J = H[f'joints_{side}'][t].astype(float)
            if np.all(np.isfinite(J)):
                dh = min(dh, float(cKDTree(Bw).query(J)[0].min()))
    rows.append(dict(t=t, d_org_mm=round(d_org * 1e3, 1), near_blue_frac=round(near_blue, 3), origin_in_blue_box=inside_box,
                     hand_mm=None if not np.isfinite(dh) else round(dh * 1e3, 1), n_obs=int(cnt[t]) if t < len(cnt) else 0))
json.dump(rows, open(out, 'w'), indent=0)
for r in rows[::2]:
    print(r)
