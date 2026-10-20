"""Independent re-derivation of the wrist-residual saturation proxy (C3). Own loader, own differentiator."""
import glob, json, sys
import numpy as np, pyarrow.parquet as pq
from scipy.ndimage import gaussian_filter1d
PUB="/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000"
KP,KD,MH,MO,G,CLIP=25.0,6.0,1.243,float(sys.argv[1]) if len(sys.argv)>1 else 0.3,9.81,0.2
SIG=float(sys.argv[2]) if len(sys.argv)>2 else 1.5
dt=1/20.
def load(f):
    t=pq.read_table(f); names=json.loads(t.schema.metadata[b"objects"]); d=t.to_pandas().sort_values("frame_index")
    P=np.zeros((len(d),len(names),3)); Q=np.zeros((len(d),len(names),4))
    for i,objs in enumerate(d["observation.objects"]):
        for o in objs:
            j=names.index(o["name"]); p=np.asarray(o["pose"],float); P[i,j]=p[:3]; Q[i,j]=p[3:]
    return int(d.episode_index.iloc[0]),names,P,Q
def angvel(q):
    d=np.abs(np.sum(q[1:]*q[:-1],-1)).clip(0,1); return np.r_[0,2*np.arccos(d)]/dt
res={1.0:[],0.5:[]}; nobj=0
for f in sorted(glob.glob(PUB+"/*.parquet")):
    ep,names,P,Q=load(f)
    for j,n in enumerate(names):
        x=gaussian_filter1d(P[:,j],SIG,axis=0,mode="nearest")
        v=np.gradient(x,dt,axis=0); a=np.gradient(v,dt,axis=0)
        w=gaussian_filter1d(angvel(Q[:,j]),SIG,mode="nearest")
        sp=np.linalg.norm(v,axis=1); mov=(sp>0.05)|(w>np.radians(30))
        lifted=P[:,j,2]>np.percentile(P[:,j,2],5)+0.01   # above its resting height by >1 cm
        if mov.sum()<5: continue
        nobj+=1
        for s in (1.0,0.5):
            F=(MH+MO)*a*s*s+KD*v*s+np.array([0,0,MO*G]); dpos=np.linalg.norm(F,axis=1)/KP
            drot=KD*w*s/KP
            res[s].append((ep,n,mov.sum(),(dpos[mov]>CLIP).sum(),(mov&lifted).sum(),(dpos[mov&lifted]>CLIP).sum(),(drot[mov]>1.0).sum(),dpos[mov].max()))
print(f"mass {MO} sigma {SIG} moving tracks {nobj}")
for s in (1.0,0.5):
    r=res[s]; nm=sum(x[2] for x in r); ns=sum(x[3] for x in r); nl=sum(x[4] for x in r); nsl=sum(x[5] for x in r)
    print(f"s={s}: tracks with pos sat {sum(x[3]>0 for x in r)}/{len(r)}; frame frac {ns/nm:.4f} ({ns}/{nm}); "
          f"lifted-only frac {nsl/max(nl,1):.4f} ({nsl}/{nl}); rot-sat tracks {sum(x[6]>0 for x in r)}; max dpos {max(x[7] for x in r):.3f}")
