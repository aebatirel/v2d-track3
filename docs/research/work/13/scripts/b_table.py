import json, numpy as np
R = json.load(open("out/b_feats.json")); N = [k for k in R if "__" not in k]
EVEN = {"kurt", "skew_se1"}
stats = [k for k in R[N[0]] if not k.startswith("_")]
print("stat            #pos x  #pos y  #pos z   | min|v| over objs x,y,z ; per-object signs x/y/z (+/-)")
for s in stats:
    A = np.array([R[n][s] for n in N])
    tag = "(even)" if s in EVEN else ""
    print(f"{s:14s}{tag:6s} {np.sum(A[:,0]>0):2d}      {np.sum(A[:,1]>0):2d}      {np.sum(A[:,2]>0):2d}    | "
          + " ".join(f"{v:.3g}" for v in np.abs(A).min(0)) + " ; "
          + " ".join("".join("+" if v > 0 else "-" for v in A[:, i]) for i in range(3)))
print("objects:", N)
