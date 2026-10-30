# GT-free M2b = M2 ∪ (library_v3 ∩ bottom slab along the library's own flatten 'up', 8 mm): keeps the v3 resting face
import numpy as np, trimesh, json, manifold3d as m3
L=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
M2=trimesh.load('meshes/M2_libsym_balls.glb', force='mesh')
up=np.array(json.load(open('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.flatten.json'))['up']); up/=np.linalg.norm(up)
def man(m): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
h0=(np.asarray(L.vertices)@up).min()
# slab: big box, bottom 8 mm along up
box=trimesh.creation.box(extents=[0.4,0.4,0.008+0.001])
# orient box z to up
z=np.array([0,0,1.0]); v=np.cross(z,up); s=np.linalg.norm(v); c=z@up
K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]); R=np.eye(3)+K+K@K*((1-c)/s**2)
T=np.eye(4); T[:3,:3]=R; T[:3,3]=up*(h0+0.004-0.0005)
box.apply_transform(T)
base=man(L)^man(box)
out=man(M2)+base
mm=out.to_mesh(); M=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3], np.asarray(mm.tri_verts), process=False); M.merge_vertices(); print("status",out.status())
print('M2b watertight',M.is_watertight,'bodies',M.body_count,'vol %.1f cm3'%(M.volume*1e6),'faces',len(M.faces))
M.export('meshes/M2b_libsym_balls_base.glb')
from scipy.spatial import ConvexHull
e1=np.cross(up,[1,0,0]); e1/=np.linalg.norm(e1); e2=np.cross(up,e1)
vv=np.asarray(M.vertices); hh=vv@up; low=vv[hh<hh.min()+0.001]; q=np.c_[low@e1,low@e2]; hull=ConvexHull(q)
com=M.center_mass; cq=np.array([com@e1,com@e2]); sgn=hull.equations[:,:2]@cq+hull.equations[:,2]
print('footprint %.1f cm2, COM inside %s margin %.1f mm'%(hull.volume*1e4, bool(np.all(sgn<=0)), -sgn.max()*1000))
