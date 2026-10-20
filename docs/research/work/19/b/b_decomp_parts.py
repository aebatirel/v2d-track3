# Exact FlashCHORD call on every part mesh of an object (one coacd.run_coacd per part = one <collision> mesh each),
# then concatenate all hulls into <outdir>/<name>.npz. usage: b_decomp_parts.py partsdir name outdir
import sys, os, glob, time, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
pd_,n,od=sys.argv[1],sys.argv[2],sys.argv[3]; os.makedirs(od,exist_ok=True); os.makedirs(f'{pd_}/hulls',exist_ok=True)
coacd.set_log_level('info'); allp=[]; t0=time.time()
for p in sorted(glob.glob(f'{pd_}/{n}_p*.npz')):
    hp=f'{pd_}/hulls/'+os.path.basename(p)
    if not os.path.exists(hp):
        d=np.load(p); parts=coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'],dtype=np.float64),np.ascontiguousarray(d['f'],dtype=np.int64)),threshold=0.05,max_convex_hull=-1,preprocess_mode='auto')
        save_hulls(hp,parts); print('PART',p,'F',len(d['f']),'hulls',len(parts),flush=True)
    dd=np.load(hp); allp+=[(dd[f'v{i}'],dd[f'f{i}']) for i in range(int(dd['n']))]
save_hulls(f'{od}/{n}.npz',allp); print('RESULT',n,pd_,'hulls',len(allp),'sec %.0f'%(time.time()-t0),flush=True)
