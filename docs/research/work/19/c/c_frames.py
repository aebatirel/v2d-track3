# Up direction (world +z) expressed in each object's scan frame at public GT frame 0, and W2 bounds.
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
for ep,n in [(26,'white_pot'),(26,'plastic_dish_rack'),(12,'blue_cup'),(11,'beige_cup'),(0,'white_pot_lid'),(31,'mini_sweeper')]:
    df=pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep); pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[0]}
    M=T(pose[n]); up=M[:3,:3].T@[0,0,1]; d=np.load(f'{W}/W2/{n}.npz'); v=d['v']
    print(f'{n:18s} ep{ep} up_in_obj {np.round(up,3)} W2 bounds mm {np.round(v.min(0)*1e3,1)} {np.round(v.max(0)*1e3,1)}')
