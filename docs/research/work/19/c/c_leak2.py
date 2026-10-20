# Uncovered W2 voxels (whole 1 mm grid) for a hull set: how deep inside W2 are they and how far outside the hulls?
import sys, numpy as np
from scipy.spatial import ConvexHull
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
n,hd=sys.argv[1],sys.argv[2]
d=np.load(f'/Users/aebatirel/Documents/Code/v2d-research/work/19/b/FG/{n}.npz'); f,lo,h=d['f'],d['lo'],float(d['h'])
ii=np.argwhere(f<0); G=lo+h*ii; fv=f[f<0]
best=np.full(len(G),np.inf)    # min over hulls of max plane distance (<=0 inside)
for v in load_hulls(f'{hd}/{n}.npz'):
    lo_,hi_=v.min(0)-2e-3,v.max(0)+2e-3; k=np.where(np.all((G>=lo_)&(G<=hi_),1))[0]
    if len(k)==0: continue
    e=ConvexHull(v).equations; s=(G[k]@e[:,:3].T+e[:,3]).max(1); best[k]=np.minimum(best[k],s)
unc=best>1e-6
print(f'{n} {hd}: W2 voxels {len(G)}, uncovered {unc.sum()} ({unc.mean()*100:.3f}%); of those depth inside W2 (mm) '
      f'median {np.median(-fv[unc])*1e3 if unc.any() else 0:.2f} max {(-fv[unc]).max()*1e3 if unc.any() else 0:.2f}; '
      f'distance outside hull union (mm, upper bound) median {np.median(best[unc])*1e3 if unc.any() else 0:.3f} max {best[unc].max()*1e3 if unc.any() else 0:.3f}')
