import sys, numpy as np, trimesh, igl, fast_simplification, manifold3d as mf
from skimage.measure import marching_cubes
sys.path.insert(0,'.'); from common import *
n='white_pot_lid'; h=1e-3
m=scan_welded(n); V=np.ascontiguousarray(m.vertices,float); F=np.ascontiguousarray(m.faces,np.int64)
lo=m.bounds[0]-4*h; hi=m.bounds[1]+4*h; N=np.ceil((hi-lo)/h).astype(int)+1
G=np.stack(np.meshgrid(*[lo[i]+h*np.arange(N[i]) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
S,_,_,_=igl.signed_distance(G,V,F,igl.SIGNED_DISTANCE_TYPE_FAST_WINDING_NUMBER); S=S.reshape(N)
for ad in [True,False]:
    v,f,_,_=marching_cubes(S,level=0,spacing=(h,h,h),allow_degenerate=ad); v=v+lo
    w=trimesh.Trimesh(v,f,process=True); w.merge_vertices()
    e=w.edges_sorted; _,c=np.unique(e,axis=0,return_counts=True)
    comps=w.split(only_watertight=False); vols=sorted([abs(x.volume)*1e6 for x in comps],reverse=True)
    print('allow_degenerate',ad,'F',len(w.faces),'wt',w.is_watertight,'boundary',(c==1).sum(),'nonmanif',(c>2).sum(),'bodies',len(comps),'vols_cm3',np.round(vols[:6],3).tolist())
    try:
        M=mf.Manifold(mf.Mesh(vert_properties=np.asarray(w.vertices,np.float32),tri_verts=np.asarray(w.faces,np.uint32))); print(' manifold3d status',M.status(),'genus',M.genus(),'nverts',M.num_vert())
    except Exception as ex: print(' mf err',ex)
