"""Rollout vs our reference per window: mean dz (sim - ref, cm), mean horizontal error (cm), mean rotation error (deg). No GT."""
import sys, json, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
kit = sys.argv[1]; obj = int(sys.argv[2]); W = json.loads(sys.argv[3]); rolls = sys.argv[4:]
sys.path.insert(0, kit); from v2dlb.submission_parquet import read_trajectory
for rp in rolls:
    tr = read_trajectory(Path(rp)); sel = tr.object_slot == obj; o = np.argsort(tr.frame_index[sel]); P = tr.pose_xyzw[sel][o]; Rf = tr.reference_xyzw[sel][o]
    dz = 100 * (P[:, 2] - Rf[:, 2]); dh = 100 * np.linalg.norm(P[:, :2] - Rf[:, :2], axis=1); er = np.degrees((R.from_quat(P[:, 3:7]) * R.from_quat(Rf[:, 3:7]).inv()).magnitude())
    print(Path(rp).parent.name, ' | '.join(f'{k}: dz {dz[a:b].mean():+.1f} dh {dh[a:b].mean():.1f} rot {er[a:b].mean():.0f}' for k, (a, b) in W.items()))
