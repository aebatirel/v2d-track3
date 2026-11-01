# GT-free [M]: fit of candidates to our observed points (ep31 clean; ep18 with the hand blob region dropped) + footprint
import numpy as np, trimesh
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
O31=np.load('ep31_clean.npy').astype(float); O31=O31[np.random.default_rng(0).choice(len(O31),60000,replace=False)]
c={'library_v3':'/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb','M2_libsym_balls':'meshes/M2_libsym_balls.glb','M2b':'meshes/M2b_libsym_balls_base.glb','P1_partprog':'meshes/P1_partprog.glb','P1v0_preleak':'meshes/P1v0_partprog_preleak.glb'}
for k,p in c.items():
    m=trimesh.load(p,force='mesh'); P=np.asarray(m.sample(100000))
    do=cKDTree(P).query(O31)[0]; dm=cKDTree(O31).query(P)[0]
    # footprint: vertices within 2 mm of the lowest point along -z (our frame up ~ +z), convex hull area in xy
    v=np.asarray(m.vertices); low=v[v[:,2]<v[:,2].min()+0.002]
    try:
        from scipy.spatial import ConvexHull
        A=ConvexHull(low[:,:2]).volume*1e4 if len(low)>3 else 0
    except Exception: A=0
    com=m.center_mass
    print('%-16s obs31->mesh p50 %.2f p90 %.2f mm | mesh->obs p50 %.2f frac>10mm %.3f | watertight %s bodies %d vol %.1f cm3 | footprint(2mm) %.1f cm2 lowest z %.2f cm, COM %s cm'%(k,np.median(do)*1e3,np.percentile(do,90)*1e3,np.median(dm)*1e3,(dm>0.01).mean(),m.is_watertight,m.body_count,m.volume*1e6,A,v[:,2].min()*100,np.round(com*100,2)))
