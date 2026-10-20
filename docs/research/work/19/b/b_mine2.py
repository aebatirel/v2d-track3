# B26: contact mining (as b_mine.py) for the public episodes whose objects stage B did not cover:
# ep18 sweeper+dust pan, ep21/22 blue cup+pitcher, ep23/24 board+board. Every frame; W2 surface samples of A inside
# B's W2 field (and B in A); prints the deepest frame per episode and pair, the number of frames > 0.5 mm, and the
# frames with depth > 1.5 mm in decreasing order (top 5).
import sys, glob, itertools, numpy as np, pandas as pd, trimesh
from scipy.ndimage import map_coordinates
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
EPS=[18,21,22,23,24]
OBJ=['mini_sweeper','mini_dust_pan','blue_cup','water_pitcher','wooden_piece_1','wooden_piece_2']
FG={n:np.load(f'{W}/FG/{n}.npz') for n in OBJ}; S={}; R={}
for n in OBJ:
    d=np.load(f'{W}/W2/{n}.npz'); m=trimesh.Trimesh(d['v'],d['f'],process=False); np.random.seed(5); S[n]=m.sample(30000); R[n]=np.linalg.norm(S[n],axis=1).max()
def dep(p,n):
    g=FG[n]; c=((p-g['lo'])/g['h']).T; return -map_coordinates(g['f'],c,order=1,mode='constant',cval=1.0)*1e3
for ep in EPS:
    df=pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep); rec={}
    for fi in range(len(df)):
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}
        for a,b in itertools.combinations([n for n in OBJ if n in pose],2):
            Ma,Mb=T(pose[a]),T(pose[b])
            if np.linalg.norm(Ma[:3,3]-Mb[:3,3])>R[a]+R[b]: rec.setdefault((a,b),[]); continue
            dab=dep(tr(np.linalg.inv(Mb)@Ma,S[a]),b).max(); dba=dep(tr(np.linalg.inv(Ma)@Mb,S[b]),a).max()
            rec.setdefault((a,b),[]).append((max(dab,dba),fi,dab,dba))
    for (a,b),L in rec.items():
        L.sort(reverse=True); n05=sum(x[0]>0.5 for x in L); top=[(x[1],round(x[0],1)) for x in L[:5]]
        mind=min((x[0] for x in L),default=None)
        print(f'EP{ep} n{len(df)} {a} {b}: frames near {len(L)} contact>0.5mm {n05} deepest {top}',flush=True)
