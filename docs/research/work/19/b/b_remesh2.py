# Watertight remesh v2 ("W"): flood-fill exterior + oriented inward shell, then marching cubes at iso delta.
#  udf/s_pn = exact distance to the position-welded scan, sign by pseudonormal (scan faces are consistently oriented).
#  core     = grid voxels with udf > r (r = 0.6 h) 6-connected to the grid boundary (air reachable from outside; it may
#             leak through scan holes into cavities / wall interiors).
#  field f  = s_pn in the band (udf <= r); +udf in reachable air in front of a surface; udf - t behind a surface
#             (s_pn < 0) in reachable air, i.e. a solid shell of thickness t on the material side of every scanned
#             surface whose interior leaked (single-sided walls, open rims); -udf in enclosed (unreachable) voxels.
#  Then drop specks < 0.05 cm3. No decimation (CoACD's self-intersection check rejects manifold3d/QEM output, B3).
# usage: b_remesh2.py name h_mm delta_mm t_mm out.npz
import sys, time, numpy as np, trimesh, igl
from scipy import ndimage
from skimage.measure import marching_cubes
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
n,h,dl,t,out=sys.argv[1],float(sys.argv[2])*1e-3,float(sys.argv[3])*1e-3,float(sys.argv[4])*1e-3,sys.argv[5]
t0=time.time(); m=scan_welded(n); V=np.ascontiguousarray(m.vertices,float); F=np.ascontiguousarray(m.faces,np.int64)
lo=m.bounds[0]-4*h; hi=m.bounds[1]+4*h; N=np.ceil((hi-lo)/h).astype(int)+1
G=np.stack(np.meshgrid(*[lo[i]+h*np.arange(N[i]) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
S=np.empty(len(G)); B=1_000_000
for i in range(0,len(G),B):
    S[i:i+B]=igl.signed_distance(G[i:i+B],V,F,igl.SIGNED_DISTANCE_TYPE_PSEUDONORMAL)[0]
S=S.reshape(N); del G; U=np.abs(S); r=0.6*h
lab,_=ndimage.label(U>r)   # 6-connectivity
bl=np.unique(np.concatenate([lab[0].ravel(),lab[-1].ravel(),lab[:,0].ravel(),lab[:,-1].ravel(),lab[:,:,0].ravel(),lab[:,:,-1].ravel()]))
core=np.isin(lab,bl[bl>0])
f=np.where(U<=r,S,np.where(core,np.where(S>=0,U,U-t),-U)); t1=time.time()
eps=0.05*h; f=np.where(np.abs(f-dl)<eps, dl+np.where(f>=dl,eps,-eps), f)   # nudge off the iso level: no near-degenerate MC triangles
v,fc,_,_=marching_cubes(f,level=dl,spacing=(h,h,h),allow_degenerate=False); v=v+lo
w=trimesh.Trimesh(v,fc,process=True); w.merge_vertices()
comps=w.split(only_watertight=False); keep=[c for c in comps if abs(c.volume)>0.05e-6]
w=trimesh.util.concatenate(keep)
if w.volume<0: w.invert()
sd_w=igl.signed_distance(np.asarray(w.vertices),V,F,igl.SIGNED_DISTANCE_TYPE_PSEUDONORMAL)[0]
WV,WF=np.asarray(w.vertices),np.asarray(w.faces,np.int64)
qs=m.sample(200000); sdq=igl.signed_distance(qs,WV,WF)[0]
np.savez(out,v=WV,f=WF,h=h,delta=dl,t=t)
pc=lambda a,q: np.percentile(a,q)*1e3
print(f'{n} h={h*1e3:.2f} delta={dl*1e3:.2f} t={t*1e3:.1f}mm grid={tuple(int(x) for x in N)} enclosed_vox={int(((U>r)&~core).sum())} '
      f'comps={len(comps)}->{len(keep)} F={len(WF)} wt={w.is_watertight} wind={w.is_winding_consistent} vol_cm3={w.volume*1e6:.1f} | '
      f'W-vert dist to scan (outward>0) mm: p50={pc(sd_w,50):.2f} p99={pc(sd_w,99):.2f} max={sd_w.max()*1e3:.2f} | scan outside W: '
      f'>0.5mm {np.mean(sdq>0.5e-3)*100:.2f}% >1mm {np.mean(sdq>1e-3)*100:.2f}% max {sdq.max()*1e3:.2f}mm | sec {time.time()-t0:.0f}',flush=True)
