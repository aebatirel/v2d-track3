import sys, time, numpy as np, trimesh, igl, fast_simplification, manifold3d as mf
from skimage.measure import marching_cubes
sys.path.insert(0,'.'); from common import *
n='white_pot_lid'; h=1e-3
m=scan_welded(n); V=np.ascontiguousarray(m.vertices,float); F=np.ascontiguousarray(m.faces,np.int64)
lo=m.bounds[0]-4*h; hi=m.bounds[1]+4*h; N=np.ceil((hi-lo)/h).astype(int)+1
G=np.stack(np.meshgrid(*[lo[i]+h*np.arange(N[i]) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
S,_,_,_=igl.signed_distance(G,V,F,igl.SIGNED_DISTANCE_TYPE_FAST_WINDING_NUMBER); S=S.reshape(N)
v,f,_,_=marching_cubes(S,level=0,spacing=(h,h,h)); v=v+lo
w=trimesh.Trimesh(v,f,process=True); w.merge_vertices()
comps=w.split(only_watertight=False)
for c in comps:
    if abs(c.volume)>0.01e-6: print('comp vol cm3 %.3f'%(c.volume*1e6),'bounds',np.round(c.bounds*1e3,1).tolist())
keep=[c for c in comps if abs(c.volume)>0.05e-6]; w=trimesh.util.concatenate(keep)
if w.volume<0: w.invert()
M=mf.Manifold(mf.Mesh(vert_properties=np.asarray(w.vertices,np.float32),tri_verts=np.asarray(w.faces,np.uint32)))
print('kept F',len(w.faces),M.status())
for tol in [0.05e-3,0.1e-3,0.2e-3]:
    t=time.time(); Ms=M.simplify(tol); mm=Ms.to_mesh(); x=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3].astype(float),np.asarray(mm.tri_verts),process=False)
    sq,_,_=igl.point_mesh_squared_distance(np.asarray(w.vertices),x.vertices,np.asarray(x.faces,np.int64))
    print('mf simplify tol',tol,'F',len(x.faces),'wt',x.is_watertight,'wind',x.is_winding_consistent,'maxdev_mm %.3f'%(np.sqrt(sq.max())*1e3),'sec %.1f'%(time.time()-t))
for tf in [60000,30000]:
    vv,ff=fast_simplification.simplify(np.asarray(w.vertices,np.float32),np.asarray(w.faces,np.int32),target_count=tf)
    x=trimesh.Trimesh(vv.astype(float),ff,process=False); e=x.edges_sorted; _,cc=np.unique(e,axis=0,return_counts=True)
    print('fast_simpl',tf,'F',len(x.faces),'wt',x.is_watertight,'boundary',(cc==1).sum(),'nonmanif',(cc>2).sum())
Ms=M.simplify(0.1e-3); mm=Ms.to_mesh(); x=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3].astype(float),np.asarray(mm.tri_verts),process=False)
sq,_,_=igl.point_mesh_squared_distance(np.asarray(w.vertices),x.vertices,np.asarray(x.faces,np.int64)); d=np.sqrt(sq)*1e3
print('dev pcts',np.round(np.percentile(d,[50,99,99.9,99.99]),3),'n>0.3mm',(d>0.3).sum())
i=np.argsort(d)[-5:]; print(np.round(w.vertices[i]*1e3,1).tolist(), np.round(d[i],2))
print('comps after',len(x.split(only_watertight=False)), 'vol',x.volume*1e6)
