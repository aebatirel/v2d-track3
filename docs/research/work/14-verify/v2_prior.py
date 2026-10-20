"""Pass-2 verifier: independent re-implementation of the dig-14 eval-set e_track composition (C1/C2/C3).
Own code; inputs = kit-scored public-GT outcome rows (c2_kit_surf.csv from verifier pass 1; e_mix.csv for PERC_M only).
Eval eps enter via kit object count + note-15 class only. Research only, no inference path."""
import json, itertools
import numpy as np, pandas as pd
W="/Users/aebatirel/Documents/Code/v2d-research/work"
EV=json.load(open("/Users/aebatirel/Documents/Code/v2d-research/kit/v2d_submission_kit/data/track_3_evaluation_objects.json"))["episodes"]
N={int(k):len(v) for k,v in EV.items()}
CL={**{e:"F" for e in (1,8,37,38)},**{e:"P" for e in (3,5,6,10,19,30,32,33)},**{e:"L" for e in (14,15,16,20,25,28,35,36)}}
v=pd.read_csv(f"{W}/14-verify/c2_kit_surf.csv")
# per-episode mean over reps first, then mean over eps of the same nobj
pe=v.groupby(["ep","nobj","model"])[["AUC","SP-SR","MP-SR"]].mean().reset_index()
T=pe.groupby(["model","nobj"])[["AUC","SP-SR","MP-SR"]].mean()
def R(m,n): return T.loc[(m,n)].values
def comp(s,r,Nseed,cont="lag30",fm=("never+good","fall50_tipped+good"),cls=CL,detail=False):
    tot=np.zeros(3); parts={"cont":np.zeros(3),"F":np.zeros(3),"P":np.zeros(3),"L":np.zeros(3)}
    for e,n in N.items():
        c=cls[e]; p=s[c]+(1-s[c])*r**Nseed
        ok=R(cont,n); bad=sum(R(f,n) for f in fm)/len(fm)
        tot+= (1-p)*ok+p*bad
        parts["cont"]+=(1-p)*(1-ok); parts[c]+=p*(1-bad)
    if detail: return tot/20,{k:x/20 for k,x in parts.items()}
    return tot/20
SLO={"F":0,"P":.25,"L":.6}; SHI={"F":.05,"P":.5,"L":.9}
def rng(slist,rlist,Nseed,cont,fms):
    vals=np.array([comp(s,r,Nseed,cont,fm) for s in slist for r in rlist for fm in fms])
    return vals.min(0),vals.max(0)
FMS=[("never+good","freeze50+good"),("never+good","fall50_tipped+good")]
def fmt(lo,hi): return " / ".join(f"{a:.3f}-{b:.3f}" for a,b in zip(lo,hi))
out=[]
for name,cont,rr,Ns in [("real 1 seed","lag30",(0.2,0.45),1),("real best3","lag30",(0.2,0.45),3),
                         ("headroom 1 seed","good",(0.11,0.25),1),("headroom best3","good",(0.11,0.25),3)]:
    out.append(f"{name:16s} note15 s lo..hi : "+fmt(*rng([SLO,SHI],rr,Ns,cont,FMS)))
    out.append(f"{name:16s} s halved (dig: S_LO/2..S_LO) : "+fmt(*rng([{k:x/2 for k,x in SLO.items()},SLO],rr,Ns,cont,FMS)))
    out.append(f"{name:16s} s halved (true: S_LO/2..S_HI/2): "+fmt(*rng([{k:x/2 for k,x in SLO.items()},{k:x/2 for k,x in SHI.items()}],rr,Ns,cont,FMS)))
    out.append(f"{name:16s} class-blind s=0 : "+fmt(*rng([{"F":0,"P":0,"L":0}],rr,Ns,cont,FMS)))
    # 36 as borderline -> P instead of L
    cl2=dict(CL); cl2[36]="P"
    vals=np.array([comp(s,r,Ns,cont,fm,cl2) for s in (SLO,SHI) for r in rr for fm in FMS])
    out.append(f"{name:16s} note15, 36->P   : "+fmt(vals.min(0),vals.max(0)))
# all-fail values for each fail model separately (p=1)
for fm in ["never+good","freeze50+good","fall50_tipped+good","fall50_tipped","never","fall50_upright"]:
    a=sum(R(fm,n) for n in N.values())/20
    out.append(f"all-fail eval-composition, ONLY {fm:20s}: AUC {a[0]:.3f} SP {a[1]:.3f} MP {a[2]:.3f}")
# C3 decomposition at mid params
mid={"F":.025,"P":.375,"L":.75}
for fm in FMS:
    t,parts=comp(mid,0.325,1,"lag30",fm,detail=True)
    L=1-t
    out.append(f"mid decomposition fm={fm[1]}: total {np.round(t,3)} loss {np.round(L,3)}; "+"; ".join(f"{k} {np.round(x,3)} ({np.round(100*x/np.where(L>0,L,1),0)}%)" for k,x in parts.items()))
    t3=comp(mid,0.325,3,"lag30",fm); t0=comp({"F":0,"P":0,"L":0},0.325,1,"lag30",fm); t03=comp({"F":0,"P":0,"L":0},0.325,3,"lag30",fm)
    out.append(f"   best3 gain note15 {np.round(t3-t,3)} ; class-blind best3 gain {np.round(t03-t0,3)}")
# fail-row AUC by nobj
for fm in ["never+good","freeze50+good","fall50_tipped+good"]:
    out.append(f"fail row {fm}: 1-obj {np.round(R(fm,1),3)} 2-obj {np.round(R(fm,2),3)}")
out.append(f"lag30 row: 1-obj {np.round(R('lag30',1),3)} 2-obj {np.round(R('lag30',2),3)}; good: 1-obj {np.round(R('good',1),3)} 2-obj {np.round(R('good',2),3)}")
txt="\n".join(out); print(txt); open(f"{W}/14-verify/v2_prior.txt","w").write(txt+"\n")
