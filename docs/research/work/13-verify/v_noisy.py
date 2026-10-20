"""Verifier: re-derive C1 counts, binomial P, and the noisy-sign LR from my own v_geom.jsonl (own skews and se1).
Role order: T3 stored (x,y,z) = (min,mid,max); T2 stored (y,x,z) = (min,mid,max) as in the claim."""
import json, numpy as np
from math import comb
from scipy.stats import norm
R = [json.loads(l) for l in open("/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v_geom.jsonl")]
FIRST7 = {"cane", "baseball_bat", "squeegee", "iron", "spray_bottle", "big_red_bowl", "light_blue_book"}
def roles(d):
    o = [0, 1, 2] if d["track"] == "T3" else [1, 0, 2]
    return [d["sd_mm"][i] for i in o], [d["skew"][i] for i in o], [d["se1"][i] for i in o]
def tail(k, n): return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
rows = {}
for d in R:
    sd, sk, se = roles(d); d["_r"] = (sd, sk, se)
    rd = sd[0] / sd[1] > 0.91; zd = sd[1] / sd[2] > 0.91
    d["rd"], d["zd"] = rd, zd
for tr in ("T2", "T3"):
    for lab, filt in (("all", lambda d: True), ("fresh22", lambda d: d["name"] not in FIRST7)):
        S = [d for d in R if d["track"] == tr and filt(d)]
        if tr == "T3" and lab == "fresh22": continue
        mid = [d["_r"][1][1] for d in S if not d["rd"]]; mx = [d["_r"][1][2] for d in S if not d["zd"]]
        mid_all = [d["_r"][1][1] for d in S]; mx_all = [d["_r"][1][2] for d in S]; mn = [d["_r"][1][0] for d in S if not d["rd"]]
        k1 = sum(s > 0 for s in mid); k2 = sum(s > 0 for s in mx); k3 = sum(s > 0 for s in mn)
        print(f"{tr} {lab:8s} mid nondeg {k1}/{len(mid)} P={tail(k1, len(mid)):.4f} | max nondeg {k2}/{len(mx)} P={tail(k2, len(mx)):.4f}"
              f" | min nondeg {k3}/{len(mn)} | mid incl degen {sum(s > 0 for s in mid_all)}/{len(mid_all)} P={tail(sum(s > 0 for s in mid_all), len(mid_all)):.4f}"
              f" | max incl degen {sum(s > 0 for s in mx_all)}/{len(mx_all)} P={tail(sum(s > 0 for s in mx_all), len(mx_all)):.5f}")
print("failures (mid/max nondeg, both tracks):")
for d in R:
    sd, sk, se = d["_r"]
    for r, flag in ((1, d["rd"]), (2, d["zd"])):
        if not flag and sk[r] < 0: print(f"  {d['track']} {d['name']:18s} role {'mid' if r == 1 else 'max'} skew {sk[r]:+.5f}  z@n=1e4 {sk[r] * 100 / se[r]:+.2f}")
ns = np.logspace(2, 9, 141)
def fit(rs, label):
    s = np.array([x[0] for x in rs]); se = np.array([x[1] for x in rs])
    ll = np.array([norm.logcdf(s * np.sqrt(n) / se).sum() for n in ns]); l0 = len(rs) * np.log(0.5)
    post = np.exp(ll - ll.max()); post /= post.sum(); q = lambda p: ns[np.searchsorted(np.cumsum(post), p)]
    print(f"{label:24s} bits {len(rs):3d} pos {int((s > 0).sum()):3d} avgLR {np.exp(ll - l0).mean():.3g} maxLR {np.exp(ll.max() - l0):.3g}"
          f" n med {q(0.5):.3g} [{q(0.1):.3g},{q(0.9):.3g}]")
def sel(tr, role):
    out = []
    for d in R:
        if d["track"] != tr: continue
        sd, sk, se = d["_r"]
        if role in (0, 1) and d["rd"]: continue
        if role == 2 and d["zd"]: continue
        out.append((sk[role], se[role]))
    return out
fit(sel("T3", 1), "T3 mid"); fit(sel("T3", 2), "T3 max"); fit(sel("T2", 1), "T2 mid"); fit(sel("T2", 2), "T2 max")
fit(sel("T3", 1) + sel("T3", 2) + sel("T2", 1) + sel("T2", 2), "joint mid+max")
fit(sel("T3", 1) + sel("T2", 1), "joint mid only")
fit(sel("T2", 0), "T2 min contrast"); fit(sel("T3", 0), "T3 min contrast")
# grid sensitivity: wider n range
ns = np.logspace(1, 12, 221); fit(sel("T3", 1) + sel("T3", 2) + sel("T2", 1) + sel("T2", 2), "joint, n in [1e1,1e12]")
