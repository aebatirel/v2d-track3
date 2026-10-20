# Where are the initial grid cells whose own convex hull is far outside W2? (diagnostic for c_hmerge)
import sys, numpy as np
src=open('/Users/aebatirel/Documents/Code/v2d-research/work/19/c/c_hmerge.py').read()
head=src.split("t0 = time.time()")[0]
sys.argv=['x',sys.argv[1],sys.argv[2],'1','6','/tmp/none','10']; g={}; exec(head,g)
V,cell,marg,cost=g['V'],g['cell'],g['marg'],g['cost']
vmin=V.min(0)-marg; k=np.floor((V-vmin)/cell).astype(np.int64)
cid,inv=np.unique(k,axis=0,return_inverse=True); inv=inv.ravel()
res=[]
for i in range(len(cid)):
    P=V[inv==i]
    if len(P)<4: continue
    c,_=cost(P); res.append((c,*(P.mean(0)*1e3),len(P)))
res=np.array(res); o=np.argsort(-res[:,0])
print(f'{len(res)} cells (no margin), cost median {np.median(res[:,0]):.2f} p99 {np.percentile(res[:,0],99):.2f} max {res[:,0].max():.2f}')
for r in res[o[:15]]: print('  cost %.2f mm at (%.0f, %.0f, %.0f) mm, %d verts'%tuple(r))
