"""Grasp templates from a successful policy rollout (2026-10-24; owner: "we did achieve the pinch hold when we scored
0.889, analyze that grip"). The ep18 standard-RL policy (FDR seed 43, 250M; registered AUC 0.889 over 6 evaluations)
holds the dust pan with a lateral (key) pinch on its ring band and the sweeper with a neck clamp
(docs/research/grasp/rl-discovered-grasps.md). This reads its body-pose trace (tools/trace_rollout.py policy) and stores,
per object, the hand's grasp IN THE OBJECT FRAME: the wrist (C_MC body = the reference wrist frame, checked 0.0 mm /
0.0 deg at frame 0) relative to the object, and the 22 finger joint angles recovered from parent / child link poses with
the URDF joint origins and axes (exact on simulator traces; equal to the reference's finger columns at frame 0).
pipeline/grasp_lock.py --templates uses them for any episode whose objects have one (public-episode training data
only; nothing from eval episodes or ground truth).
Usage: extract_grasp_templates.py TRACE.npz REF.parquet OUT.json OBJECT:SIDE:FRAME [...]
"""
import json, os, sys

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'research', 'grasp', 'rl-grasp-scripts'))
import rlgrasp_lib as L  # noqa: E402

trace, ref, out = sys.argv[1:4]
tr = L.load_trace(trace); t = pq.read_table(ref); T = len(t.column('robot_left_wrist_position')[0].as_py())
res = dict(source=dict(trace=trace, reference=os.path.basename(ref),
                       note='ep18 standard RL (FDR s43, 250M, registered AUC 0.889); see docs/research/grasp/rl-discovered-grasps.md'),
           templates={})
for spec in sys.argv[4:]:
    obj, side, f = spec.split(':'); f = int(f)
    po = tr['obj'][obj][f]; pw = tr['links'][f'{side}_hand_C_MC'][f]
    Ro = R.from_quat(po[3:7]); Rw = R.from_quat(pw[3:7])
    fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
    ang = L.joint_angles({k: v[f] for k, v in tr['links'].items()}, L.revolute_joints(side))
    o0 = tr['obj'][obj][0]
    res['templates'][obj] = dict(
        side=side, frame=f, wrist_pos_obj=Ro.inv().apply(pw[:3] - po[:3]).round(6).tolist(),
        wrist_quat_obj_xyzw=(Ro.inv() * Rw).as_quat().round(6).tolist(),
        finger_joint_names=fj, finger_joints=[round(ang[n][0], 5) for n in fj],
        off_axis_residual_max=round(max(ang[n][1] for n in fj), 5),
        object_moved_cm_at_frame=round(100 * float(np.linalg.norm(po[:3] - o0[:3])), 2),
        object_rot_deg_at_frame=round(L.rot_deg(po[3:7], o0[3:7]), 1))
    x = res['templates'][obj]
    print(f"{obj} ({side}, f{f}): wrist in object frame {np.round(100 * np.array(x['wrist_pos_obj']), 1)} cm; object moved "
          f"{x['object_moved_cm_at_frame']} cm / {x['object_rot_deg_at_frame']} deg; joints (deg) "
          f"{dict(zip(fj, np.round(np.degrees(x['finger_joints']), 0).tolist()))}", flush=True)
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); json.dump(res, open(out, 'w'), indent=1)
print('wrote', out)
