"""Independent re-derivation of C2: policy-outcome models on public GT, scored by calling the kit's own Track 3
score() entry points (AUC, SP-SR, MP-SR) on DataFrames. Own loader, own models, own vertex payload. Research only:
public GT used for analysis; nothing here is an inference path."""
import glob, json, io, base64, importlib.util, sys
import numpy as np, pandas as pd, pyarrow.parquet as pq, trimesh
ROOT="/Users/aebatirel/Documents/Code/v2d-research"; PUB=f"{ROOT}/data/track_3/public"
KIT=f"{ROOT}/kit/v2d_submission_kit/metric_code/track_3"; dt=1/20.
def mod(n):
    s=importlib.util.spec_from_file_location(n.replace("-","_"),f"{KIT}/{n}.py"); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
M={n:mod(n) for n in ["AUC","SP-SR","MP-SR"]}
VMODE=sys.argv[1] if len(sys.argv)>1 else "surf"
def verts(name,n=500):
    import os; pth=f"{PUB}/mesh/{name}/{name}.glb"; pth=pth if os.path.exists(pth) else f"{PUB}/mesh/{name}/{name}_visual.glb"
    m=trimesh.load(pth,force="mesh"); rng=np.random.default_rng(7)
    if VMODE=="surf":
        return trimesh.sample.sample_surface(m,n,seed=7)[0]
    return m.vertices[rng.choice(len(m.vertices),n,replace=len(m.vertices)<n)]
def load(f):
    t=pq.read_table(f); names=json.loads(t.schema.metadata[b"objects"]); d=t.to_pandas().sort_values("frame_index")
    P=np.zeros((len(d),len(names),7))
    for i,objs in enumerate(d["observation.objects"]):
        for o in objs:
            p=np.asarray(o["pose"],float); P[i,names.index(o["name"]),:]=np.r_[p[:3],p[4:7],p[3]]  # -> xyz + xyzw
    return int(d.episode_index.iloc[0]),names,P
EPS=[load(f) for f in sorted(glob.glob(f"{PUB}/data/chunk-000/*.parquet"))]
VB={}
for _,names,_ in EPS:
    for n in names:
        if n not in VB: VB[n]=verts(n)
buf=io.BytesIO(); np.savez(buf,**VB); B64=base64.b64encode(buf.getvalue()).decode()
def frames(ep,names,ref,ach):
    T,N,_=ref.shape; rows=[]
    fi=np.repeat(np.arange(T),N); sl=np.tile(np.arange(N),T)
    base=dict(episode_index=ep,world_index=0,frame_index=fi,object_slot=sl,object_name=np.array(names)[sl])
    sol=pd.DataFrame(base); sub=pd.DataFrame(base)
    rid=[f"{ep}_{a}_{b}" for a,b in zip(fi,sl)]; sol["row_id"]=rid; sub["row_id"]=rid
    cols=["pos_x","pos_y","pos_z","quat_x","quat_y","quat_z","quat_w"]
    for k,c in enumerate(cols):
        sol["ref_"+c]=ref.reshape(-1,7)[:,k]; sub[c]=ach.reshape(-1,7)[:,k]
    sol["auc_vertex_samples_b64"]=""; sol.loc[0,"auc_vertex_samples_b64"]=B64
    for c in ["eval_script_sha256","eval_code_sha256","checkpoint_sha256","packer_script_sha256","uploader_script_sha256"]:
        sub[c]="x"
    sub["code_commit_url"]="https://github.com/a/b/commit/abcdef1"
    return sol,sub
def score(ep,names,ref,ach):
    sol,sub=frames(ep,names,ref,ach)
    return {k:M[k].score(sol,sub,"row_id") for k in M}
# ---- own model implementations ----
def qm(a,b):
    ax,ay,az,aw=np.moveaxis(a,-1,0); bx,by,bz,bw=np.moveaxis(b,-1,0)
    return np.stack([aw*bx+ax*bw+ay*bz-az*by,aw*by-ax*bz+ay*bw+az*bx,aw*bz+ax*by-ay*bx+az*bw,aw*bw-ax*bx-ay*by-az*bz],-1)
def aa(ax,ang):
    ax=np.asarray(ax,float); ax=ax/np.linalg.norm(ax,axis=-1,keepdims=True); ang=np.asarray(ang,float)[...,None]
    return np.concatenate([ax*np.sin(ang/2),np.cos(ang/2)],-1)
