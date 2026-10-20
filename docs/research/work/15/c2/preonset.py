"""Public GT, slot 0: first frame with >1 mm or >1 deg change from f0 ('first perturbation'), 1 cm onset, and the
largest displacement/rotation from f0 BEFORE the 1 cm onset. Analysis only (priors for the frame-0 anchor window)."""
import pandas as pd, numpy as np
from scipy.spatial.transform import Rotation as R
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
for e in [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]:
    df = pd.read_parquet(D % e); objs = df['observation.objects']
    P = np.array([o[0]['pose'] for o in objs]); name = objs.iloc[0][0]['name']
    d = np.linalg.norm(P[:, :3] - P[0, :3], axis=1) * 1000
    q = R.from_quat(P[:, [4, 5, 6, 3]]); a = np.degrees((q[0].inv() * q).magnitude())
    on = np.argmax(d > 10) if (d > 10).any() else len(d)
    pert = np.argmax((d > 1) | (a > 1)) if ((d > 1) | (a > 1)).any() else len(d)
    pre = slice(0, on)
    print(f'ep{e:2d} {name:18s} n={len(d)} first>1mm|1deg f{pert:3d}  1cm-onset f{on:3d}  gap {on - pert:3d} f  '
          f'pre-onset max {d[pre].max():5.1f} mm {a[pre].max():5.1f} deg')
