"""Stage C retry: sensitivity of the eval W (frame-0 camera heading in mocap) to the reference set.
Sets: sharp-profile refs only {12,13,0} (a-priori criterion), best4 {12,13,21,0}, all fitted refs.
Also LOO on the sharp set. Usage: python s32_refset.py <flipped|native>"""
import json, sys, numpy as np
k = sys.argv[1]
T = json.load(open(f"s26_transfer_{k}_s25_refine_{k}.json"))["pairs"]; F = json.load(open(f"s25_refine_{k}.json"))
w = lambda a: (a + 180) % 360 - 180; u = lambda a: np.mod(np.asarray(a, float), 360.0)
fitted = sorted(int(e) for e in F if str(e).isdigit())
sets = {"sharp3": [12, 13, 0], "best4": [12, 13, 21, 0], "all": fitted}
print("fitted refs:", {e: round(F[str(e)]["psi"], 2) for e in fitted})
def pred(tag, q, S):
    pr = [T[f"{tag}{q}|{p}"]["psi"] for p in S if p != q and f"{tag}{q}|{p}" in T]
    return float(np.median(u(pr))) if pr else np.nan, len(pr)
for S in ("sharp3", "best4", "all"):
    r = [w(pred("p", q, sets[S])[0] - F[str(q)]["psi"]) for q in sets[S]]
    print(f"LOO {S:6s} {sets[S]}: resid {np.round(r,2)} rms {np.sqrt(np.mean(np.square(r))):.2f}")
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
out = {}; d34 = []; dall = []
for q in EV:
    a, b, c = (pred("e", q, sets[s])[0] for s in ("sharp3", "best4", "all"))
    out[q] = dict(sharp3=a, best4=b, all=c); d34.append(w(a - b)); dall.append(w(c - b))
    print(f"eval {q:2d}: sharp3 {a:7.2f} best4 {b:7.2f} all {c:7.2f}  d(sharp3-best4) {w(a-b):+5.2f} d(all-best4) {w(c-b):+5.2f}")
d34 = np.array(d34); dall = np.array(dall)
print(f"sharp3-best4: mean {d34.mean():+.2f} sd {d34.std():.2f} max {np.abs(d34).max():.2f}; all-best4: mean {dall.mean():+.2f} sd {dall.std():.2f} max {np.abs(dall).max():.2f}")
json.dump(out, open(f"s32_refset_{k}.json", "w"), indent=1)
