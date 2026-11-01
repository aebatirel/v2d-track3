# ep18 P_o sweeper jump at f155: would ep0's F2 backfill fire (quasi-static [0,k) within 4 cm / 25 deg of f0)?
import sys, numpy as np
from scipy.spatial.transform import Rotation as Rot
d = np.load(sys.argv[1]); P = d['mini_sweeper']; k = 155
t = 100*np.linalg.norm(P[:k, :3, 3]-P[0, :3, 3], axis=1)
a = np.degrees(Rot.from_matrix(np.einsum('ji,njk->nik', P[0, :3, :3], P[:k, :3, :3])).magnitude())
print('pre-jump max %.1f cm %.0f deg -> fires: %s' % (t.max(), a.max(), t.max() <= 4 and a.max() <= 25))
for f in (150, 153, 154, 155, 156, 160): print(f, np.round(100*(P[f, :3, 3]-P[0, :3, 3]), 1))
