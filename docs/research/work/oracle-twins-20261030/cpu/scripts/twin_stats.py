"""Task-shape stats of public twins (diagnostic, mocap): per object travel, max rotation from frame 0, final rotation,
end height change, and which perceived human hand (hands_refined.npz, world = rectified-left camera 0) is nearest each
moving object over time (hand-over = both sides take turns holding it). Mocap world != camera world, so the hand-object
distance uses the perceived object track (poses.npz) as a stand-in for the frame; only nearest-side labels are used.
Usage: python -I twin_stats.py PARQUET_DIR IN_DIR EP [EP ...]"""
import sys, json, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
PQD, IND = sys.argv[1:3]
for ep in [int(x) for x in sys.argv[3:]]:
    tab = pq.read_table(f'{PQD}/episode_{ep:06d}.parquet', columns=['observation.objects']).to_pandas()
    names = [o['name'] for o in tab['observation.objects'].iloc[0]]
    P = np.load(f'{IND}/ep{ep}/poses.npz'); W = P['world_T_cam']; N = len(W)
    Hh = np.load(f'{IND}/ep{ep}/hands_refined.npz')
    out = {}
    for n in names:
        g = np.stack([np.array([o for o in row if o['name'] == n][0]['pose'], float) for row in tab['observation.objects']])
        pos = g[:, :3]; R = Rot.from_quat(g[:, [4, 5, 6, 3]]); rel = R * R[0].inv()
        ang = np.degrees(rel.magnitude()); up = R.apply([0, 0, 1.0]); tilt = np.degrees(np.arccos(np.clip(up @ up[0], -1, 1)))
        travel = np.linalg.norm(pos - pos[0], axis=1)
        moving = travel > 0.01
        ow = np.einsum('tij,tjk->tik', W.astype(float), P[f'cam_T_{n}'].astype(float))[:, :3, 3]
        near = []
        for t in range(N):
            dd = {}
            for s in ('left', 'right'):
                J = Hh[f'joints_{s}'][t]; v = bool(Hh[f'valid_{s}'][t])
                dd[s] = float(np.linalg.norm(J[[4, 8, 12]] - ow[t], axis=1).min()) if v else 9.0
            near.append('L' if dd['left'] < 0.08 and dd['left'] <= dd['right'] else 'R' if dd['right'] < 0.08 else '-')
        seq = ''.join(near)
        runs = []                                   # compressed run sequence of holding sides
        for c in seq:
            if not runs or runs[-1][0] != c:
                runs.append([c, 1])
            else:
                runs[-1][1] += 1
        runs = [f'{c}{k}' for c, k in runs if k >= 4]
        out[n] = dict(travel_max_cm=round(float(travel.max() * 100), 1), end_travel_cm=round(float(travel[-1] * 100), 1),
                      rot_max_deg=round(float(ang.max()), 1), rot_end_deg=round(float(ang[-1]), 1),
                      up_tilt_max_deg=round(float(tilt.max()), 1), up_tilt_end_deg=round(float(tilt[-1]), 1),
                      dz_end_cm=round(float((pos[-1, 2] - pos[0, 2]) * 100), 1),
                      first_move_f=int(np.argmax(moving)) if moving.any() else None, frames=len(g), near_hand_runs=runs)
    print(json.dumps({ep: out}))
