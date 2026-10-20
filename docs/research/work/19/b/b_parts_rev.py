# Helper worker: exact call on the part meshes of an object in REVERSE order, skipping parts already done; atomic
# writes (tmp + rename) so the forward b_decomp_parts.py never reads a partial file. usage: b_parts_rev.py partsdir name
import sys, os, glob, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
pd_,n=sys.argv[1],sys.argv[2]; coacd.set_log_level('info')
for p in sorted(glob.glob(f'{pd_}/{n}_p*.npz'))[::-1]:
    hp=f'{pd_}/hulls/'+os.path.basename(p)
    if os.path.exists(hp): break      # met the forward worker
    d=np.load(p); parts=coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'],dtype=np.float64),np.ascontiguousarray(d['f'],dtype=np.int64)),threshold=0.05,max_convex_hull=-1,preprocess_mode='auto')
    tmp=hp[:-4]+'.tmp.npz'; save_hulls(tmp,parts); os.replace(tmp,hp); print('PART',p,'F',len(d['f']),'hulls',len(parts),flush=True)
