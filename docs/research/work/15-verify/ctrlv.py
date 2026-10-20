# Control: are A-scan points that sit deep in B's hulls actually inside B's scanned material, or in free space?
import sys, numpy as np, pandas as pd, trimesh
from scipy.spatial import cKDTree
sys.argv, args = sys.argv[:1], sys.argv[1:]
import penv as P
for s in args:
    ep,f,a,b=s.split(':'); ep=int(ep)
    if f=='end': f=len(pd.read_parquet(f'{P.D}/data/chunk-000/episode_{ep:06d}.parquet',columns=['frame_index']))-1
    f=int(f); Ra,ta=P.pose(ep,f,a); Rb,tb=P.pose(ep,f,b)
    A=P.scan(a); B=P.scan(b)
    As,_=trimesh.sample.sample_surface(A,60000,seed=2); Ab=P.to_b(As,Ra,ta,Rb,tb)
    Eb=[P.planes(v) for v,_ in P.load_hulls(b)]; dh=P.depth_in(Ab,Eb)
    Bs,fi=trimesh.sample.sample_surface(B,2000000,seed=3); Bn=B.face_normals[fi]
    dist,j=cKDTree(Bs).query(Ab); sd=np.einsum('ij,ij->i',Ab-Bs[j],Bn[j])
    ins=(sd<0)&(dist<0.03); dscan=np.where(ins,dist,0)   # dig-15 style normal-sign test
    deep=dh>0.002
    print(f'ep{ep} f{f} {a}->{b}: in-hull max {dh.max()*1e3:.1f} | normal-sign in-scan max {dscan.max()*1e3:.1f} p99 {np.percentile(dscan,99)*1e3:.1f} | '
          f'{deep.sum()} pts >2mm in hulls: unsigned dist to B-scan median {np.median(dist[deep])*1e3 if deep.any() else 0:.1f} '
          f'p10 {np.percentile(dist[deep],10)*1e3 if deep.any() else 0:.1f}, frac >3mm {np.mean(dist[deep]>0.003) if deep.any() else 0:.2f}; '
          f'deepest pt: hull depth {dh.max()*1e3:.1f}, scan dist {dist[np.argmax(dh)]*1e3:.1f}',flush=True)
