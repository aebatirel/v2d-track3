"""Pass-2: per-axis saturation proxy restricted to LIFTED frames (object z > rest z + 2 cm), to drop on-table drags where the table carries
the weight. Own variant of kin_axis.py. Research only."""
import glob, json, sys
import numpy as np, pyarrow.parquet as pq
from scipy.ndimage import gaussian_filter1d
PUB="/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000"
KP,KD,MH,G,CLIP=25.0,6.0,1.231,9.81,0.2; dt=1/20.
MO=float(sys.argv[1]); SIG=float(sys.argv[2]); LIFT=float(sys.argv[3]) if len(sys.argv)>3 else 0.02
def load(f):
    t=pq.read_table(f); names=json.loads(t.schema.metadata[b"objects"]); d=t.to_pandas().sort_values("frame_index")
    P=np.zeros((len(d),len(names),3)); Q=np.zeros((len(d),len(names),4))
    for i,objs in enumerate(d["observation.objects"]):
        for o in objs:
            j=names.index(o["name"]); p=np.asarray(o["pose"],float); P[i,j]=p[:3]; Q[i,j]=p[3:]
    return names,P,Q
def angvel(q):
    d=np.abs(np.sum(q[1:]*q[:-1],-1)).clip(0,1); return np.r_[0,2*np.arccos(d)]/dt
for s in (1.0,0.5):
    trk=ntr=nm=ns=nl=0
    for f in sorted(glob.glob(PUB+"/*.parquet")):
        names,P,Q=load(f)
        for j in range(len(names)):
            x=gaussian_filter1d(P[:,j],SIG,axis=0,mode="nearest"); v=np.gradient(x,dt,axis=0); a=np.gradient(v,dt,axis=0)
            w=gaussian_filter1d(angvel(Q[:,j]),SIG,mode="nearest"); mov=(np.linalg.norm(v,axis=1)>0.05)|(w>np.radians(30))
            if mov.sum()<5: continue
            lifted=P[:,j,2]>np.percentile(P[:,j,2],5)+LIFT
            ntr+=1; nm+=mov.sum(); nl+=(mov&lifted).sum()
            F=(MH+MO)*a*s*s+KD*v*s+np.array([0,0,MO*G]); d=np.abs(F)/KP
            sat=(d>CLIP).any(1)&mov&lifted; ns+=sat.sum(); trk+=sat.any()
    print(f"mass {MO} sig {SIG} lift>{LIFT} s={s}: tracks sat {trk}/{ntr}; sat lifted-moving frames {ns}/{nl}={ns/max(nl,1):.4f} ({ns}/{nm}={ns/nm:.4f} of all moving)")
