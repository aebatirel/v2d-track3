import pandas as pd, numpy as np
from scipy.spatial.transform import Rotation as R
df=pd.read_parquet('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_000031.parquet')
O=df['observation.objects']; names=[o['name'] for o in O.iloc[0]]; print(names)
for k,nm in enumerate(names):
    P=np.array([o[k]['pose'] for o in O]); d=np.linalg.norm(P[:,:3]-P[0,:3],axis=1)*1000
    q=R.from_quat(P[:,[4,5,6,3]]); a=np.degrees((q[0].inv()*q).magnitude())
    print(nm,' '.join(f'f{f}:{d[f]:.1f}/{a[f]:.1f}' for f in range(10,52,2)))
