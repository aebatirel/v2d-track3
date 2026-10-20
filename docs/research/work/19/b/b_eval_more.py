# B26: GT contact / near-contact states of the objects stage B did not cover. Floor = W2-vs-W2 exact signed distance
# (max over W2A surface samples of depth inside W2B; negative = clearance). Hull variants: per-hull depth (b_eval/pen2
# metric; negative = lower bound of the clearance) and union depth (v_uniondepth2 metric), both directions.
# usage: b_eval_more.py LABEL=dir[,dir2] ...
import sys, os, numpy as np, pandas as pd, trimesh, igl
from scipy.spatial import ConvexHull, cKDTree
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
CASES=[(18,88,'mini_sweeper','mini_dust_pan'),(18,111,'mini_sweeper','mini_dust_pan'),
       (23,278,'wooden_piece_1','wooden_piece_2'),(24,246,'wooden_piece_1','wooden_piece_2')]
EPS,DB,DQ,PAD=5e-5,4e6,0.25e6,0.015
class Obj:
    def __init__(s,path):
        d=np.load(path); s.hv=[d[f'v{i}'] for i in range(int(d['n']))]; s.ch=[ConvexHull(v) for v in s.hv]
        s.H=[(v.min(0),v.max(0),h.equations) for v,h in zip(s.hv,s.ch)]
        s.lo=np.array([h[0] for h in s.H]); s.hi=np.array([h[1] for h in s.H]); s.bc={}; out=[]
        for i,(v,h) in enumerate(zip(s.hv,s.ch)):
            m=trimesh.Trimesh(v,h.simplices,process=False); np.random.seed(100+i); out.append(np.vstack([v[h.vertices],m.sample(max(50,int(m.area*DQ)))]))
        s.S=np.vstack(out)
    def inside_any(s,p,skip=-1,eps=0.0):
        ins=np.zeros(len(p),bool)
        for j,(lo,hi,e) in enumerate(s.H):
            if j==skip: continue
            k=np.where(~ins&np.all((p>=lo-eps)&(p<=hi+eps),1))[0]
            if len(k): ins[k[(p[k]@e[:,:3].T+e[:,3]).max(1)<=eps]]=True
        return ins
    def boundary(s,i):
        if i not in s.bc:
            v,h=s.hv[i],s.ch[i]; m=trimesh.Trimesh(v,h.simplices,process=False); np.random.seed(i)
            p=np.vstack([v[h.vertices],m.sample(max(60,int(m.area*DB)))]); s.bc[i]=p[~s.inside_any(p,skip=i,eps=EPS)]
        return s.bc[i]
    def depth(s,q):
        ph=np.full(len(q),-np.inf)
        for e in [h[2] for h in s.H]: ph=np.maximum(ph,-(q@e[:,:3].T+e[:,3]).max(1))
        ins=ph>0; ud=np.zeros(len(q))
        if ins.any():
            lo,hi=q[ins].min(0)-PAD,q[ins].max(0)+PAD; sel=np.where(np.all((s.hi>=lo)&(s.lo<=hi),1))[0]
            B=np.vstack([s.boundary(i) for i in sel]); ud[ins]=cKDTree(B).query(q[ins])[0]
        return ph*1e3,ud*1e3
def pose(ep,fi):
    df=pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep); return {x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}
_o={}
def obj(d,n):
    for dd in d.split(','):
        p=f'{dd}/{n}.npz'
        if os.path.exists(p):
            if p not in _o: _o[p]=Obj(p)
            return _o[p]
args=sys.argv[1:]
if args and args[0]=='floors':
    for ep,fi,a,b in CASES:
        ps=pose(ep,fi); Ma,Mb=T(ps[a]),T(ps[b]); A=np.load(f'{W}/W2/{a}.npz'); B=np.load(f'{W}/W2/{b}.npz')
        ma=trimesh.Trimesh(A['v'],A['f'],process=False); mb=trimesh.Trimesh(B['v'],B['f'],process=False); np.random.seed(3)
        pa=tr(np.linalg.inv(Mb)@Ma,ma.sample(150000)); pb=tr(np.linalg.inv(Ma)@Mb,mb.sample(150000))
        dab=-igl.signed_distance(pa,B['v'],B['f'])[0]*1e3; dba=-igl.signed_distance(pb,A['v'],A['f'])[0]*1e3
        print(f'W2floor ep{ep} f{fi} {a} vs {b}: W2A-in-W2B max {dab.max():5.1f} | W2B-in-W2A max {dba.max():5.1f}',flush=True)
    args=args[1:]
for arg in args:
    lab,d=arg.split('=',1)
    for ep,fi,a,b in CASES:
        A,Bo=obj(d,a),obj(d,b); ps=pose(ep,fi); Ma,Mb=T(ps[a]),T(ps[b])
        ab=Bo.depth(tr(np.linalg.inv(Mb)@Ma,A.S)); ba=A.depth(tr(np.linalg.inv(Ma)@Mb,Bo.S))
        print(f'{lab:6s} ep{ep} f{fi} {a} vs {b}: hulls {len(A.hv)}/{len(Bo.hv)} A-in-B per-hull {ab[0].max():5.1f} union {ab[1].max():4.1f} | B-in-A per-hull {ba[0].max():5.1f} union {ba[1].max():4.1f}',flush=True)
