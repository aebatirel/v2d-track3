"""Joint family-wise null for b_search families + tail probability of the observed number of fitting rules."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import numpy as np, b_search as B
rng = np.random.default_rng(int(sys.argv[2])); N = int(sys.argv[1])
fams = {"F1": B.fam_F1, "F2": B.fam_F2, "F2b": B.fam_F2b, "F4": B.fam_F4}
obs = {k: int(f(B.D)[0].all(1).sum()) for k, f in fams.items()}; obs["F3"] = B.fam_F3(B.D)[1]
C = {k: [] for k in obs}
for t in range(N):
    flip = rng.random(B.NO) < 0.5
    if not flip.any(): flip[rng.integers(B.NO)] = True
    Dn = B.D.copy(); Dn[:, flip, :2] *= -1
    for k, f in fams.items(): C[k].append(int(f(Dn)[0].all(1).sum()))
    C["F3"].append(B.fam_F3(Dn)[1])
C = {k: np.array(v) for k, v in C.items()}
print("observed #fitting:", obs)
for k in C: print(f"  {k}: P(>=1)={np.mean(C[k]>0):.3f}  P(count>=obs={obs[k]})={np.mean(C[k]>=max(obs[k],1)):.3f}")
anyp = (C["F1"] + C["F2"] + C["F2b"] + C["F4"]) > 0
print(f"  joint F1|F2|F2b|F4: P(>=1 rule fits)={anyp.mean():.3f};  with F3: {np.mean(anyp | (C['F3']>0)):.3f}")
