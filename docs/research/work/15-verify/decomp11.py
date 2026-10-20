# Re-decompose public collision meshes exactly as flash_chord/assets/mesh.py does, with a chosen coacd build.
import sys, os, time, numpy as np, trimesh
lib=os.environ.get('COACD_LIB','pylib11'); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), lib))
import coacd; coacd.set_log_level('error')
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
O=os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get('OUT','hulls11')); os.makedirs(O,exist_ok=True)
import re
for n in sys.argv[1:]:
    out=f'{O}/{n}.npz'
    if os.path.exists(out): print(n,'exists'); continue
    u=open(f'{R}/urdf/{n}_rigid.urdf').read()
    cf=re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1); f=os.path.normpath(os.path.join(R,'urdf',cf))
    m=trimesh.load(f,force='mesh')   # no explicit merge (Newton passes its loaded source vertices)
    v=np.ascontiguousarray(m.vertices,dtype=np.float64); fc=np.ascontiguousarray(m.faces,dtype=np.int64).reshape(-1,3)
    t=time.time(); parts=coacd.run_coacd(coacd.Mesh(v,fc),threshold=0.05,max_convex_hull=-1,preprocess_mode='auto')
    np.savez(out,n=len(parts),**{f'v{i}':np.asarray(p[0]) for i,p in enumerate(parts)},**{f'f{i}':np.asarray(p[1]) for i,p in enumerate(parts)})
    print(n,os.path.basename(f),'V',len(v),'hulls',len(parts),'sec %.0f'%(time.time()-t),coacd.__file__.split('/')[-3],flush=True)
