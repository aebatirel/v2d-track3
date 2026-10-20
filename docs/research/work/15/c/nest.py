# Stage C: how much of the beige cup sticks out of the blue cup at the end of public ep 11 (Cup_Stack, twin of eval 10)
import numpy as np, pandas as pd, trimesh
from scipy.spatial.transform import Rotation as Rot
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
df=pd.read_parquet(f'{D}/data/chunk-000/episode_000011.parquet',columns=['observation.objects']); fr=df['observation.objects'].tolist()
def W(n,f):
    p=[o['pose'] for o in fr[f] if o['name']==n][0]; R=Rot.from_quat([p[4],p[5],p[6],p[3]]).as_matrix()
    v=trimesh.load(f'{D}/mesh/{n}/{n}.glb',force='mesh').vertices; return v@R.T+np.array(p[:3])
for f in (0,len(fr)-1):
    b=W('blue_cup',f); e=W('beige_cup',f)
    print(f'frame {f}: blue z {b[:,2].min():.3f}..{b[:,2].max():.3f}  beige z {e[:,2].min():.3f}..{e[:,2].max():.3f}  '
          f'beige top above blue top {1000*(e[:,2].max()-b[:,2].max()):.0f} mm; beige bottom above blue bottom {1000*(e[:,2].min()-b[:,2].min()):.0f} mm')
