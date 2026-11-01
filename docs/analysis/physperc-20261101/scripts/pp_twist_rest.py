"""pp_twist_rest (GT-free): "a resting symmetric object does not spin". For blue_cup / beige_cup: frames where the
object is static (centroid step < MOVE_MM) and no hand is within HAND_MM get no twist increment (the axis is parallel
transported, tilt kept exactly); all other frames keep the tracker's own body-frame increment R_(t-1)^T R_t.
Usage: pp_twist_rest.py SCRATCH MESHDIR TRACKS_IN OUT [EPS]"""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL
from twist_canon_grasp_41383b4 import mesh_axis
MOVE_MM, HAND_MM = 1.0, 50.0
S, MD, TIN, OUT = sys.argv[1:5]
EPS = [int(x) for x in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
for e in EPS:
    P = dict(np.load(f'{TIN}/ep{e}/poses_world_vo.npz')); J = PL.hand_joints(S, e); rec = {}
    for n in [k for k in P if k in ('blue_cup', 'beige_cup')]:
        mp = f'{MD}/{n}.glb'; c = PL.shell_com(mp); a, _, _ = mesh_axis(mp)
        R = P[n][:, :3, :3]; T = len(R); OP = P[n][:, :3, 3] + np.einsum('tij,j->ti', R, c)
        out = [R[0]]; nrest = 0
        for t in range(1, T):
            static = np.linalg.norm(OP[t] - OP[t - 1]) * 1000 < MOVE_MM and PL.hand_dist(J, t, mp, P[n][t]) * 1000 > HAND_MM
            if static:
                u0 = out[-1] @ a; u1 = R[t] @ a
                out.append(PL.swing(u0, u1) @ out[-1]); nrest += 1
            else:
                out.append(out[-1] @ (R[t - 1].T @ R[t]))
                # re-project the axis onto the tracker's (tilt kept exactly)
                out[-1] = PL.swing(out[-1] @ a, R[t] @ a) @ out[-1]
        R2 = np.array(out); Q = P[n].copy(); Q[:, :3, :3] = R2; Q[:, :3, 3] = OP - np.einsum('tij,j->ti', R2, c)
        P[n] = Q; rec[n] = dict(static_frames=nrest, frames=T)
    os.makedirs(f'{OUT}/ep{e}', exist_ok=True)
    np.savez(f'{OUT}/ep{e}/poses_world_vo.npz', **P); json.dump(rec, open(f'{OUT}/ep{e}/pp_twist_rest.json', 'w'))
    if rec:
        print(e, rec, flush=True)
