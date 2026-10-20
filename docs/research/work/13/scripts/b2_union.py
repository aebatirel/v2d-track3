"""Stage B retry: union of ALL parameter-free families (Stage B F1,F2,F2b,F4 + retry G1,G2,G2m,G7): 10/10 count, LOO share,
and the same under random roll configurations (z kept). Usage: b2_union.py n_null seed"""
import sys, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import b_search as B, b2_cascades as C


def okmat(Dm):
    mats = [f(Dm)[0] for f in (B.fam_F1, B.fam_F2, B.fam_F2b, B.fam_F4)]
    mats += list(C.families(Dm)[0].values())
    return np.concatenate(mats, 0)


def loo(ok):
    sh = []
    for j in range(ok.shape[1]):
        oth = np.delete(ok, j, 1).all(1)
        sh.append(ok[oth, j].mean() if oth.any() else np.nan)
    return np.array(sh)


nnull = int(sys.argv[1]); rng = np.random.default_rng(int(sys.argv[2]))
ok = okmat(B.D); s = loo(ok)
print(f"rules {ok.shape[0]}; fit 10/10: {ok.all(1).sum()}; LOO share per scan {np.round(s,2)}; mean {np.nanmean(s):.3f}")
print("LOO candidate counts per held-out scan:", [int(np.delete(ok, j, 1).all(1).sum()) for j in range(ok.shape[1])])
fit, ms = [], []
for t in range(nnull):
    flip = rng.random(B.NO) < 0.5
    if not flip.any():
        flip[rng.integers(B.NO)] = True
    Dn = B.D.copy(); Dn[:, flip, :2] *= -1
    o = okmat(Dn); fit.append(o.all(1).sum()); ms.append(np.nanmean(loo(o)))
fit, ms = np.array(fit), np.array(ms)
print(f"NULL {nnull}: P(>=1 fits 10/10) = {np.mean(fit>0):.3f}; P(#fit >= {ok.all(1).sum()}) = {np.mean(fit>=ok.all(1).sum()):.3f}; "
      f"LOO mean share null mean {np.nanmean(ms):.3f}, P(>= {np.nanmean(s):.3f}) = {np.nanmean(ms>=np.nanmean(s)):.3f}")
