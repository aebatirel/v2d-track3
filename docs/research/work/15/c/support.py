# Stage C: classify GT object motion into static / on-table slide-or-pivot / lifted (public GT; analysis only)
import json, glob, numpy as np, pandas as pd, trimesh
from scipy.spatial.transform import Rotation as Rot
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
meta={json.loads(l)['episode_index']:json.loads(l) for l in open(f'{D}/meta/episodes_metadata.jsonl')}
VC={}
def verts(n):
    if n not in VC:
        fs=sorted(glob.glob(f'{D}/mesh/{n}/*.glb')); f=[x for x in fs if 'collision' not in x][0]
        m=trimesh.load(f,force='mesh'); v=m.vertices
        VC[n]=v[np.random.default_rng(0).choice(len(v),min(3000,len(v)),replace=False)]
    return VC[n]
eps=[0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45]
for e in eps:
    df=pd.read_parquet(f'{D}/data/chunk-000/episode_{e:06d}.parquet',columns=['observation.objects'])
    objs=df['observation.objects'].tolist(); names=[o['name'] for o in objs[0]]
    P={n:np.array([[o['pose'] for o in fr if o['name']==n][0] for fr in objs]) for n in names}
    minz={};pos={}
    for n in names:
        p=P[n]; R=Rot.from_quat(np.c_[p[:,4:7],p[:,3]]).as_matrix()
        w=np.einsum('fij,vj->fvi',R,verts(n))+p[:,None,:3]; minz[n]=w[:,:,2].min(1); pos[n]=p[:,:3]
    table=np.median([minz[n][0] for n in names]) if len(names)>1 else minz[names[0]][0]
    table=min(minz[n][0] for n in names)  # lowest frame-0 contact = table
    out=[]
    for n in names:
        p=pos[n]; v=np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1)]*20  # m/s
        mv=v>0.02
        on=minz[n]-table<0.01
        slide=mv&on; lift=mv&~on
        # longest contiguous on-table moving run, xy distance travelled in it
        best=0;bd=0;i=0
        while i<len(slide):
            if slide[i]:
                j=i
                while j<len(slide) and slide[j]: j+=1
                d=np.linalg.norm(p[j-1,:2]-p[i,:2])
                if d>bd: bd=d;best=j-i
                i=j
            else: i+=1
        out.append(f'{n}: mov {mv.sum()} f, on-table-moving {slide.sum()} f, airborne/other-support {lift.sum()} f, '
                   f'longest on-table run {best} f / {bd*100:.1f} cm, minz0-table {100*(minz[n][0]-table):.1f} cm')
    print(e, meta[e].get('task', meta[e].get('tasks','?')) if e in meta else '?', '| table z %.3f'%table); [print('   ',s) for s in out]
