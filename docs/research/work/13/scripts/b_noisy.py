"""Noisy-sign models: published roll bit of object o = sign of p*s(a) computed on n random surface samples.
P(published | model) = Phi(p*s_exact / (sd_1e5 * sqrt(1e5/n))). Likelihood ratio vs random roll (2^-10), max over n.
Also the z sign. Null: random roll bits -> distribution of the max log-LR over all (stat, axis, polarity, n)."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import json, numpy as np
from scipy.stats import norm
import b_search as B
SM = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_sample.json"))
N0 = SM["N"]; SDJ = SM["sd"]
stats = [s for s in B.ODD if s in SDJ[B.OBJ[0]] and (len(sys.argv) < 2 or s not in B.ZBAD)]
D = np.array([[B.R[o][s] for o in B.OBJ] for s in stats])          # exact values (S,10,3)
SD = np.array([[SDJ[o][s] for o in B.OBJ] for s in stats])         # sd at N0
SD = np.maximum(SD, 1e-9)
NS = np.array([1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 1e7, 1e9])


def loglik(Dv, SDv):
    # Dv, SDv: (S, 10) for one axis -> (2 pol, S, len(NS)) log-likelihoods
    z = Dv[None, :, :, None] / (SDv[None, :, :, None] * np.sqrt(N0 / NS)[None, None, None, :])
    z = np.concatenate([z, -z], 0)
    return norm.logcdf(z).sum(2)


def best(Dx):
    out = []
    for a in (0, 1):
        L = loglik(Dx[:, :, a], SD[:, :, a])
        out.append(L)
    return np.stack(out)          # (2 axes, 2 pol, S, nN)


if __name__ == "__main__":
    L0 = 10 * np.log(0.5)
    L = best(D)
    flat = L.reshape(-1, len(NS)); mx = flat.max(1)
    order = np.argsort(-mx)
    print(f"roll: log-LR vs random (log 2^-10 = {L0:.2f}); top models (axis, polarity, stat, best n, LR):")
    for k in order[:12]:
        a, p, s = np.unravel_index(k, L.shape[:3])
        j = np.argmax(flat[k])
        print(f"   {'xy'[a]} {'+' if p==0 else '-'}{stats[s]:10s} n*={NS[j]:.0e}  LR={np.exp(flat[k, j]-L0):8.2f}   P(all 10 | n*)={np.exp(flat[k,j]):.2e}")
    for nm in ("skew",):
        s = stats.index(nm)
        for a in (0, 1):
            print(f"   profile {'xy'[a]} +{nm}: LR(n) = " + " ".join(f"{n:.0e}:{np.exp(L[a,0,s,j]-L0):.2f}" for j, n in enumerate(NS)))
    obs = mx.max() - L0
    rng = np.random.default_rng(2); nul = []
    for t in range(2000):
        f = rng.random(B.NO) < 0.5
        if not f.any(): f[rng.integers(B.NO)] = True
        Dn = D.copy(); Dn[:, f, :2] *= -1
        nul.append(best(Dn).max() - L0)
    nul = np.array(nul)
    print(f"max log-LR observed {obs:.2f} (LR {np.exp(obs):.1f}); null mean LR {np.exp(nul).mean():.1f}, "
          f"median {np.exp(np.median(nul)):.1f}; P(null max >= obs) = {np.mean(nul >= obs):.3f}")
    # z sign
    Lz = loglik(D[:, :, 2], SD[:, :, 2]).reshape(-1, len(NS))
    mz = Lz.max(1); kz = np.argsort(-mz)[:5]
    print("z: top noisy models:", [(('+' if k < len(stats) else '-') + stats[k % len(stats)], f"{np.exp(mz[k]-L0):.0f}") for k in kz])
    nz = []
    for t in range(2000):
        f = rng.random(B.NO) < 0.5
        if not f.any(): f[rng.integers(B.NO)] = True
        Dz = D[:, :, 2] * np.where(f, -1, 1)
        nz.append(loglik(Dz, SD[:, :, 2]).max() - L0)
    print(f"z: observed max LR {np.exp(mz.max()-L0):.0f}; P(null max >= obs) = {np.mean(np.array(nz) >= mz.max()-L0):.3f}")
