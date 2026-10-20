# Stage B evaluation (own code, same depth definition as note-15 work/15-verify/r2/pen2.py):
#  depth of a point inside a union of convex hulls = max over hulls of min over facets of the inward plane distance.
# (1) per object: hull outward deviation (hull vertices + surface samples, signed distance to the scan with
#     pseudonormal sign and to the W2 reference solid; + = outside) and scan coverage (scan samples outside the hulls).
# (2) GT contact states (pen2 case list): hullA-in-hullsB, hullB-in-hullsA, scanA-in-hullsB, plus floors with the
#     W2 solids (W2A surface in W2B), i.e. what exact (non-inflated) colliders would give.
# usage: b_eval.py obj|pairs LABEL=hulldir [LABEL=hulldir ...]
import sys, os, numpy as np, pandas as pd, trimesh, igl
from scipy.spatial import ConvexHull
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
rng=np.random.default_rng(0); DENS=0.25e6   # samples per m^2 (1 per 4 mm^2)
OBJ=['white_pot_lid','white_pot','mini_sweeper','plastic_dish_rack','blue_cup','beige_cup']
CASES=[(0,0,'white_pot_lid','white_pot'),(2,0,'white_pot_lid','white_pot'),(0,-1,'white_pot_lid','white_pot'),
       (31,0,'mini_sweeper','plastic_dish_rack'),(31,160,'mini_sweeper','plastic_dish_rack'),
       (26,4,'white_pot','plastic_dish_rack'),(27,216,'white_pot','plastic_dish_rack'),
       (12,160,'blue_cup','plastic_dish_rack'),(12,-1,'blue_cup','plastic_dish_rack'),(13,176,'blue_cup','plastic_dish_rack'),
       (13,-1,'blue_cup','plastic_dish_rack'),(11,96,'beige_cup','blue_cup'),(11,-1,'beige_cup','blue_cup')]
_c={}
def C(k,f):
    if k not in _c: _c[k]=f()
    return _c[k]
def scan(n): return C(('s',n),lambda: scan_welded(n))
def W2(n):
    d=C(('w',n),lambda: np.load(f'{W}/W2/{n}.npz')); return d['v'],d['f']
def hulls(d,n):   # d may be 'dirA,dirB,...': first dir holding <n>.npz wins
    for dd in d.split(','):
        p=f'{dd}/{n}.npz'
        if os.path.exists(p): return C(('h',p),lambda: load_hulls(p))
    return None
def hsamp(hv):   # hull vertices + area samples (local frame)
    out=[]
    for v in hv:
        hh=ConvexHull(v); m=trimesh.Trimesh(v,hh.simplices,process=False); k=max(50,int(m.area*DENS))
        out.append(np.vstack([v[hh.vertices],samp(m,k,0)]))
    return np.vstack(out)
def samp(m,k,s):
    np.random.seed(s); return m.sample(k)
def eqs(hv,M=None): return [ConvexHull(v if M is None else tr(M,v)).equations for v in hv]
def depth_in(pts,hv,M):   # positive depth only (pairs), AABB-prefiltered per hull; 0 where outside all hulls
    best=np.zeros(len(pts))
    for v in hv:
        w=tr(M,v); lo,hi=w.min(0),w.max(0); k=np.where(np.all((pts>=lo)&(pts<=hi),1))[0]
        if len(k)==0: continue
        e=ConvexHull(w).equations; s=pts[k]@e[:,:3].T+e[:,3]; best[k]=np.maximum(best[k],-s.max(1))
    return best
def depth(pts,E,lo=None,hi=None):
    best=np.full(len(pts),-np.inf)
    for e in E:
        s=pts@e[:,:3].T+e[:,3]; best=np.maximum(best,-s.max(1))
    return best     # >0 inside (depth), <0 outside (lower bound of the distance to the union)
