"""GT-free post-processing rule R-backfill, scored on public tracks (diagnostic): for an object whose first guard
re-acquisition at frame k jumps > 5 cm or > 30 deg from frame k-1, and whose perceived track over [0, k) stayed within
4 cm / 25 deg of its frame-0 pose (quasi-static), replace [0, k) by the world pose at k. Scored * (X*_geom) and lib."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB = '/home/user/v2d-track3/meshes/library_v3'
XF.kit(S + '/map/scoring/kit/v2d_submission_kit'); T3D = S + '/map/scoring/t3'
XG = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
cases = [(0, f'{S}/leak/p1/oracle_roots/Ps_scan/ep0/poses_world_vo.npz', 'scan', {'white_pot': 64}),
         (23, f'{S}/refine/in/ep23/poses_world_vo.npz', 'lib', {'wooden_piece_1': 155})]
out = {}
for ep, path, frame, reacq in cases:
    names, gt = XF.mocap(T3D, ep); H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    V = np.load(path); T = {n: V[n].astype(float) for n in names}
    X = {n: (np.eye(4) if frame == 'scan' else np.array(XG[n]['X_scan_T_lib'])) for n in names}
    REG = [XF.reg_of_X(np.eye(4), h['anchor']) for h in H]
    star = lambda T: {n: T[n] @ np.linalg.inv(X[n]) for n in names}
    r = {'before': XF.score_track(names, star(T), gt, H, REG)}
    T2 = {n: T[n].copy() for n in names}
    for n, k in reacq.items():
        P = T[n]; jt = float(np.linalg.norm(P[k, :3, 3] - P[k - 1, :3, 3]) * 100)
        jr = float(np.degrees(Rot.from_matrix(P[k - 1, :3, :3].T @ P[k, :3, :3]).magnitude()))
        mt = float(np.linalg.norm(P[:k, :3, 3] - P[0, :3, 3], axis=1).max() * 100)
        mr = float(np.degrees(Rot.from_matrix(np.einsum('ji,njk->nik', P[0, :3, :3], P[:k, :3, :3])).magnitude()).max())
        fire = (jt > 5 or jr > 30) and mt < 4 and mr < 25
        r[n] = dict(k=k, jump_cm=round(jt, 2), jump_deg=round(jr, 1), pre_motion_cm=round(mt, 2), pre_motion_deg=round(mr, 1), fires=bool(fire))
        if fire: T2[n][:k] = P[k]
    r['after'] = XF.score_track(names, star(T2), gt, H, REG)
    out[f'ep{ep}'] = r
print(json.dumps(out, indent=1))
