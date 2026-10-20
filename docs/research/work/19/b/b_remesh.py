# Watertight remesh of a scan: GWN-signed distance on a grid of spacing h (libigl fast winding number sign, exact
# unsigned distance), marching cubes at iso level delta, drop specks (<0.05 cm3), manifold3d simplify(tol).
# usage: b_remesh.py name h_mm delta_mm simplify_tol_mm out.npz
import sys, time, numpy as np, trimesh, igl, manifold3d as mf
from skimage.measure import marching_cubes
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
n,h,dl,tol,out=sys.argv[1],float(sys.argv[2])*1e-3,float(sys.argv[3])*1e-3,float(sys.argv[4])*1e-3,sys.argv[5]
t0=time.time(); m=scan_welded(n); V=np.ascontiguousarray(m.vertices,float); F=np.ascontiguousarray(m.faces,np.int64)
lo=m.bounds[0]-4*h; hi=m.bounds[1]+4*h; N=np.ceil((hi-lo)/h).astype(int)+1
G=np.stack(np.meshgrid(*[lo[i]+h*np.arange(N[i]) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
S=np.empty(len(G)); B=1_000_000
for i in range(0,len(G),B):
    S[i:i+B]=igl.signed_distance(G[i:i+B],V,F,igl.SIGNED_DISTANCE_TYPE_FAST_WINDING_NUMBER)[0]
S=S.reshape(N); del G; t1=time.time()
v,f,_,_=marching_cubes(S,level=dl,spacing=(h,h,h)); v=v+lo
w=trimesh.Trimesh(v,f,process=True); w.merge_vertices()
comps=w.split(only_watertight=False); keep=[c for c in comps if abs(c.volume)>0.05e-6]
w=trimesh.util.concatenate(keep)
if w.volume<0: w.invert()
f0=len(w.faces)
M=mf.Manifold(mf.Mesh(vert_properties=np.asarray(w.vertices,np.float32),tri_verts=np.asarray(w.faces,np.uint32)))
if tol>0: M=M.simplify(tol)
mm=M.to_mesh(); w=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3].astype(float),np.asarray(mm.tri_verts).astype(np.int64),process=False)
sd_w=igl.signed_distance(np.asarray(w.vertices),V,F,igl.SIGNED_DISTANCE_TYPE_FAST_WINDING_NUMBER)[0]
qs=m.sample(200000); dq=np.sqrt(igl.point_mesh_squared_distance(qs,np.asarray(w.vertices),np.asarray(w.faces,np.int64))[0]); sdq=igl.signed_distance(qs,np.asarray(w.vertices),np.asarray(w.faces,np.int64))[0]
np.savez(out,v=np.asarray(w.vertices),f=np.asarray(w.faces,np.int64),h=h,delta=dl,tol=tol)
pc=lambda a,q: np.percentile(a,q)*1e3
print(f'{n} h={h*1e3:.2f} delta={dl*1e3:.2f} tol={tol*1e3:.2f}mm grid={tuple(int(x) for x in N)} MC_F={f0} comps={len(comps)}->{len(keep)} F={len(w.faces)} '
      f'wt={w.is_watertight} wind={w.is_winding_consistent} mf={M.status().name} vol_cm3={w.volume*1e6:.1f} | W-vert sd vs scan mm: '
      f'p1={pc(sd_w,1):.2f} p50={pc(sd_w,50):.2f} p99={pc(sd_w,99):.2f} max={sd_w.max()*1e3:.2f} | scan->W mm: p50={pc(dq,50):.2f} '
      f'p99={pc(dq,99):.2f} p99.9={pc(dq,99.9):.2f} max={dq.max()*1e3:.2f} >1mm={np.mean(dq>1e-3)*100:.2f}% scan-outside-W>0.5mm={np.mean(sdq>0.5e-3)*100:.2f}% >1mm={np.mean(sdq>1e-3)*100:.2f}% | sec sdf={t1-t0:.0f} tot={time.time()-t0:.0f}',flush=True)
