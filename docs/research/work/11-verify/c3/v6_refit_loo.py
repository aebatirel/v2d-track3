"""Verifier: LOO heading residual and eval-W shift when the s25 reference fits are replaced by v2 refits
(start offset -3/0/+3, sample seed 1; fit or profile argmax). Approximation: a ref's transferred prediction shifts
by (psi_new - psi_s25) of that ref (pure world-yaw change; pitch/roll changes of the refit ignored).
usage: python v6_refit_loo.py <native|flipped>"""
import json, sys, numpy as np, itertools
K = sys.argv[1]; W11 = "/Users/aebatirel/Documents/Code/v2d-research/work/11"; V = "/Users/aebatirel/Documents/Code/v2d-research/work/11-verify"
T = json.load(open(f"{W11}/s26_transfer_{K}_s25_refine_{K}.json"))["pairs"]; F = json.load(open(f"{W11}/s25_refine_{K}.json"))
w = lambda a: (np.asarray(a, float) + 180) % 360 - 180; u = lambda a: np.mod(np.asarray(a, float), 360.0)
REFS = [12, 13, 21, 0]
def v2(ep, d, key): return json.load(open(f"{V}/v2_out/{K}_{ep}_{d:+d}_1.json"))[key]
variants = {"s25": {e: F[str(e)]["psi"] for e in REFS}}
for d in (-3, 0, 3):
    variants[f"fit{d:+d}"] = {e: v2(e, d, "psi_fit") for e in REFS}
    variants[f"argmax{d:+d}"] = {e: v2(e, d, "profile_argmax") for e in REFS}
variants["median_all_v2"] = {e: float(np.median([v2(e, d, k) for d in (-3, 0, 3) for k in ("psi_fit", "profile_argmax")])) for e in REFS}
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
def pred(tag, q, S, psi):
    pr = [u(T[f"{tag}{q}|{p}"]["psi"] + (psi[p] - F[str(p)]["psi"])) for p in S if p != q and f"{tag}{q}|{p}" in T]
    return float(np.median(pr))
base = {q: pred("e", q, REFS, variants["s25"]) for q in EV}
res = {}
for name, psi in variants.items():
    out = {}
    for setname, S in (("best4", REFS), ("sharp3", [12, 13, 0])):
        r = [float(w(pred("p", q, S, psi) - psi[q])) for q in S]
        out[setname] = dict(resid=[round(x, 2) for x in r], rms=float(np.sqrt(np.mean(np.square(r)))))
    sh = np.array([w(pred("e", q, REFS, psi) - base[q]) for q in EV])
    out["evalW_shift_best4"] = dict(mean=float(sh.mean()), min=float(sh.min()), max=float(sh.max()))
    res[name] = out
    print(f"{name:14s} psi {[round(psi[e],2) for e in REFS]} LOO best4 rms {out['best4']['rms']:.2f} {out['best4']['resid']}  sharp3 rms {out['sharp3']['rms']:.2f}  evalW shift mean {sh.mean():+.2f} [{sh.min():+.2f},{sh.max():+.2f}]")
# random draw: each ref independently picks one of its 6 v2 values (fit/argmax x 3 starts) -> distribution of LOO rms
vals = {e: [v2(e, d, k) for d in (-3, 0, 3) for k in ("psi_fit", "profile_argmax")] for e in REFS}
r4, r3 = [], []
for combo in itertools.product(*[range(6)] * 4):
    psi = {e: vals[e][i] for e, i in zip(REFS, combo)}
    r4.append(np.sqrt(np.mean(np.square([w(pred("p", q, REFS, psi) - psi[q]) for q in REFS]))))
    r3.append(np.sqrt(np.mean(np.square([w(pred("p", q, [12, 13, 0], psi) - psi[q]) for q in [12, 13, 0]]))))
for n, r in (("best4", r4), ("sharp3", r3)):
    r = np.array(r); print(f"all 6^4 combos {n}: LOO rms median {np.median(r):.2f} p10 {np.percentile(r,10):.2f} p90 {np.percentile(r,90):.2f}")
res["combos"] = dict(best4=[float(np.median(r4)), float(np.percentile(r4, 10)), float(np.percentile(r4, 90))],
                     sharp3=[float(np.median(r3)), float(np.percentile(r3, 10)), float(np.percentile(r3, 90))])
json.dump(res, open(f"{V}/c3/v6_refit_loo_{K}.json", "w"), indent=1)
