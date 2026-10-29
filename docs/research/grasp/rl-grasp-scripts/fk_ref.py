"""Kinematically consistent reference hand: forward kinematics of the Sharpa Wave URDF from the reference's wrist pose
(robot_<side>_wrist_position / _wxyz = the C_MC frame) and finger joint targets (robot_<side>_finger_joints), i.e. the
PD targets the policy's residual is added to. Writes a trace-format npz (q xyz+xyzw, frame, labels) with the reference
object poses. Usage: fk_ref.py REF.parquet OUT.npz [--palm_from_frames]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pyarrow.parquet as pq
import xml.etree.ElementTree as ET
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import urdf_path, _rpy, _xyz
t = pq.read_table(sys.argv[1]); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
labels, Q = [], []
for s in ('left', 'right'):
    wp = np.array(t.column(f'robot_{s}_wrist_position')[0].as_py(), float).reshape(T, 3)
    wq = np.array(t.column(f'robot_{s}_wrist_wxyz')[0].as_py(), float).reshape(T, 4)[:, [1, 2, 3, 0]]
    names = t.column(f'{s}_robot_finger_joint_names')[0].as_py(); J = np.array(t.column(f'robot_{s}_finger_joints')[0].as_py(), float).reshape(T, len(names))
    root = ET.parse(urdf_path(s)).getroot(); joints = [j for j in root.findall('joint') if j.get('type') == 'revolute']
    if len(sys.argv) > 3 and sys.argv[3] == '--palm_from_frames':   # intended palm pose (wrist ILC changes only the command)
        fn = t.column(f'{s}_robot_frame_names')[0].as_py(); F = np.array(t.column(f'robot_{s}_frames')[0].as_py(), float).reshape(T, -1, 7)
        k = fn.index(f'{s}_hand_C_MC'); wp = F[:, k, :3]; wq = F[:, k][:, [4, 5, 6, 3]]
    pose = {f'{s}_hand_C_MC': (wp, R.from_quat(wq))}
    pending = list(joints)
    while pending:
        for j in list(pending):
            par, ch = j.find('parent').get('link'), j.find('child').get('link')
            if par not in pose:
                continue
            o = j.find('origin'); ax = _xyz(j.find('axis').get('xyz')); q = J[:, names.index(j.get('name'))]
            pp, pr = pose[par]; cp = pp + pr.apply(_xyz(o.get('xyz'))); cr = pr * _rpy(o.get('rpy')) * R.from_rotvec(q[:, None] * ax[None])
            pose[ch] = (cp, cr); pending.remove(j)
    for ln, (pp, pr) in pose.items():
        labels.append(f'{s}_sharpa_wave/{ln}'); Q.append(np.c_[pp, pr.as_quat()])
names = t.column('object_body_names')[0].as_py()
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
for k, n in enumerate(names):
    labels.append(f'track3_{n}/object'); Q.append(np.c_[OP[:, k], OQ[:, k]])
np.savez(sys.argv[2], q=np.stack(Q, 1).astype(np.float32), frame=np.arange(T), labels=np.array(labels))
print('wrote', sys.argv[2], len(labels), 'bodies', T, 'frames')
