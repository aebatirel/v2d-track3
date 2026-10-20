import sys, numpy as np, trimesh, igl
sys.path.insert(0,'.'); from common import *
from scipy.spatial import ConvexHull
for n in ['blue_cup','beige_cup']:
    m=scan_welded(n); V=np.asarray(m.vertices); F=np.asarray(m.faces,np.int64); c=m.bounds.mean(0)
    hv=load_hulls(f'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/hulls11/{n}.npz'); E=[ConvexHull(h).equations for h in hv]
    d=np.load(f'W/{n}.npz'); WV,WF=d['v'],d['f']
    print(n,'bounds',np.round(m.bounds*1e3,1).tolist())
    for z in [-80,-75,-70,-60,-40,-20,0,40,80]:
        # radial profile along +x from the axis at height z: scan crossings, W inside?, V0 inside?
        r=np.arange(0,60,1.0)*1e-3; P=np.stack([c[0]+r,np.full_like(r,c[1]),np.full_like(r,z*1e-3)],1)
        sw=igl.signed_distance(P,WV,WF)[0]
        inV0=np.array([any((p@e[:,:3].T+e[:,3]).max()<=0 for e in E) for p in P])
        print(f'  z={z:4d} W-solid r(mm): {"".join("#" if s<0 else "." for s in sw)}')
        print(f'         V0-solid r(mm): {"".join("#" if s else "." for s in inV0)}')
