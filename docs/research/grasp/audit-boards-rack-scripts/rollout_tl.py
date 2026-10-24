"""Per-frame object state in rollouts vs our reference (no GT): lift (z - z0, cm), xy displacement, rotation from f0,
error to reference (cm / deg)."""
import sys, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
kit = sys.argv[1]; frames = [int(x) for x in sys.argv[2].split(',')]; rolls = sys.argv[3:]
sys.path.insert(0, kit); from v2dlb.submission_parquet import read_trajectory
for rp in rolls:
    tr = read_trajectory(Path(rp)); names = sorted(set(tr.object_slot.tolist()))
    print('==', '/'.join(rp.split('/')[-4:-1]))
    for k in names:
        sel = tr.object_slot == k; o = np.argsort(tr.frame_index[sel]); P = tr.pose_xyzw[sel][o]; Rf = tr.reference_xyzw[sel][o]
        nm = tr.object_name[sel][0] if tr.object_name is not None else k
        lift = 100 * (P[:, 2] - P[0, 2]); rl = 100 * (Rf[:, 2] - Rf[0, 2]); dxy = 100 * np.linalg.norm(P[:, :2] - P[0, :2], axis=1)
        rot = np.degrees((R.from_quat(P[:, 3:7]) * R.from_quat(P[0, 3:7]).inv()).magnitude())
        e = 100 * np.linalg.norm(P[:, :3] - Rf[:, :3], axis=1); er = np.degrees((R.from_quat(P[:, 3:7]) * R.from_quat(Rf[:, 3:7]).inv()).magnitude())
        print(f'  {nm}: max lift {lift.max():.1f} (ref {rl.max():.1f}) at f{int(np.argmax(lift))}; first err>3cm f{int(np.argmax(e > 3)) if (e > 3).any() else -1}; final err {e[-1]:.1f}cm {er[-1]:.0f}deg')
        print('   ' + ' '.join(f'f{f}:{lift[f]:+.1f}/{rl[f]:+.1f}z {dxy[f]:.1f}xy {rot[f]:.0f}r e{e[f]:.1f}' for f in frames if f < len(P)))
