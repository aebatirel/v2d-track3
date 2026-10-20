"""GT slot displacement (mm) and rotation (deg) from frame 0, every 3rd frame up to N. usage: gtdisp.py ep slot N"""
import sys, pandas as pd, numpy as np
from scipy.spatial.transform import Rotation as R
e, k, N = map(int, sys.argv[1:4])
df = pd.read_parquet('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet' % e)
P = np.array([o[k]['pose'] for o in df['observation.objects']]); name = df['observation.objects'].iloc[0][k]['name']
q = R.from_quat(P[:, [4, 5, 6, 3]]); d = np.linalg.norm(P[:, :3] - P[0, :3], axis=1) * 1000
a = np.degrees((q[0].inv() * q).magnitude())
print(e, name, ' '.join(f"f{i}:{d[i]:.1f}mm/{a[i]:.1f}d" for i in range(0, min(N, len(P)), 3)))
