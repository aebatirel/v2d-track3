"""pp_twist (GT-free): GRASP session's twist_canon.canonicalise (claude/grasp-ep13-20261101, copied verbatim as
twist_canon_grasp_41383b4.py) applied to our npz tracks of blue_cup / beige_cup. Hands: our MediaPipe joints (world);
wrist orientation = palm frame from wrist (0), index MCP (5), pinky MCP (17); invalid frames put far away.
Object position = mesh surface centroid in the world; radius = max centroid distance of our mesh.
Usage: pp_twist.py SCRATCH MESHDIR TRACKS_IN OUT [EPS]"""
import json, os, sys, numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL
from twist_canon_grasp_41383b4 import canonicalise, mesh_axis
S, MD, TIN, OUT = sys.argv[1:5]
EPS = [int(x) for x in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
SYMC = ('blue_cup', 'beige_cup')
for e in EPS:
    P = dict(np.load(f'{TIN}/ep{e}/poses_world_vo.npz')); T = len(next(iter(P.values())))
    H = np.load(f'{S}/data/b4/ep{e}/hands.npz'); hands = {}
    for s in ('left', 'right'):
        J = np.asarray(H[f'joints_{s}'], float).copy(); ok = np.asarray(H[f'valid_{s}'], bool) & np.isfinite(J).all((1, 2))
        J[~ok] = 1e3
        x = J[:, 5] - J[:, 0]; y = J[:, 17] - J[:, 0]; z = np.cross(x, y)
        Rw = []
        for t in range(T):
            if ok[t] and np.linalg.norm(z[t]) > 1e-9:
                a = x[t] / np.linalg.norm(x[t]); c = z[t] / np.linalg.norm(z[t]); b = np.cross(c, a)
                Rw.append(np.column_stack([a, b, c]))
            else:
                Rw.append(Rw[-1] if Rw else np.eye(3))
        q = Rot.from_matrix(np.array(Rw)).as_quat()[:, [3, 0, 1, 2]]
        hands[s] = (J, q)
    rec = {}
    for n in P:
        if n not in SYMC:
            continue
        mp = f'{MD}/{n}.glb'; c = PL.shell_com(mp)
        ax, _, _ = mesh_axis(mp)
        rad = float(np.max(np.linalg.norm(np.asarray(PL.mesh(mp).vertices) - c, axis=1)))
        R = P[n][:, :3, :3]; OP = P[n][:, :3, 3] + np.einsum('tij,j->ti', R, c)
        OQ = Rot.from_matrix(R).as_quat()[:, [3, 0, 1, 2]]
        q2, info = canonicalise(OQ, OP, ax, rad, hands)
        R2 = Rot.from_quat(q2[:, [1, 2, 3, 0]]).as_matrix()
        Q = P[n].copy(); Q[:, :3, :3] = R2
        Q[:, :3, 3] = OP - np.einsum('tij,j->ti', R2, c)            # keep the centroid
        P[n] = Q; rec[n] = dict(axis=ax.tolist(), **{k: info[k] for k in ('held_frames', 'removed_deg_max', 'tilt_change_deg_max')})
    os.makedirs(f'{OUT}/ep{e}', exist_ok=True)
    np.savez(f'{OUT}/ep{e}/poses_world_vo.npz', **P); json.dump(rec, open(f'{OUT}/ep{e}/pp_twist.json', 'w'), indent=1)
    if rec:
        print(e, rec, flush=True)
