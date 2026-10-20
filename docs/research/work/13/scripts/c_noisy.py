"""Stage C: noisy-sign model for 'mid and max axes signed by positive skew', fitted jointly on Track 3 (10 scans) and the
non-degenerate Track 2 scans. Published bit = sign of the skew estimated from n random surface points:
P(bit = +) = Phi(s * sqrt(n) / se1) (delta-method SE along a fixed axis). Average likelihood over log-uniform n in
[1e2, 1e9] vs random bits (0.5 each). Writes out/c_noisy.log via stdout."""
import json, numpy as np
from scipy.stats import norm
T3 = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_feats.json"))
T2 = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_t2feats_stored.json"))
O3 = [k for k in T3 if "__" not in k]


def rows(R, objs, roles):
    out = []
    for o in objs:
        sd = R[o]["_sd_mm"]
        for r in roles:
            if r in (0, 1) and sd[0] / sd[1] > 0.91: continue
            if r == 2 and sd[1] / sd[2] > 0.91: continue
            out.append((o, r, R[o]["skew"][r], R[o]["skew_se1"][r]))
    return out


ns = np.logspace(2, 9, 141)
def fit(rs, label):
    s = np.array([x[2] for x in rs]); se = np.array([x[3] for x in rs])
    ll = np.array([norm.logcdf(s * np.sqrt(n) / se).sum() for n in ns])
    lr_avg = np.exp(ll - len(rs) * np.log(0.5)).mean(); best = ns[np.argmax(ll)]
    post = np.exp(ll - ll.max()); post /= post.sum()
    q = lambda p: ns[np.searchsorted(np.cumsum(post), p)]
    print(f"{label:28s} bits {len(rs):3d}  #pos {int((s > 0).sum()):3d}  maxLR {np.exp(ll.max() - len(rs) * np.log(0.5)):.3g} at n={best:.3g}"
          f"  avgLR(log-unif n) {lr_avg:.3g}  n post median {q(0.5):.3g} [{q(0.1):.3g}, {q(0.9):.3g}]")
    return post


if __name__ == "__main__":
    r3m = rows(T3, O3, [1]); r3z = rows(T3, O3, [2])
    o2 = sorted(T2); r2m = rows(T2, o2, [1]); r2z = rows(T2, o2, [2])
    fit(r3m, "T3 mid (y)"); fit(r3z, "T3 max (z)"); fit(r2m, "T2 mid (x)"); fit(r2z, "T2 max (z)")
    fit(r3m + r3z, "T3 mid+max"); fit(r2m + r2z, "T2 mid+max")
    post = fit(r3m + r3z + r2m + r2z, "T3+T2 mid+max (joint)")
    # alternative hypotheses on the same bits for contrast: min axis
    fit(rows(T3, O3, [0]), "T3 min (x) [contrast]"); fit(rows(T2, o2, [0]), "T2 min (y) [contrast]")
    np.save("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_noisy_post.npy", np.vstack([ns, post]))
