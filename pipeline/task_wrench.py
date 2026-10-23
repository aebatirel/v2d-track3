"""Task wrench along a reference object trajectory (2026-10-23, physics-aware grasp design, docs/research/notes/24).
For every frame, the wrench the hand(s) must apply to the object to make it follow its reference motion:
  F = m (a - g)                      (world frame, N)
  tau = I_w alpha + omega x I_w omega  (about the centre of mass, world frame, N m)
plus the torque of F about a grip point (e.g. a power grasp on a spoon handle with the bowl hanging out), and a support
flag (object resting on the table: near its frame-0 height and slow). Linear and angular accelerations come from
Savitzky-Golay derivatives of OUR reference (perceived object poses), so no ground truth is read.
Usage: task_wrench.py PARQUET [--mass 0.3] [--inertia Ixx,Iyy,Izz (body frame)] [--grip x,y,z] [--com x,y,z] [--fps 20]
(grip and com in the object frame, e.g. from grasp_lock's report: wrap.grip_obj_m, wrap.com_obj_m)
"""
import argparse, json

import numpy as np
import pyarrow.parquet as pq
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot

G = np.array([0.0, 0.0, -9.81])


def object_tracks(parquet):
    t = pq.read_table(parquet); names = t.column('object_body_names')[0].as_py()
    P = np.array(t.column("object_body_position")[0].as_py(), float); T = P.size // (3 * len(names))
    P = P.reshape(T, len(names), 3)
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, :, [1, 2, 3, 0]]
    return names, P, Q


def wrench(P, Q, mass, inertia_body, fps, grip=None, com=(0.0, 0.0, 0.0), win=9):
    """P (T,3), Q (T,4 xyzw) body origin of one object; grip, com in the object frame. Returns per-frame arrays."""
    dt = 1.0 / fps; T = len(P); win = min(win, T - (1 - T % 2)) if T > 4 else 3
    R = Rot.from_quat(Q); com = np.asarray(com, float); Pc = P + R.apply(com)   # centre-of-mass track
    a = savgol_filter(Pc, win, 3, deriv=2, delta=dt, axis=0, mode='interp')
    v = savgol_filter(Pc, win, 3, deriv=1, delta=dt, axis=0, mode='interp')
    rv = (R[1:] * R[:-1].inv()).as_rotvec() / dt                    # world angular velocity between frames
    w = np.vstack([rv[:1], 0.5 * (rv[1:] + rv[:-1]), rv[-1:]])
    w = savgol_filter(w, win, 3, axis=0, mode='interp'); al = savgol_filter(w, win, 3, deriv=1, delta=dt, axis=0, mode='interp')
    F = mass * (a - G)
    Iw = np.einsum('tij,j,tkj->tik', R.as_matrix(), np.asarray(inertia_body, float), R.as_matrix())
    tau = np.einsum('tij,tj->ti', Iw, al) + np.cross(w, np.einsum('tij,tj->ti', Iw, w))
    out = dict(F=F, tau=tau, acc=a, speed=np.linalg.norm(v, axis=1), omega=np.linalg.norm(w, axis=1))
    if grip is not None:                                            # wrench about the grip point (object frame -> world)
        r = R.apply(np.asarray(grip, float) - com)                  # grip point relative to the COM, world frame
        out['tau_grip'] = tau + np.cross(-r, F)                     # torque the hand must supply about the grip point
    rest_z = P[0, 2]
    out['supported'] = (np.abs(P[:, 2] - rest_z) < 0.01) & (out['speed'] < 0.05)
    return out


def summary(o):
    held = ~o['supported']; s = lambda x: np.linalg.norm(x, axis=1)  # noqa: E731
    r = dict(frames=int(len(held)), held_frames=int(held.sum()),
             F_max_N=round(float(s(o['F'])[held].max()), 2) if held.any() else 0.0,
             acc_max_ms2=round(float(s(o['acc'])[held].max()), 2) if held.any() else 0.0,
             acc_p95_ms2=round(float(np.percentile(s(o['acc'])[held], 95)), 2) if held.any() else 0.0,
             tau_com_max_Nm=round(float(s(o['tau'])[held].max()), 4) if held.any() else 0.0)
    if 'tau_grip' in o and held.any():
        r['tau_grip_max_Nm'] = round(float(s(o['tau_grip'])[held].max()), 3)
        r['tau_grip_p95_Nm'] = round(float(np.percentile(s(o['tau_grip'])[held], 95)), 3)
    return r


def main():
    p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('--mass', type=float, default=0.3)
    p.add_argument('--inertia', default='2.6e-3,2.58e-3,4.55e-5'); p.add_argument('--grip', default=None)
    p.add_argument('--fps', type=float, default=20.0); p.add_argument('--object', default=None)
    p.add_argument('--com', default='0,0,0', help='centre of mass in the object frame (m)')
    a = p.parse_args()
    names, P, Q = object_tracks(a.parquet); res = {}
    for j, n in enumerate(names):
        if a.object and a.object not in n:
            continue
        o = wrench(P[:, j], Q[:, j], a.mass, [float(x) for x in a.inertia.split(',')], a.fps,
                   [float(x) for x in a.grip.split(',')] if a.grip else None, [float(x) for x in a.com.split(',')])
        res[n] = summary(o)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
