"""DIAGNOSTIC (2026-10-30, physics study): in our reference, do the perceived fingertips touch the object they hold?
For every hold phase that pipeline/grasp_lock.py found (its *_grasp_lock.json: hand, object, start..end), the signed
distance of the five perceived fingertip keypoints (mano_<side>_joints 4, 8, 12, 16, 20; bone-axis points, so a
fingertip pad sits ~0.6-0.9 cm outside its keypoint) to the object's mesh posed by the reference, per frame. Reports
the median over the hold of the nearest tip, the share of frames with >= 2 tips within 1.5 cm of the surface, and the
nearest tip at the hold's start, move and end frames. Our reference only; no ground truth.
Usage: hold_gap.py REF.parquet GRASP_LOCK.json MESH_DIR      (MESH_DIR/<object>.glb, the simulator's meshes)
"""
import json, sys
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot

t = pq.read_table(sys.argv[1]); ph = json.load(open(sys.argv[2]))['phases']; mesh_dir = sys.argv[3]
names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py()).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py()).reshape(T, B, 4)[..., [1, 2, 3, 0]]
J = {s: np.array(t.column(f'mano_{s}_joints')[0].as_py()).reshape(T, 21, 3) for s in ('left', 'right')}
pqs = {}
for p in ph:
    s, o, a, b = p['hand'], p['object'], p['start'], min(p['end'], T - 1)
    j = names.index(o)
    if o not in pqs:
        pqs[o] = trimesh.proximity.ProximityQuery(trimesh.load(f'{mesh_dir}/{o}.glb', force='mesh'))
    d = np.zeros((b - a + 1, 5))
    for i, f in enumerate(range(a, b + 1)):
        loc = Rot.from_quat(OQ[f, j]).inv().apply(J[s][f, [4, 8, 12, 16, 20]] - OP[f, j])
        d[i] = -100 * pqs[o].signed_distance(loc)          # cm, + outside the surface
    near = d.min(1); two = (np.sort(d, 1)[:, 1] <= 1.5).mean()
    pick = lambda f: near[min(max(f - a, 0), len(near) - 1)]
    mv = p.get('move_frame') or a
    print(f"{s:5s} {o:18s} f{a}-{b} ({p.get('object_travel_cm', 0):.0f} cm travel): nearest tip median {np.median(near):+.1f} cm "
          f"(p90 {np.percentile(near, 90):+.1f}), >=2 tips within 1.5 cm in {100 * two:.0f} % of frames | at start "
          f"{pick(a):+.1f}, move f{mv} {pick(mv):+.1f}, end {pick(b):+.1f}  (+ = outside)")
