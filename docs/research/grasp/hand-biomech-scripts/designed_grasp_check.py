"""Which robot sites touch the object in a grasp-lock reference (the DESIGNED grasp, i.e. the PD targets incl. squeeze)?
Approximate: site points (tip / DP / MP sites, palm frame) vs our mesh surface; signed distance (negative = inside).
Also reports thumb-vs-finger opposition: the angle between the object's surface normals at the thumb and at the fingers.
Usage: designed_grasp_check.py REF_GL_PARQUET GRASP_LOCK_JSON LIBRARY_DIR"""
import sys, json
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as Rot

ref, js, lib = sys.argv[1:4]
t = pq.read_table(ref); spec = json.load(open(js))
names = t.column('object_body_names')[0].as_py()
P = np.array(t.column('object_body_position')[0].as_py(), float)
Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[:, :, [1, 2, 3, 0]]
for ph in spec['phases']:
    side, obj = ph['hand'], ph['object']; k = names.index(obj)
    fn = t.column(f'{side}_robot_frame_names')[0].as_py()
    Fr = np.array(t.column(f'robot_{side}_frames')[0].as_py(), float)     # (T, 67, 7) xyz + quat (order?)
    m = trimesh.load(f'{lib}/{obj}.glb', force='mesh'); pq_ = trimesh.proximity.ProximityQuery(m)
    sites = [i for i, n in enumerate(fn) if n.endswith('_tip_site') or n.endswith('_DP_site') or n.endswith('_MP_site') or n.endswith('hand_C_MC')]
    h0 = ph['hold_from']; closed = h0 + spec['args']['close']; mid = (closed + ph['end']) // 2
    print(f"== {side} {obj}: hold {h0}-{ph['end']}, grasp frame {ph['grasp_frame']}, fingers_on {ph['fingers_on']}, gap {ph['grasp_gap_mm']} mm, "
          f"squeeze {ph['squeeze_rad']} rad, joints at limit {ph['joints_at_limit_after_squeeze']}, wrap {ph['wrap'] is not None}")
    for f in (closed, mid):
        R = Rot.from_quat(Q[f, k]); pts = R.inv().apply(Fr[f, sites, :3] - P[f, k])
        cp, d, tri = pq_.on_surface(pts)
        sd = d * np.where(m.contains(pts), -1.0, 1.0) if m.is_watertight else d
        nrm = m.face_normals[tri]
        touch = [(fn[s].replace(f'{side}_', ''), round(float(sd[j]) * 1000, 1)) for j, s in enumerate(sites) if sd[j] < 0.012]
        th = [j for j, s in enumerate(sites) if 'thumb' in fn[s] and sd[j] < 0.012]
        fi = [j for j, s in enumerate(sites) if 'thumb' not in fn[s] and 'C_MC' not in fn[s] and sd[j] < 0.012]
        opp = None
        if th and fi:
            nt = nrm[th].mean(0); nf = nrm[fi].mean(0)
            opp = round(float(np.degrees(np.arccos(np.clip(np.dot(nt / np.linalg.norm(nt), nf / np.linalg.norm(nf)), -1, 1)))), 0)
        palm = [round(float(sd[j]) * 1000, 1) for j, s in enumerate(sites) if 'C_MC' in fn[s]]
        print(f'   frame {f}: sites within 12 mm: {touch}')
        print(f'      thumb sites {len(th)}, finger sites {len(fi)}, thumb-vs-finger surface-normal angle {opp} deg (180 = opposed), palm frame {palm} mm')
