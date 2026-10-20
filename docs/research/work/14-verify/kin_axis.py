"""Per-axis version of the saturation proxy (C3): wrist residual clamp is per world axis (hand_pose.py:408)."""
import glob, json, sys
import numpy as np, pyarrow.parquet as pq
from scipy.ndimage import gaussian_filter1d
PUB="/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000"
KP,KD,MH,G,CLIP=25.0,6.0,1.243,9.81,0.2
MO=float(sys.argv[1]); SIG=float(sys.argv[2]); dt=1/20.
def load(f):
    t=pq.read_table(f); names=json.loads(t.schema.metadata[b"objects"]); d=t.to_pandas().sort_values("frame_index")
    P=np.zeros((len(d),len(names),3)); Q=np.zeros((len(d),len(names),4))
    for i,objs in enumerate(d["observation.objects"]):
        for o in objs:
            j=names.index(o["name"]); p=np.asarray(o["pose"],float); P[i,j]=p[:3]; Q[i,j]=p[3:]
    return int(d.episode_index.iloc[0]),names,P,Q
def angvel(q):
    d=np.abs(np.sum(q[1:]*q[:-1],-1)).clip(0,1); return np.r_[0,2*np.arccos(d)]/dt
for s in (1.0,0.5):
    trk=0; nm=0; ns=0; nz=0; exc=[]; ntr=0
    for f in sorted(glob.glob(PUB+"/*.parquet")):
        ep,names,P,Q=load(f)
        for j,n in enumerate(names):
            x=gaussian_filter1d(P[:,j],SIG,axis=0,mode="nearest"); v=np.gradient(x,dt,axis=0); a=np.gradient(v,dt,axis=0)
            w=gaussian_filter1d(angvel(Q[:,j]),SIG,mode="nearest"); sp=np.linalg.norm(v,axis=1)
            mov=(sp>0.05)|(w>np.radians(30))
            if mov.sum()<5: continue
            ntr+=1
            F=(MH+MO)*a*s*s+KD*v*s+np.array([0,0,MO*G]); d=np.abs(F)/KP     # per-axis offset demand
            sat=(d>CLIP).any(1)&mov
            nm+=mov.sum(); ns+=sat.sum(); nz+=((d[:,2]>CLIP)&mov).sum(); trk+=sat.any()
            e=(np.maximum(d-CLIP,0)).max(1)[sat]; exc+=list(e)
    exc=np.array(exc) if exc else np.zeros(1)
    print(f"mass {MO} sig {SIG} s={s}: tracks sat {trk}/{ntr}; frames {ns}/{nm}={ns/nm:.4f} (z-axis {nz}); "
          f"excess over clip on sat frames: median {100*np.median(exc):.1f} cm, p95 {100*np.percentile(exc,95):.1f} cm, max {100*exc.max():.1f} cm")
