# Independent penetration check of public-GT contact states against CoACD hulls (two metrics).
import sys, os, re, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
HD=os.environ.get('HD','hulls11')
def load_hulls(n):
    z=np.load(f'{HD}/{n}.npz'); return [(z[f'v{i}'].astype(float),z[f'f{i}'].reshape(-1,3)) for i in range(int(z['n']))]
def planes(v):
    h=ConvexHull(v); return h.equations  # n.x + d <= 0 inside
def pose(ep,f,name):
    fr=pd.read_parquet(f'{D}/data/chunk-000/episode_{ep:06d}.parquet',columns=['observation.objects'])['observation.objects'].iloc[f]
    p=[o['pose'] for o in fr if o['name']==name][0]
    return Rot.from_quat([p[4],p[5],p[6],p[3]]).as_matrix(), np.array(p[:3],float)
def to_b(P,Ra,ta,Rb,tb): return ((P@Ra.T+ta)-tb)@Rb
def depth_in(P,PL):
    best=np.zeros(len(P))
    for e in PL: best=np.maximum(best,-(P@e[:,:3].T+e[:,3]).max(1))
    return best
def sat_pd(va,ea,vb,eb):
    # upper bound on penetration depth using face normals of both hulls; 0 if separated
    ax=np.vstack([ea[:,:3],eb[:,:3]])
    pa=va@ax.T; pb=vb@ax.T
    ov=np.minimum(pa.max(0)-pb.min(0), pb.max(0)-pa.min(0))
    return max(0.0, ov.min())
def scan(n):
    u=open(f'{D}/urdf/{n}_rigid.urdf').read(); cf=re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1)
    return trimesh.load(os.path.normpath(os.path.join(D,'urdf',cf)),force='mesh')
def run(ep,f,a,b):
    Ha=load_hulls(a); Hb=load_hulls(b); Ea=[planes(v) for v,_ in Ha]; Eb=[planes(v) for v,_ in Hb]
    Ra,ta=pose(ep,f,a); Rb,tb=pose(ep,f,b)
    rng=np.random.default_rng(1)
    hullmesh=trimesh.util.concatenate([trimesh.Trimesh(v,fc) for v,fc in Ha])
    Ps,_=trimesh.sample.sample_surface(hullmesh,60000,seed=1)
    d_hh=depth_in(to_b(Ps,Ra,ta,Rb,tb),Eb)
    Ss,_=trimesh.sample.sample_surface(scan(a),60000,seed=1)
    d_sh=depth_in(to_b(Ss,Ra,ta,Rb,tb),Eb)
    # SAT per hull pair (A hull verts expressed in B frame)
    best=0; nov=0
    for (va,_),ea in zip(Ha,Ea):
        vab=to_b(va,Ra,ta,Rb,tb); eab=planes(vab)
        lo,hi=vab.min(0),vab.max(0)
        for (vb,_),eb in zip(Hb,Eb):
            if np.any(vb.min(0)>hi) or np.any(vb.max(0)<lo): continue
            pd_=sat_pd(vab,eab,vb,eb)
            if pd_>0: nov+=1
            best=max(best,pd_)
    print(f'{HD} ep{ep} f{f} {a}->{b}: Ahull-in-Bhull max {d_hh.max()*1e3:.1f} p99 {np.percentile(d_hh,99)*1e3:.1f} | '
          f'Ascan-in-Bhull max {d_sh.max()*1e3:.1f} p99 {np.percentile(d_sh,99)*1e3:.1f} | SAT-PD max {best*1e3:.1f} mm, overlapping hull pairs {nov}',flush=True)
for s in sys.argv[1:]:
    ep,f,a,b=s.split(':'); ep=int(ep)
    if f=='end': f=len(pd.read_parquet(f'{D}/data/chunk-000/episode_{ep:06d}.parquet',columns=['frame_index']))-1
    run(ep,int(f),a,b)
