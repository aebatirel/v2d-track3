import sys, numpy as np, trimesh, igl
sys.path.insert(0,'.'); from common import *
from scipy.spatial import ConvexHull
n=sys.argv[1]; Wd=sys.argv[2]; axis=int(sys.argv[3]); zs=[float(x) for x in sys.argv[4].split(',')]
m=scan_welded(n); V=np.asarray(m.vertices); F=np.asarray(m.faces,np.int64); c=m.bounds.mean(0)
d=np.load(f'{Wd}/{n}.npz'); WV,WF=d['v'],d['f']
sd=igl.signed_distance(WV,V,F,igl.SIGNED_DISTANCE_TYPE_PSEUDONORMAL)[0]; far=WV[sd>1e-3]
print(n,'W verts outward >1mm:',len(far),'of',len(WV), 'bbox',np.round(far.min(0)*1e3,1).tolist() if len(far) else '',np.round(far.max(0)*1e3,1).tolist() if len(far) else '')
hv=load_hulls(f'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/hulls11/{n}.npz'); E=[ConvexHull(h).equations for h in hv]
o=[a for a in range(3) if a!=axis]
for z in zs:
    r=np.arange(-70,70,1.5)*1e-3; P=np.zeros((len(r),3)); P[:,o[0]]=c[o[0]]+r; P[:,o[1]]=c[o[1]]; P[:,axis]=z*1e-3
    sw=igl.signed_distance(P,WV,WF)[0]; inV0=np.array([any((p@e[:,:3].T+e[:,3]).max()<=0 for e in E) for p in P])
    print(f'  {z:6.0f} W : {"".join("#" if s<0 else "." for s in sw)}\n         V0: {"".join("#" if s else "." for s in inV0)}')
