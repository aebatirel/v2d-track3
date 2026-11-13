# GT-free control meshes (inputs: library_v3 and the other agent's GT-free C2 transform + observed ball centres; no scan).
# C0: library_v3 intersected with its own C2 image, NO balls  -> tests whether the balls are what breaks the tie.
# C1: library_v3 UNION the 2 observed +x balls (+posts), NOT symmetrised -> tests whether symmetrisation is needed at all.
import numpy as np, trimesh, json, manifold3d as m3
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
L=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
J=json.load(open(f'{S}/diag/sweeper/meshes/M2_libsym_balls.json'))
R=np.array(J['R']); t=np.array(J['c2_t'])
def man(m): return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
def tom(M):
    mm=M.to_mesh(); T=trimesh.Trimesh(np.asarray(mm.vert_properties)[:,:3], np.asarray(mm.tri_verts), process=True); return T
Lr=L.copy(); Tm=np.eye(4); Tm[:3,:3]=R; Tm[:3,3]=t; Lr.apply_transform(Tm)
body=man(L)^man(Lr)
C0=tom(body); C0.export(f'{S}/diag/sweeper_verify/meshes/C0_libsym_noballs.glb')
balls=m3.Manifold()
for b in J['balls']:
    cen=np.array(b['centre_cm'])/100
    balls=balls+m3.Manifold.sphere(0.007,48).translate(cen.tolist())+m3.Manifold.cylinder(max(cen[0],0.002),0.0035,0.0035,24).rotate([0,90,0]).translate([0.0,cen[1],cen[2]])
C1=tom(man(L)+balls); C1.export(f'{S}/diag/sweeper_verify/meshes/C1_lib_plus_balls.glb')
for n,m in (('C0',C0),('C1',C1)): print(n,'watertight',m.is_watertight,'vol cm3 %.1f area cm2 %.1f'%(m.volume*1e6,m.area*1e4),'extents',np.round(m.extents*100,2))
# how much do the balls protrude beyond library_v3 itself? (if library already has bumps there, C1 changes little)
from scipy.spatial import cKDTree
P=np.asarray(L.sample(200000)); T=cKDTree(P)
for b in J['balls']:
    cen=np.array(b['centre_cm'])/100; apex=cen+np.array([0.007,0,0])
    print('ball',b['centre_cm'],'library max x within 7mm (y,z) of centre: %.2f cm; apex x %.2f cm; lib dist to apex %.1f mm'%(P[np.hypot(P[:,1]-cen[1],P[:,2]-cen[2])<0.007][:,0].max()*100, apex[0]*100, T.query(apex)[0]*1e3))
