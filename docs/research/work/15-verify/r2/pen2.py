# Own penetration metric: points sampled on A's hull surfaces (and on A's scan) -> depth inside the union of B's hulls
# (max over B hulls of the inward distance to the nearest face plane). Both directions. Also the A-scan point's distance to
# B's scan surface (KD-tree on dense B-scan samples) as a scan-vs-scan control.
import sys, re, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R
H=sys.argv[1]  # hull dir
P='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
rng=np.random.default_rng(0)
def hulls(n):
    d=np.load(f'{H}/{n}.npz'); return [d[f'v{i}'] for i in range(int(d['n']))]
def scan(n):
    u=open(f'{P}/urdf/{n}_rigid.urdf').read()
    return trimesh.load(P+'/urdf/'+re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1),force='mesh')
def T(pose):
    x,y,z,qw,qx,qy,qz=pose; M=np.eye(4); M[:3,:3]=R.from_quat([qx,qy,qz,qw]).as_matrix(); M[:3,3]=[x,y,z]; return M
def tr(M,p): return p@M[:3,:3].T+M[:3,3]
def eqs(hv,M):
    out=[]
    for v in hv:
        w=tr(M,v); h=ConvexHull(w); out.append(h.equations)
    return out
def depth(pts,E):
    best=np.full(len(pts),-np.inf)
    for e in E:
        s=pts@e[:,:3].T+e[:,3]; best=np.maximum(best,-s.max(1))
    return np.maximum(best,0)
def hsamp(hv,M,k=1500):
    return np.vstack([tr(M,trimesh.Trimesh(v,ConvexHull(v).simplices).sample(k)) for v in hv])
cache={}
def get(n):
    if n not in cache:
        s=scan(n); cache[n]=(hulls(n),s,s.sample(150000))
    return cache[n]
cases=[(0,0,'white_pot_lid','white_pot'),(2,0,'white_pot_lid','white_pot'),(0,-1,'white_pot_lid','white_pot'),
       (31,0,'mini_sweeper','plastic_dish_rack'),(31,160,'mini_sweeper','plastic_dish_rack'),
       (26,4,'white_pot','plastic_dish_rack'),(27,216,'white_pot','plastic_dish_rack'),
       (12,160,'blue_cup','plastic_dish_rack'),(12,-1,'blue_cup','plastic_dish_rack'),(13,176,'blue_cup','plastic_dish_rack'),(13,-1,'blue_cup','plastic_dish_rack'),
       (11,96,'beige_cup','blue_cup'),(11,-1,'beige_cup','blue_cup'),(12,0,'blue_cup','plastic_dish_rack'),(26,-1,'white_pot','plastic_dish_rack')]
for ep,f,a,b in cases:
    df=pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep); o=df['observation.objects'].iloc[f]
    pose={x['name']:x['pose'] for x in o}
    if a not in pose or b not in pose:
        # control: separated pair from another episode - put B at its own episode pose is not available; skip
        print(ep,f,a,b,'pair not in episode'); continue
    Ma,Mb=T(pose[a]),T(pose[b]); ha,sa,ssa=get(a); hb,sb,ssb=get(b)
    Ea,Eb=eqs(ha,Ma),eqs(hb,Mb)
    pa=hsamp(ha,Ma); pb=hsamp(hb,Mb)
    dab=depth(pa,Eb); dba=depth(pb,Ea)
    sca=tr(Ma,ssa[rng.choice(len(ssa),40000,replace=False)]); dsa=depth(sca,Eb)
    kd=cKDTree(tr(Mb,ssb)); i=np.argmax(dsa); dist=kd.query(sca[i])[0]
    print(f'ep{ep} f{f if f>=0 else len(df)-1} {a} vs {b}: hullA-in-hullsB max {dab.max()*1e3:5.1f} p99 {np.percentile(dab,99)*1e3:4.1f} | '
          f'hullB-in-hullsA max {dba.max()*1e3:5.1f} | scanA-in-hullsB max {dsa.max()*1e3:5.1f} (that point is {dist*1e3:4.1f} mm from B scan)',flush=True)
