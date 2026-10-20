# Exact FlashCHORD call (assets/mesh.py @8c778f90) on a given mesh, coacd 1.0.11; logs manifoldness.
# usage: b_decomp.py in.npz|scan:<name> out_hulls.npz [threshold] [preprocess_mode] [preprocess_resolution]
import sys, time, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
src,out=sys.argv[1],sys.argv[2]; th=float(sys.argv[3]) if len(sys.argv)>3 else 0.05
pm=sys.argv[4] if len(sys.argv)>4 else 'auto'; pr=int(sys.argv[5]) if len(sys.argv)>5 else None
coacd.set_log_level('info')
if src.startswith('scan:'):
    m=scan_newton(src[5:]); v,f=np.asarray(m.vertices),np.asarray(m.faces)
else:
    d=np.load(src); v,f=d['v'],d['f']
kw=dict(threshold=th,max_convex_hull=-1,preprocess_mode=pm)
if pr: kw['preprocess_resolution']=pr
t=time.time()
parts=coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(v,dtype=np.float64),np.ascontiguousarray(f,dtype=np.int64).reshape(-1,3)),**kw)
save_hulls(out,parts)
print('RESULT',src,'->',out,kw,'V',len(v),'F',len(f),'hulls',len(parts),'sec %.0f'%(time.time()-t),flush=True)
