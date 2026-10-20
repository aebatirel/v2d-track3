# Stage C control: same frames as pen.py worst/end, depth of A-scan points inside B-SCAN (KD-tree + normals) vs inside B-HULLS
import sys, os, numpy as np, pandas as pd, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0,os.path.dirname(__file__)); import pen as P
def scan(n):
    f=f'{P.D}/mesh/{n}/{n}_collision.glb' if os.path.exists(f'{P.D}/mesh/{n}/{n}_collision.glb') else f'{P.D}/mesh/{n}/{n}.glb'
    return trimesh.load(f,force='mesh')
CASES=[(0,'white_pot_lid','white_pot',372),(11,'beige_cup','blue_cup',96),(12,'blue_cup','plastic_dish_rack',160),
       (27,'white_pot','plastic_dish_rack',216),(31,'mini_sweeper','plastic_dish_rack',160),(31,'mini_sweeper','plastic_dish_rack',0)]
for e,a,b,f in CASES:
    df=pd.read_parquet(f'{P.D}/data/chunk-000/episode_{e:06d}.parquet',columns=['observation.objects'])
    fr=df['observation.objects'].tolist()
    pa=[o['pose'] for o in fr[f] if o['name']==a][0]; pb=[o['pose'] for o in fr[f] if o['name']==b][0]
    Ra,ta=P.T(pa); Rb,tb=P.T(pb)
    A=scan(a); As=A.sample(30000); Ab=((As@Ra.T+ta)-tb)@Rb
    B=scan(b); Bs,fi=trimesh.sample.sample_surface(B,1500000); Bn=B.face_normals[fi]
    dist,j=cKDTree(Bs).query(Ab); sd=np.einsum('ij,ij->i',Ab-Bs[j],Bn[j])
    inside=(sd<0)&(dist<0.03); dscan=np.where(inside,dist,0)
    dh=P.depth(Ab,P.eqs(b))
    print(f'ep {e} f{f} {a}->{b}: A-scan in B-scan max {dscan.max()*1e3:.1f} mm p99 {np.percentile(dscan,99)*1e3:.1f}; '
          f'A-scan in B-hulls max {dh.max()*1e3:.1f} mm p99 {np.percentile(dh,99)*1e3:.1f}',flush=True)
