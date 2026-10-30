# GT-free candidate M2: library_v3 intersected with its own C2 (long-axis) image, plus the two marker balls observed in ep31.
# Inputs: library_v3 mesh (ours), ep31 observed points (ours). No scan, mocap, align or parquet pose.
import numpy as np, trimesh, json, manifold3d as m3
from scipy.spatial import cKDTree
L=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
P=np.asarray(L.sample(30000, seed=3)) if 'seed' in trimesh.sample.sample_surface.__code__.co_varnames else np.asarray(L.sample(30000))
c=P.mean(0); w,V=np.linalg.eigh(np.cov((P-c).T)); a=V[:,-1]
R0=2*np.outer(a,a)-np.eye(3)
def kab(A,B):
    ca,cb=A.mean(0),B.mean(0); U,_,Vt=np.linalg.svd((A-ca).T@(B-cb)); R=Vt.T@U.T
    if np.linalg.det(R)<0: Vt[-1]*=-1; R=Vt.T@U.T
    return R, cb-R@ca
T=cKDTree(P); R=R0.copy(); t=c-R0@c
for it in range(60):
    X=P@R.T+t; d,i=T.query(X); k=d<np.percentile(d,90)
    r,tt=kab(X[k],P[i[k]]); R=r@R; t=r@t+tt
d=T.query(P@R.T+t)[0]
from scipy.spatial.transform import Rotation as Rot
rv=Rot.from_matrix(R).as_rotvec(); ang=np.degrees(np.linalg.norm(rv)); ax=rv/np.linalg.norm(rv)
print('library self-C2: angle %.2f axis %s, residual mean %.2f mm p90 %.2f'%(ang, np.round(ax,3), d.mean()*1e3, np.percentile(d,90)*1e3))
def man(mesh):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(mesh.vertices,np.float32), tri_verts=np.asarray(mesh.faces,np.uint32)))
def tomesh(M):
    mm=M.to_mesh(); return trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3], np.asarray(mm.tri_verts), process=True)
ML=man(L)
Lr=L.copy(); Tm=np.eye(4); Tm[:3,:3]=R; Tm[:3,3]=t; Lr.apply_transform(Tm)
body=ML^man(Lr)
B=tomesh(body); print('body: vol cm3 %.1f (library %.1f), area %.1f cm2, bodies %d'%(B.volume*1e6, L.volume*1e6, B.area*1e4, B.body_count))
balls=json.load(open('balls_obs.json'))
face_x=balls['face_x_cm']/100; r=0.007
parts=body
info=[]
for b in balls['balls']:
    apex=b['apex_x_cm']/100
    # y,z of the protrusion peak: use the r=7 fit's y,z; centre x = apex - r (cap seen from +x)
    _,yc,zc=np.array(b['centre_r7_cm'])/100
    cen=np.array([apex-r,yc,zc])
    sph=m3.Manifold.sphere(r,48).translate(cen.tolist())
    post_len=max(cen[0]-0.0,0.002)
    post=m3.Manifold.cylinder(post_len,0.0035,0.0035,24).rotate([0,90,0]).translate([0.0,yc,zc])
    parts=parts+sph+post
    info.append(dict(centre_cm=np.round(cen*100,2).tolist(), r_mm=7))
M=tomesh(parts)
print('M2: watertight', M.is_watertight, 'bodies', M.body_count, 'vol %.1f cm3 area %.1f cm2 faces %d'%(M.volume*1e6, M.area*1e4, len(M.faces)), 'extents cm', np.round(M.extents*100,2))
M.export('meshes/M2_libsym_balls.glb')
json.dump(dict(c2_axis=ax.tolist(), c2_angle=ang, c2_t=t.tolist(), R=R.tolist(), balls=info), open('meshes/M2_libsym_balls.json','w'), indent=1)
