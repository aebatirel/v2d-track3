import sys, numpy as np, trimesh, manifold3d as mf
d=np.load(sys.argv[1]); v,f=d['v'],d['f']
M=mf.Manifold(mf.Mesh(vert_properties=np.asarray(v,np.float32),tri_verts=np.asarray(f,np.uint32)))
for tol in [0.005,0.01,0.02,0.05]:
    mm=M.simplify(tol*1e-3).to_mesh(); vv=np.asarray(mm.vert_properties)[:,:3].astype(float); ff=np.asarray(mm.tri_verts).astype(np.int64)
    out=sys.argv[1].replace('.npz',f'_s{tol}.npz'); np.savez(out,v=vv,f=ff); print(out,len(ff))
