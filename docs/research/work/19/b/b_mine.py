# Mine GT contact states automatically over all public GT episodes (every 2nd frame, all pairs of the six objects):
# depth of W2-surface samples of A inside B's W2 solid, read from B's saved W2 field grid (trilinear; field = W2 iso
# surface at 0, so depth ~ distance inside W2 near the surface). Per episode & pair keep the deepest frame if > 0.5 mm.
import sys, glob, itertools, numpy as np, pandas as pd, trimesh
from scipy.ndimage import map_coordinates
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
OBJ=['white_pot_lid','white_pot','mini_sweeper','plastic_dish_rack','blue_cup','beige_cup']
FG={n:np.load(f'{W}/FG/{n}.npz') for n in OBJ}; S={}; R={}
for n in OBJ:
    d=np.load(f'{W}/W2/{n}.npz'); m=trimesh.Trimesh(d['v'],d['f'],process=False); np.random.seed(5); S[n]=m.sample(30000); R[n]=np.linalg.norm(S[n],axis=1).max()
def dep(p,n):
    g=FG[n]; c=((p-g['lo'])/g['h']).T; return -map_coordinates(g['f'],c,order=1,mode='constant',cval=1.0)*1e3
for f in sorted(glob.glob(P+'/data/chunk-000/episode_*.parquet')):
    df=pd.read_parquet(f); ep=int(f[-14:-8]); best={}; cnt={}
    for fi in range(0,len(df),2):
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}
        for a,b in itertools.combinations([n for n in OBJ if n in pose],2):
            Ma,Mb=T(pose[a]),T(pose[b])
            if np.linalg.norm(Ma[:3,3]-Mb[:3,3])>R[a]+R[b]: continue
            dab=dep(tr(np.linalg.inv(Mb)@Ma,S[a]),b).max(); dba=dep(tr(np.linalg.inv(Ma)@Mb,S[b]),a).max(); d=max(dab,dba)
            if d>0.5: cnt[(a,b)]=cnt.get((a,b),0)+1
            if d>0.5 and d>best.get((a,b),(0,))[0]: best[(a,b)]=(d,fi,dab,dba)
    for (a,b),(d,fi,dab,dba) in best.items():
        print(f'CASE ep{ep} f{fi} n{len(df)} {a} {b} W2depth A-in-B {dab:.1f} B-in-A {dba:.1f} contact_frames {cnt[(a,b)]}/{(len(df)+1)//2}',flush=True)