def objstats(lab,d,n):
    hv=hulls(d,n)
    if hv is None: return
    m=scan(n); V,F=np.asarray(m.vertices),np.asarray(m.faces,np.int64); WV,WF=W2(n)
    P=hsamp(hv); s_scan=igl.signed_distance(P,V,F,igl.SIGNED_DISTANCE_TYPE_PSEUDONORMAL)[0]*1e3
    s_w=igl.signed_distance(P,WV,WF)[0]*1e3
    q=samp(m,60000,1); dq=np.full(len(q),5e-3)   # >0: scan point outside all hulls (lower bound, capped at 5 mm)
    for v in hv:
        lo,hi=v.min(0)-5e-3,v.max(0)+5e-3; k=np.where(np.all((q>=lo)&(q<=hi),1))[0]
        if len(k)==0: continue
        e=ConvexHull(v).equations; dq[k]=np.minimum(dq[k],np.maximum((q[k]@e[:,:3].T+e[:,3]).max(1),0))
    dq*=1e3
    nv=sum(len(ConvexHull(v).vertices) for v in hv)
    print(f'{lab:10s} {n:18s} hulls {len(hv):4d} hullverts {nv:6d} >64v {sum(len(ConvexHull(v).vertices)>64 for v in hv):3d} | hull-vs-scan mm p95 {np.percentile(s_scan,95):5.2f} p99 {np.percentile(s_scan,99):5.2f} max {s_scan.max():5.2f}'
          f' | hull-vs-W2 p99 {np.percentile(s_w,99):5.2f} max {s_w.max():5.2f} | scan uncovered >1mm {np.mean(dq>1)*100:5.2f}% max {dq.max():5.2f}',flush=True)
def pairs(lab,d):
    for ep,f,a,b in CASES:
        ha,hb=hulls(d,a),hulls(d,b)
        if ha is None or hb is None: continue
        df=C(('p',ep),lambda: pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep)); fi=f if f>=0 else len(df)-1
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma,Mb=T(pose[a]),T(pose[b])
        pa=tr(Ma,C(('hs',d,a),lambda: hsamp(ha))); pb=tr(Mb,C(('hs',d,b),lambda: hsamp(hb)))
        dab=depth_in(pa,hb,Mb)*1e3; dba=depth_in(pb,ha,Ma)*1e3
        sa=tr(Ma,C(('ss',a),lambda: samp(scan(a),40000,2))); dsa=depth_in(sa,hb,Mb)*1e3
        print(f'{lab:10s} ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: hullA-in-hullsB max {dab.max():5.1f} p99 {max(0,np.percentile(dab,99)):4.1f} | '
              f'hullB-in-hullsA max {dba.max():5.1f} | scanA-in-hullsB max {dsa.max():5.1f}',flush=True)
def floors():
    for ep,f,a,b in CASES:
        df=C(('p',ep),lambda: pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep)); fi=f if f>=0 else len(df)-1
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma,Mb=T(pose[a]),T(pose[b])
        Wa,Wb=W2(a),W2(b); A=trimesh.Trimesh(*Wa,process=False); Bm=trimesh.Trimesh(*Wb,process=False)
        pa=tr(Ma,samp(A,150000,3)); pb=tr(Mb,samp(Bm,150000,3))
        Mbi=np.linalg.inv(Mb); Mai=np.linalg.inv(Ma)
        dab=-igl.signed_distance(tr(Mbi,pa),*Wb)[0]*1e3; dba=-igl.signed_distance(tr(Mai,pb),*Wa)[0]*1e3
        m=scan(a); sa=tr(Ma,samp(m,40000,2)); dsa=-igl.signed_distance(tr(Mbi,sa),*Wb)[0]*1e3
        print(f'{"W2floor":10s} ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: W2A-in-W2B max {dab.max():5.1f} p99 {max(0,np.percentile(dab,99)):4.1f} | '
              f'W2B-in-W2A max {dba.max():5.1f} | scanA-in-W2B max {dsa.max():5.1f}',flush=True)
CASES2=[(0,28,'white_pot_lid','white_pot'),(2,314,'white_pot_lid','white_pot'),(11,124,'beige_cup','blue_cup'),
        (12,168,'blue_cup','plastic_dish_rack'),(13,130,'blue_cup','plastic_dish_rack'),(26,12,'white_pot','plastic_dish_rack'),
        (27,218,'white_pot','plastic_dish_rack'),(31,238,'mini_sweeper','plastic_dish_rack')]
mode=sys.argv[1] if __name__=="__main__" else ""
if mode in ('pairs2','floors2'): CASES[:]=CASES2; mode=mode[:-1]
if mode=='floors': floors()
for a in sys.argv[2:]:
    lab,d=a.split('=',1)
    if mode=='obj':
        for n in OBJ: objstats(lab,d,n)
    elif mode=='pairs': pairs(lab,d)
