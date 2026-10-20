# Per-piece check of the concavity-tolerance model: outward deviation of each CoACD hull set from the exact mesh it was
# computed from, vs 0.025 x L (L = longest bbox extent of that mesh). usage: b_partdev.py meshglob hullsdir
import sys, glob, os, numpy as np, trimesh, igl
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
from scipy.spatial import ConvexHull
rows=[]
for p in sorted(glob.glob(sys.argv[1])):
    hp=os.path.join(sys.argv[2],os.path.basename(p))
    if not os.path.exists(hp): continue
    d=np.load(p); V,F=d['v'],d['f']; L=np.ptp(V,0).max()
    pts=[]
    for v in load_hulls(hp):
        h=ConvexHull(v); m=trimesh.Trimesh(v,h.simplices,process=False); np.random.seed(0)
        pts.append(np.vstack([v[h.vertices],m.sample(max(50,int(m.area*0.25e6)))]))
    s=igl.signed_distance(np.vstack(pts),V,F)[0]
    rows.append((os.path.basename(p),L*1e3,s.max()*1e3,np.percentile(s,99)*1e3,s.max()/(0.025*L)))
for r in rows: print(f'{r[0]:28s} L {r[1]:6.1f} mm  hull-vs-own-mesh max {r[2]:5.2f} p99 {r[3]:5.2f} mm  max/(0.025L) {r[4]:.2f}')
if rows: print('SUMMARY n=%d  max/(0.025L): median %.2f max %.2f'%(len(rows),np.median([r[4] for r in rows]),max(r[4] for r in rows)))
