# Compare two hull sets of the same input (platform determinism): counts, vertex equality, and geometric difference.
import sys, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
from scipy.spatial import ConvexHull
a,b=load_hulls(sys.argv[1]),load_hulls(sys.argv[2])
same=len(a)==len(b) and all(x.shape==y.shape and np.array_equal(x,y) for x,y in zip(a,b))
def samp(hv,k=20000):
    P=np.vstack(hv); return P
def dist_out(P,H):   # max over points of distance outside the union of hulls H (upper bound via planes)
    best=np.full(len(P),np.inf)
    for v in H:
        e=ConvexHull(v).equations; best=np.minimum(best,np.maximum((P@e[:,:3].T+e[:,3]).max(1),0))
    return best*1e3
import trimesh
def surf(hv):
    out=[]
    for v in hv:
        h=ConvexHull(v); m=trimesh.Trimesh(v,h.simplices,process=False); np.random.seed(0); out.append(np.vstack([v,m.sample(max(30,int(m.area*0.5e6)))]))
    return np.vstack(out)
da=dist_out(surf(a),b); db=dist_out(surf(b),a)
print(f'{sys.argv[1]} vs {sys.argv[2]}: hulls {len(a)} vs {len(b)}, bit-identical {same}; '
      f'surface of A outside union(B) max {da.max():.2f} mm, B outside A max {db.max():.2f} mm (p99 {np.percentile(da,99):.2f}/{np.percentile(db,99):.2f})')
