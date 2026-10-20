# Contact zone on object B (its frame) from public GT contact states: B's W2 vertices within d mm of A's W2 surface.
import sys, numpy as np, pandas as pd
from scipy.spatial import cKDTree
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
A,B,d=sys.argv[1],sys.argv[2],float(sys.argv[3])*1e-3; states=[tuple(int(x) for x in s.split(':')) for s in sys.argv[4].split(',')]
VA=np.load(f'{W}/W2/{A}.npz')['v']; VB=np.load(f'{W}/W2/{B}.npz')['v']; tB=cKDTree(VB); hit=np.zeros(len(VB),bool)
for ep,f in states:
    df=pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep); fi=f if f>=0 else len(df)-1
    pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma,Mb=T(pose[A]),T(pose[B])
    pa=tr(np.linalg.inv(Mb)@Ma,VA[::5])
    for idx in tB.query_ball_point(pa,d): hit[idx]=True
Z=VB[hit]*1e3
print(f'{B} zone (<= {d*1e3:.0f} mm of {A}, {len(states)} states): {hit.sum()} of {len(VB)} W2 vertices; bbox mm {Z.min(0).round(1)} .. {Z.max(0).round(1)}')
