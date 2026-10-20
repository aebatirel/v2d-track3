# One-off helper: exact call on named part files (atomic write). usage: b_one.py part.npz [...]
import sys, os, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
for p in sys.argv[1:]:
    hp=os.path.join(os.path.dirname(p),'hulls',os.path.basename(p))
    if os.path.exists(hp): continue
    d=np.load(p); parts=coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'],dtype=np.float64),np.ascontiguousarray(d['f'],dtype=np.int64)),threshold=0.05,max_convex_hull=-1,preprocess_mode='auto')
    tmp=hp[:-4]+'.tmp.npz'; save_hulls(tmp,parts); os.replace(tmp,hp); print('PART',p,'hulls',len(parts),flush=True)
