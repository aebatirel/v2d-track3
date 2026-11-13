# GT-free: frame-to-frame jumps > 5 cm or > 30 deg in every local Phase-1 track (the trigger of ep0 F2 backfill).
import glob, sys, os, numpy as np
from scipy.spatial.transform import Rotation as Rot
R = sys.argv[1]
for arm in ('Po', 'Po2', 'Ps_scan'):
    fs = sorted(glob.glob(f'{R}/{arm}/ep*/poses_world_vo.npz')); hits = []
    for f in fs:
        ep = os.path.basename(os.path.dirname(f)); d = np.load(f)
        for n in d.files:
            P = d[n]; dt = 100*np.linalg.norm(np.diff(P[:, :3, 3], axis=0), axis=1)
            da = np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', P[:-1, :3, :3], P[1:, :3, :3])).magnitude())
            for k in np.where((dt > 5) | (da > 30))[0]:
                hits.append(f'{ep}:{n}@f{k+1} {dt[k]:.1f}cm {da[k]:.0f}deg')
    print(arm, len(fs), 'tracks;', len(hits), 'jumps:', '; '.join(hits[:12]))