def nlerp_slerp(q0,q1,w):
    d=np.sum(q0*q1,-1,keepdims=True); q1=np.where(d<0,-q1,q1); d=np.abs(d).clip(0,1); th=np.arccos(d); s=np.sin(th)
    out=np.where(s<1e-6,(1-w)*q0+w*q1,(np.sin((1-w)*th)*q0+np.sin(w*th)*q1)/np.where(s<1e-6,1,s))
    return out/np.linalg.norm(out,axis=-1,keepdims=True)
def moving(P,j):
    v=np.r_[0,np.linalg.norm(np.diff(P[:,j,:3],axis=0),axis=1)]/dt
    d=np.abs(np.sum(P[1:,j,3:]*P[:-1,j,3:],-1)).clip(0,1); w=np.r_[0,2*np.arccos(d)]/dt
    v=np.convolve(v,np.ones(7)/7,"same"); w=np.convolve(w,np.ones(7)/7,"same")
    return (v>0.04)|(w>np.radians(20))
def most(P): return int(np.argmax([np.linalg.norm(np.diff(P[:,j,:3],axis=0),axis=1).sum() for j in range(P.shape[1])]))
def m_ident(P,rng): return P.copy()
def m_never(P,rng):
    o=P.copy(); j=most(P); o[:,j]=P[0,j]; return o
def drop_at(frac,mode):
    def f(P,rng):
        o=P.copy(); j=most(P); mv=np.where(moving(P,j))[0]
        if not len(mv): return o
        t0=mv[int(frac*(len(mv)-1))]; pose=P[t0,j].copy()
        if mode=="freeze": o[t0:,j]=pose; return o
        pose[2]=P[0,j,2]  # falls to its resting height at the drop xy
        if mode=="upright": pose[3:]=P[0,j,3:]
        if mode=="tipped":
            ax=rng.normal(size=3); ax[2]=0; pose[3:]=qm(aa(ax,np.pi/2),P[0,j,3:])
        o[t0:,j]=pose; return o
    return f
def lag(tau):
    a=dt/(tau+dt)
    def f(P,rng):
        o=P.copy()
        for t in range(1,len(P)):
            o[t,:,:3]=o[t-1,:,:3]+a*(P[t,:,:3]-o[t-1,:,:3]); o[t,:,3:]=nlerp_slerp(o[t-1,:,3:],P[t,:,3:],a)
        return o
    return f
def jit(cm,deg):
    def f(P,rng):
        o=P.copy(); o[...,:3]+=rng.normal(size=P[...,:3].shape)*cm/100
        rv=rng.normal(size=P[...,:3].shape)*np.radians(deg); o[...,3:]=qm(aa(rv+1e-12,np.linalg.norm(rv,axis=-1)),P[...,3:])
        o[0,0]=P[0,0]; return o
    return f
def place(cm,deg):
    def f(P,rng):
        o=P.copy()
        for j in range(P.shape[1]):
            mv=moving(P,j)
            if not mv.any(): continue
            last=len(mv)-int(np.argmax(mv[::-1]))
            d=rng.normal(size=3); d[2]=0; d/=np.linalg.norm(d)
            o[last:,j,:3]+=d*cm/100; o[last:,j,3:]=qm(aa(rng.normal(size=3),np.radians(deg)),P[last:,j,3:])
        return o
    return f
def comp(*fs):
    def f(P,rng):
        for g in fs: P=g(P,rng)
        return P
    return f
GOOD=comp(lag(0.10),jit(0.3,1),place(1.0,3))
MODELS={"ident":m_ident,"good":GOOD,"lag30":lag(0.30),"never":m_never,"never+good":comp(GOOD,m_never),
        "freeze50":drop_at(0.5,"freeze"),"fall50_upright":drop_at(0.5,"upright"),"fall50_tipped":drop_at(0.5,"tipped"),
        "freeze50+good":comp(GOOD,drop_at(0.5,"freeze")),"fall50_tipped+good":comp(GOOD,drop_at(0.5,"tipped"))}
rows=[]
for ep,names,P in EPS:
    for mn,fn in MODELS.items():
        reps=2 if mn in ("good","never+good","freeze50+good","fall50_tipped+good","fall50_tipped") else 1
        for r in range(reps):
            rng=np.random.default_rng(97*ep+r)
            rows.append(dict(ep=ep,nobj=len(names),model=mn,rep=r,**score(ep,names,P,fn(P,rng))))
df=pd.DataFrame(rows); df.to_csv(f"c2_kit_{VMODE}.csv",index=False)
pe=df.groupby(["ep","model"])[["AUC","SP-SR","MP-SR"]].mean().reset_index()
print(f"vertices={VMODE}"); print(pe.groupby("model")[["AUC","SP-SR","MP-SR"]].mean().round(3).to_string())
