# [D] Independent basin analysis. Own re-implementation of the kit's per-start trimmed ICP (written from the kit docstring/
# algorithm, not from mesh_metric.py or the other agent's margin.py), plus the kit's own _register_object_body as a cross-check
# of the winner. Reference = kit packer budget_mesh(scan, 4096, 4096) (or the raw scan with --raw). Seeds = kit pose-board seeds.
import sys, math, json, time, importlib.util, numpy as np
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
K=f'{S}/kit/v2d_submission_kit'; sys.path.insert(0,K)
from v2dlb.mesh_budget import budget_mesh
from v2dlb.mesh_common import _sample_mesh_surface
from v2dlb.vertices import sample_vertices
spec=importlib.util.spec_from_file_location('auc',f'{K}/metric_code/track_3/AUC.py'); auc=importlib.util.module_from_spec(spec); spec.loader.exec_module(auc)
import trimesh
SCAN=f'{S}/loc/t3/mesh/mini_sweeper/mini_sweeper_visual.glb'
def load(p, raw=False):
    if raw:
        m=trimesh.load(p,force='mesh',process=False); return np.asarray(m.vertices,float), np.asarray(m.faces,np.int64)
    v,f=budget_mesh(p,4096,4096); return np.asarray(v,float), np.asarray(f,np.int64)
def moments(v,f):   # area-weighted surface centroid + RMS radius, own implementation (vertex-triangle integral)
    T=v[f]; A=0.5*np.linalg.norm(np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]),axis=1); k=A>1e-12; T,A=T[k],A[k]
    c=(T.mean(1)*A[:,None]).sum(0)/A.sum(); X=T-c
    sq=(X**2).sum(2).sum(1); cr=(X[:,0]*X[:,1]).sum(1)+(X[:,0]*X[:,2]).sum(1)+(X[:,1]*X[:,2]).sum(1)
    return c, math.sqrt((A*(sq+cr)/6).sum()/A.sum())
def pca(P):
    X=P-P.mean(0); w,V=np.linalg.eigh(X.T@X/len(X)); B=V[:,::-1].copy()
    if np.linalg.det(B)<0: B[:,-1]*=-1
    return B
def starts(ref,cand):
    import itertools
    Br,Bc=pca(ref),pca(cand); out=[np.eye(3)]; seen={tuple(np.round(np.eye(3),10).ravel())}
    for perm in itertools.permutations(range(3)):
        Pm=np.eye(3)[:,perm]
        for sg in itertools.product((-1.,1.),repeat=3):
            M=Pm@np.diag(sg)
            if np.linalg.det(M)<=0: continue
            Rr=Br@M@Bc.T
            if np.linalg.det(Rr)<0: continue
            key=tuple(np.round(Rr,10).ravel())
            if key in seen: continue
            seen.add(key); out.append(Rr)
            if len(out)>=25: return out
    return out
def kabsch(A,B):
    ca,cb=A.mean(0),B.mean(0); U,_,Vt=np.linalg.svd((A-ca).T@(B-cb)); R=Vt.T@U.T
    if np.linalg.det(R)<0: Vt=Vt.copy(); Vt[-1]*=-1; R=Vt.T@U.T
    return R, cb-R@ca
def symd(a,b): return 0.5*(cKDTree(a).query(b)[0].mean()+cKDTree(b).query(a)[0].mean())
def icp(ref,cand,R0):
    T=cKDTree(ref); R=R0.copy(); t=ref.mean(0)-R@cand.mean(0); prev=math.inf
    for _ in range(40):
        X=cand@R.T+t; d,i=T.query(X); k=max(3,int(math.ceil(len(d)*0.9))); ch=np.argpartition(d,k-1)[:k]
        r,tt=kabsch(X[ch],ref[i[ch]]); R=r@R; t=r@t+tt; e=float(d[ch].mean())
        if math.isfinite(prev) and abs(prev-e)<=1e-8*max(prev,1.0): break
        prev=e
    return R,t,symd(ref,cand@R.T+t)
def ang(R): return math.degrees(math.acos(max(-1,min(1,(np.trace(R)-1)/2))))
def axis(R):
    w,V=np.linalg.eig(R); a=np.real(V[:,np.argmin(abs(w-1))]); return a/np.linalg.norm(a)
label, path = sys.argv[1], sys.argv[2]; raw_ref = '--raw' in sys.argv
rv,rf=load(SCAN, raw=raw_ref); cv,cf=load(path)
rc,rr=moments(rv,rf); cc,cr=moments(cv,cf)
kc,kr=auc._surface_moments(rv,rf); assert np.allclose(kc,rc) and abs(kr-rr)<1e-9
anchor=rc; q=sample_vertices(SCAN)-anchor
seeds=[19000057,30000090,11,22,33,44]+list(range(1001,1025))
rows=[]
for s in seeds:
    cp=(_sample_mesh_surface(cv,cf,3000,s)-cc)*(rr/cr); rp=_sample_mesh_surface(rv,rf,3000,s)-rc
    res=[icp(rp,cp,R0) for R0 in starts(rp,cp)]
    sc=np.array([r[2] for r in res]); an=np.array([ang(r[0]) for r in res])
    w=int(np.argmin(sc)); R,t,_=res[w]
    ok=sc[an<90].min() if (an<90).any() else np.inf; fl=sc[an>90].min() if (an>90).any() else np.inf
    ca=cc+R.T@(anchor-rc-t)/(rr/cr)
    add=float(np.linalg.norm((ca-anchor)+q@R-q,axis=1).mean())
    # kit's own function as cross-check of the winner
    ka,kR=auc._register_object_body((cv,cf),(rv,rf),anchor,s)
    rows.append(dict(seed=s, win_deg=round(ang(R),2), win_axis=np.round(axis(R),3).tolist() if ang(R)>90 else None, kit_deg=round(ang(kR),2),
                     ok_mm=round(ok*1e3,4), flip_mm=round(fl*1e3,4), margin_mm=round((fl-ok)*1e3,4), add_mm=round(add*1e3,2), n_flip_starts=int((an>90).sum())))
    print(label, rows[-1], flush=True)
fl=[r for r in rows if r['win_deg']>90]
summ=dict(label=label, path=path, ref='raw' if raw_ref else 'budget4096', n=len(rows), flips=len(fl), flips_roster=sum(r['win_deg']>90 for r in rows[:6]), flips_extra=sum(r['win_deg']>90 for r in rows[6:]),
          kit_agrees=all((r['win_deg']>90)==(r['kit_deg']>90) for r in rows),
          margin_min=min(r['margin_mm'] for r in rows), margin_med=float(np.median([r['margin_mm'] for r in rows])), margin_roster=[r['margin_mm'] for r in rows[:6]],
          add_med=float(np.median([r['add_mm'] for r in rows])), add_roster=[r['add_mm'] for r in rows[:2]], time=time.strftime('%H:%M:%S'))
print('SUMMARY', json.dumps(summ))
with open(f'{S}/diag/sweeper_verify/basins.jsonl','a') as fh: fh.write(json.dumps(dict(summary=summ, rows=rows))+'\n')
