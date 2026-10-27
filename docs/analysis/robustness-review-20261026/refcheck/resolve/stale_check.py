"""How far is each canonical reference's perception from the newest stored perception of the same episode?
(refcheck/resolve, 26 Oct 2026; CPU, perception outputs only, no ground truth.) Raw world poses are compared directly
(both are VO world frames of the same camera, built the same way) and also up to one constant rigid transform.
Usage: python -I stale_check.py STORE_ROOT OUT.json"""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
PAIRS = [  # (ep, canonical perception dir, newest perception dir)
    (2, 'runs/20261024-e3-e49e83d/perc2/ep2', 'runs/20261025-sweep-a894083/results/sweep/base/ep2'),
    (11, 'runs/20261025-twin11v3x-0e8aebb/perc2/ep11', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep11'),
    (12, 'runs/20261021-auto18-966eb96/perc2m/ep12', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep12'),
    (18, 'runs/20261021-auto18-966eb96/perc2m/ep18', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep18'),
    (21, 'runs/20261025-twin21arc-ee7ba8e/perc2/ep21', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep21'),
    (24, 'runs/20261021-auto24-966eb96/perc2m/ep24', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep24'),
    (26, 'runs/20261024-w1-37cc551/perc2/ep26', 'runs/20261025-sweep-a894083/results/sweep/base/ep26'),
    (27, 'runs/20261021-auto18-966eb96/perc2m/ep27', 'runs/20261025-sweep-a894083/results/sweep/base/ep27'),
    (31, 'runs/20261024-ev30rp-07eef1a/perc2/ep31', 'runs/20261025-guard-fe3f407/results/sweep/guard/ep31'),
    (39, 'runs/20261024-e3-e49e83d/perc2/ep39', 'runs/20261025-sweep-a894083/results/sweep/base/ep39'),
]
root, out = sys.argv[1], sys.argv[2]; res = []
for ep, a, b in PAIRS:
    A = np.load(f'{root}/{a}/poses_world_vo.npz'); B = np.load(f'{root}/{b}/poses_world_vo.npz'); row = dict(ep=ep, canonical=a, newest=b, objects={})
    for n in A.files:
        Wa, Wb = A[n], B[n]; T = min(len(Wa), len(Wb))
        raw = np.linalg.norm(Wa[:T, :3, 3] - Wb[:T, :3, 3], axis=1) * 1000
        rr = np.degrees((Rot.from_matrix(Wa[:T, :3, :3]) * Rot.from_matrix(Wb[:T, :3, :3]).inv()).magnitude())
        row['objects'][n] = dict(raw_pos_max_mm=round(float(raw.max()), 2), raw_pos_med_mm=round(float(np.median(raw)), 2),
                                 raw_rot_max_deg=round(float(rr.max()), 2), frames_over_10mm=int((raw > 10).sum()), frames=T)
    res.append(row); print(ep, a.split('runs/')[1], 'vs', b.split('runs/')[1], {n: (o['raw_pos_med_mm'], o['raw_pos_max_mm'], o['raw_rot_max_deg']) for n, o in row['objects'].items()})
json.dump(res, open(out, 'w'), indent=1)
