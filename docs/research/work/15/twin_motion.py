"""Twin GT motion summary: per object max/end displacement from f0, max lift, max rotation, last-moving frame."""
import sys, numpy as np, pandas as pd
from scipy.spatial.transform import Rotation as R
B='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
for ep in map(int, sys.argv[1:]):
    df = pd.read_parquet(B % ep); objs = df['observation.objects'].tolist(); n = len(objs)
    names = [o['name'] for o in objs[0]]
    out = [f"{ep} n={n}"]
    for j, nm in enumerate(names):
        P = np.array([[o for o in fr if o['name']==nm][0]['pose'] for fr in objs], float)
        p = P[:, :3]; q = P[:, [4,5,6,3]]
        d = np.linalg.norm(p - p[0], axis=1)
        ang = np.degrees((R.from_quat(q) * R.from_quat(q[0]).inv()).magnitude())
        v = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * 20
        mv = np.where(v > 0.03)[0]
        last = mv[-1] if len(mv) else -1; first = mv[0] if len(mv) else -1
        tilt = np.degrees(np.arccos(np.clip(np.abs(R.from_quat(q).apply([0,0,1])[:,2] * 1), -1, 1)))
        tilt0 = R.from_quat(q).apply([0,0,1])[:,2]
        out.append(f"| {nm}: dmax={d.max()*100:.1f}cm dend={d[-1]*100:.1f}cm lift={(p[:,2]-p[0,2]).max()*100:.1f}cm "
                   f"rotmax={ang.max():.0f}d rotend={ang[-1]:.0f}d zaxis_z[min]={tilt0.min():+.2f} vmax={v.max():.2f}m/s move[{first}-{last}]")
    print(' '.join(out))
