"""Null distribution of the LOO share-correct for the parameter-free roll families (random roll bits)."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import numpy as np, b_search as B
fams = [B.fam_F1, B.fam_F2, B.fam_F2b, B.fam_F4]
def loo(D):
    ok = np.concatenate([f(D)[0] for f in fams]); sh = []
    for o in range(B.NO):
        m = np.delete(ok, o, 1).all(1)
        if m.any(): sh.append(ok[m, o].mean())
    return np.mean(sh) if sh else np.nan, len(sh)
obs = loo(B.D); rng = np.random.default_rng(11); res = []
for t in range(int(sys.argv[1])):
    f = rng.random(B.NO) < 0.5
    if not f.any(): f[rng.integers(B.NO)] = True
    Dn = B.D.copy(); Dn[:, f, :2] *= -1; res.append(loo(Dn))
v = np.array([r[0] for r in res]); n = np.array([r[1] for r in res])
print(f"observed LOO share {obs[0]:.3f} over {obs[1]} held-outs with >=1 9/9 rule")
print(f"null: mean {np.nanmean(v):.3f}, sd {np.nanstd(v):.3f}, P(share >= obs) = {np.nanmean(v >= obs[0]):.3f}, mean #held-outs scored {n.mean():.1f}")
