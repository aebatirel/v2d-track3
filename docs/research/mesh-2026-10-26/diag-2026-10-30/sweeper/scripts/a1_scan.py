# [D] scan geometry of the mini sweeper (diagnostic only)
import numpy as np, trimesh, json, sys
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
sc=trimesh.load(f'{S}/loc/t3/mesh/mini_sweeper/mini_sweeper_visual.glb', force='mesh')
lib=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
for nm,m in [('scan',sc),('lib_v3',lib)]:
    v=m.vertices; c=m.area_faces@m.triangles_center/m.area
    X=m.sample(200000,); X=np.asarray(X)
    C=np.cov((X-X.mean(0)).T); w,V=np.linalg.eigh(C); V=V[:,::-1]; w=w[::-1]
    P=(X-X.mean(0))@V
    print(nm, 'verts',len(v),'faces',len(m.faces),'watertight',m.is_watertight,'bodies',m.body_count,'area cm2',round(m.area*1e4,1),'vol cm3',round(abs(m.volume)*1e6,1) if m.is_watertight else None)
    print('  aabb extents cm', np.round(m.extents*100,2), 'bounds', np.round(m.bounds*100,2).tolist())
    print('  PCA sd mm', np.round(np.sqrt(w)*1000,1), 'PCA extents cm', np.round((P.max(0)-P.min(0))*100,2))
    print('  PCA axes (cols)', np.round(V,3).tolist())
    print('  centroid', np.round(c*100,2))
