# Independent re-decomposition with the pinned coacd 1.0.11, loader variant process=False (raw GLB arrays), same call as
# flash_chord/assets/mesh.py convex_decompose(threshold=0.05, max_convex_hull=-1, preprocess_mode='auto').
import sys, os, re, time, numpy as np, trimesh
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11')
import coacd; coacd.set_log_level('info')
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
os.makedirs('hullsP',exist_ok=True)
for n in sys.argv[1:]:
    out=f'hullsP/{n}.npz'
    if os.path.exists(out): print(n,'exists'); continue
    u=open(f'{R}/urdf/{n}_rigid.urdf').read()
    f=R+'/urdf/'+re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1)
    m=trimesh.load(f,force='mesh',process=False)
    t=time.time(); parts=coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.int64)),threshold=0.05,max_convex_hull=-1,preprocess_mode='auto')
    np.savez(out,n=len(parts),**{f'v{i}':np.asarray(p[0]) for i,p in enumerate(parts)},**{f'f{i}':np.asarray(p[1]) for i,p in enumerate(parts)})
    print(n,'hulls',len(parts),'sec %.0f'%(time.time()-t),coacd.__file__,flush=True)
