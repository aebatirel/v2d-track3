"""C2/P GT-free rest check of a pitcher mesh at the pitcher's observed resting poses (our track, our depth's table
plane; no scan, mocap or parquet pose). Uses pipeline/support_fill.py's own statics (rest_frames, settle_check:
COM inside the support polygon, margin >= 3 mm, tip >= 3 deg, quasi-static rocking up to 3 deg) so the verdict means
what 'UNSTABLE' meant on 25 Oct.

Per rest frame f (support_fill.rest_frames on the object's world track; frames whose lowest mesh point is more than
NEAR = 15 mm from the table are dropped, as support_fill does; no hand mask: the hold phases come from a reference
parquet, which this check does not read):
  gap_mm   = lowest mesh point above the table plane (negative = the mesh sinks into the table at the tracked pose);
  up_axis_deg = angle between the table normal and the mesh's lathe axis (if MESH.lathe.json exists);
  settle   = support_fill.settle_check on the convex-hull vertices of the mesh put on the table (lowest point at the
             plane), COM = the mesh's volume centroid (trimesh center_mass; the simulator uses the URDF inertial origin,
             which the pack does not change).
Usage: rest_check.py OUT.json POSES.npz TABLE.json OBJ LABEL=MESH.glb ...
"""
import json, os, sys
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..', '..', 'pipeline')))
import support_fill as SF  # noqa: E402

out, poses, tablej, obj = sys.argv[1:5]
specs = sys.argv[5:]
P = np.load(poses)
W_C = P['world_T_cam'].astype(np.float64); T_co = P[f'cam_T_{obj}'].astype(np.float64)
N = min(len(W_C), len(T_co))
W_O = np.einsum('tij,tjk->tik', W_C[:N], T_co[:N])
tb = json.load(open(tablej)); n = np.array(tb['n_world']); c = tb['c_world']
# a world frame whose z is the table normal and whose z = 0 is the table plane
z = n / np.linalg.norm(n); x = np.cross([0, 1.0, 0], z); x /= np.linalg.norm(x); y = np.cross(z, x)
Rt = np.stack([x, y, z]); o = -c * z                                  # point on the plane: n.p + c = 0 -> p = -c n
pos = (W_O[:, :3, 3] - o) @ Rt.T
quat = Rot.from_matrix(np.einsum('ij,tjk->tik', Rt, W_O[:, :3, :3])).as_quat()
rest = SF.rest_frames(pos, quat, np.zeros(N, bool))
res = dict(poses=poses, table=tablej, obj=obj, frames=int(N), rest_candidates=[int(f) for f in rest], meshes={})
for spec in specs:
    lab, path = spec.split('=', 1)
    m = trimesh.load(path, force='mesh')
    hull = m.convex_hull.vertices
    com = m.center_mass if m.is_watertight else m.centroid
    lj = path.rsplit('.', 1)[0] + '.lathe.json'
    axis = np.array(json.load(open(lj))['axis']) if os.path.exists(lj) else None
    rows = []
    for f in rest:
        Rw = Rt @ W_O[f, :3, :3]; tw = (W_O[f, :3, 3] - o) @ Rt.T
        X = hull @ Rw.T + tw; cm = Rw @ com + tw
        gap = float(X[:, 2].min())
        if abs(gap) > SF.NEAR:
            rows.append(dict(frame=int(f), gap_mm=round(gap * 1e3, 1), resting=False))
            continue
        Xs, cs = X.copy(), cm.copy(); Xs[:, 2] -= gap; cs[2] -= gap
        st = SF.settle_check(Xs, cs)
        row = dict(frame=int(f), resting=True, gap_mm=round(gap * 1e3, 1), com_height_mm=round(float(cs[2]) * 1e3, 1),
                   settle={k: (bool(v) if isinstance(v, (bool, np.bool_)) else v) for k, v in st.items()})
        if axis is not None:
            up_obj = Rw.T @ np.array([0, 0, 1.0])
            row['up_axis_deg'] = round(float(np.degrees(np.arccos(abs(np.clip(up_obj @ axis, -1, 1))))), 2)
        rows.append(row)
    ok = [r for r in rows if r.get('resting')]
    res['meshes'][lab] = dict(path=path, watertight=bool(m.is_watertight), volume_cm3=round(float(m.volume) * 1e6, 1)
                              if m.is_watertight else None, rest=rows,
                              verdict='STANDS (certified at every resting frame)' if ok and all(r['settle'].get('ok') for r in ok)
                              else ('NO RESTING FRAME' if not ok else 'UNSTABLE at ' + ','.join(str(r['frame']) for r in ok
                                                                                                 if not r['settle'].get('ok'))))
    print(lab, res['meshes'][lab]['verdict'], json.dumps(rows))
json.dump(res, open(out, 'w'), indent=1, default=float)
