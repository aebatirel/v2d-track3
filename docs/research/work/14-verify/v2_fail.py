"""Pass-2: harsher/alternative failure models scored with the kit (own composition), to test the 'SP-SR >= 0.58 even if all fail' bound.
Reuses pass-1 verifier helpers (c2_kit.py, verifier-owned) up to its main loop. Public GT only; research, no inference."""
import sys
src=open("c2_kit.py").read().split("\nrows=[]")[0]
sys.argv=["x","surf"]; exec(src)
def all_objs(fn_one):
    # apply a one-object failure to EVERY object that moves (both objects fail in 2-object eps)
    def f(P,rng):
        o=P.copy()
        for j in range(P.shape[1]):
            if moving(P,j).sum()<3: continue
            sub=P[:,[j]]; r=fn_one(sub,rng); o[:,j]=r[:,0]
        return o
    return f
NEW={"fall20_tipped+good":comp(GOOD,drop_at(0.2,"tipped")),"fall80_tipped+good":comp(GOOD,drop_at(0.8,"tipped")),
     "ALL_never+good":comp(GOOD,all_objs(m_never)),"ALL_fall50_tipped+good":comp(GOOD,all_objs(drop_at(0.5,"tipped"))),
     "ALL_fall20_tipped+good":comp(GOOD,all_objs(drop_at(0.2,"tipped")))}
rows=[]
for ep,names,P in EPS:
    for mn,fn in NEW.items():
        for r in range(2):
            rng=np.random.default_rng(97*ep+r)
            rows.append(dict(ep=ep,nobj=len(names),model=mn,rep=r,**score(ep,names,P,fn(P,rng))))
df=pd.DataFrame(rows); df.to_csv("v2_fail.csv",index=False)
pe=df.groupby(["ep","nobj","model"])[["AUC","SP-SR","MP-SR"]].mean().reset_index()
print(pe.groupby(["model","nobj"])[["AUC","SP-SR","MP-SR"]].mean().round(3).to_string())
