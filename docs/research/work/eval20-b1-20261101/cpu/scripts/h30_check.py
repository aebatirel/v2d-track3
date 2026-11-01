"""GT-free H30 check of eval 20 (2026-11-01): per frame, the nearest robot hand frame point of OUR reference (robot_{left,
right}_frames, without 'universe'; retargeted from our perceived hands, raw_motion_file names perc2 / hands_refined) to each
object's visual mesh surface (the reference's own glb, at the reference pose). No mocap, no dataset pose field.
Usage: h30_check.py REF.parquet ASSET_ROOT OUT.json"""
import json, sys
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R

ref, root, out = sys.argv[1:4]
t = pq.read_table(ref)
col = lambda n: t.column(n)[0].as_py()
names = col('object_body_names'); pos = np.array(col('object_body_position'), float); q = np.array(col('object_body_wxyz'), float)
T = len(pos)
pts = []
for side in ('left', 'right'):
    fn = col(f'{side}_robot_frame_names'); fr = np.array(col(f'robot_{side}_frames'), float)
    keep = [i for i, n in enumerate(fn) if n != 'universe']
    fr = fr.reshape(T, len(fn), -1)
    pts.append(fr[:, keep, :3])
H = np.concatenate(pts, 1)                                          # T x K x 3 hand frame positions (world)
res = dict(ref=ref, frames=T, raw_motion_file=col('raw_motion_file'), objects={})
for b, n in enumerate(names):
    m = trimesh.load(f'{root}/mesh/{n}/{n}.glb', force='mesh')
    pq_ = trimesh.proximity.ProximityQuery(m)
    d = []
    for f in range(T):
        Rm = R.from_quat(q[f, b][[1, 2, 3, 0]]).as_matrix()
        local = (H[f] - pos[f, b]) @ Rm                             # world -> object frame
        _, dist, _ = pq_.on_surface(local)
        inside = m.contains(local) if m.is_watertight else np.zeros(len(local), bool)
        dist = np.where(inside, 0.0, dist)
        d.append(round(float(dist.min()) * 1000, 1))
    res['objects'][n] = dict(hand_min_mm=d, H30=[x > 30 for x in d])
json.dump(res, open(out, 'w'))
for n, o in res['objects'].items():
    print(n, 'H30 frames:', [f for f in range(T) if o['H30'][f]][:3], '...', 'n', sum(o['H30']),
          '| hand_min_mm at f152/f165/f170/f183/f192/f201:', [o['hand_min_mm'][f] for f in (152, 165, 170, 183, 192, 201)])
