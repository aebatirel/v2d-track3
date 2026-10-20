"""Stage B: search deterministic roll-sign rules on the 10 published frames + multiple-comparison null + LOO.
z is fixed by skew_z>0 (10/10). A roll rule must make x and y come out positive (published = identity).
Families:
 F1  single stat:      sign(axis a in {x,y}) by p*s>0
 F2  x/y magnitude:    axis a* = argmax_{x,y} |r(a)|, sign by p*s(a*)>0
 F2b 3-axis cascade:   top-2 axes by |r| fixed by p*s>0, third by right-hand completion (z included)
 F4  kurtosis select:  a* = argmin/argmax_{x,y} of kurt or |kurt|, sign by p*s(a*)>0
 F3  hybrid:           if |s1(a1)| >= tau use p1*s1(a1) else p2*s2(a2); tau fitted (1..9 objects below tau)
Null: each object's roll flipped (x,y stats negated) independently with prob 1/2; rerun the full search.
Usage: b_search.py [n_null] [seed]
"""
import sys, json, itertools, numpy as np
R = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_feats.json"))
OBJ = [k for k in R if "__" not in k]
EVEN = {"kurt", "skew_se1"}
DROP = {"m_ab2", "m_ac2", "netnorm"}
ODD = [k for k in R[OBJ[0]] if not k.startswith("_") and k not in EVEN | DROP]
ZBAD = {"m_az_absz", "m_az3"}          # even in z when a = z
D = np.array([[R[o][s] for o in OBJ] for s in ODD])           # (S, 10, 3)
SE = np.array([R[o]["skew_se1"] for o in OBJ])                 # (10, 3)
KU = np.array([R[o]["kurt"] for o in OBJ])
iskew = ODD.index("skew")
RANK = {s: np.abs(D[i]) for i, s in enumerate(ODD)}
RANK["skewz"] = np.abs(D[iskew]) / SE
S, NO = len(ODD), len(OBJ)


def fam_F1(D):
    ok = []; names = []
    for a in (0, 1):
        for si in range(S):
            for p in (1, -1):
                ok.append(p * D[si, :, a] > 0); names.append(("F1", "xy"[a], ODD[si], p))
    return np.array(ok), names


def fam_F2(D):
    ok = []; names = []
    for rn, Rk in RANK.items():
        rk = np.abs(D[ODD.index(rn)]) if rn in ODD else np.abs(D[iskew]) / SE
        a_star = np.argmax(rk[:, :2], 1)
        for si in range(S):
            v = D[si, np.arange(NO), a_star]
            for p in (1, -1):
                ok.append(p * v > 0); names.append(("F2", rn, ODD[si], p))
    return np.array(ok), names


def fam_F2b(D):
    ok = []; names = []
    for rn in RANK:
        if rn in ZBAD:
            continue
        rk = np.abs(D[ODD.index(rn)]) if rn in ODD else np.abs(D[iskew]) / SE
        top = np.argsort(-rk, 1)[:, :2]
        for si in range(S):
            if ODD[si] in ZBAD:
                continue
            v1 = D[si, np.arange(NO), top[:, 0]]; v2 = D[si, np.arange(NO), top[:, 1]]
            for p in (1, -1):
                ok.append((p * v1 > 0) & (p * v2 > 0)); names.append(("F2b", rn, ODD[si], p))
    return np.array(ok), names


def fam_F4(D):
    ok = []; names = []
    sel = {"min_kurt": np.argmin(KU[:, :2], 1), "max_kurt": np.argmax(KU[:, :2], 1),
           "min_abskurt": np.argmin(np.abs(KU[:, :2]), 1), "max_abskurt": np.argmax(np.abs(KU[:, :2]), 1)}
    for sn, a_star in sel.items():
        for si in range(S):
            v = D[si, np.arange(NO), a_star]
            for p in (1, -1):
                ok.append(p * v > 0); names.append(("F4", sn, ODD[si], p))
    return np.array(ok), names


def fam_F3(D, objs=None, return_detail=False):
    """Vectorised hybrid search. Returns count of genuine hybrids (1..n-1 below tau) fitting all objs."""
    idx = np.arange(NO) if objs is None else np.asarray(objs)
    n = len(idx)
    Dx = D[:, idx, :2]                                  # (S, n, 2)
    sig = np.concatenate([Dx, -Dx], 0) > 0              # (2S, n, 2): polarity-expanded correctness
    V = np.abs(np.concatenate([D[:, idx, :2], D[:, idx, :2]], 0))   # thresholds on |s1|
    P1 = sig.transpose(0, 2, 1).reshape(-1, n)          # (4S, n) primaries (stat,pol,axis)
    VV = V.transpose(0, 2, 1).reshape(-1, n)
    P2 = P1                                             # fallbacks: same catalogue
    order = np.argsort(VV, 1)
    c1s = np.take_along_axis(P1, order, 1)              # primary correctness sorted by |s1|
    suf = np.flip(np.cumprod(np.flip(c1s, 1), 1), 1)    # suf[:,k] = all c1 from k..n-1 sorted
    fits = []
    for i in range(P1.shape[0]):
        c2s = P2[:, order[i]]                           # (4S, n) fallback correctness in i's order
        pre = np.cumprod(c2s, 1)                        # pre[:,k-1] = all c2 among first k
        # k objects below tau, k = 1..n-1: need pre[:,k-1] and suf[i,k]
        good = pre[:, :-1] & suf[i, 1:][None, :]        # (4S, n-1)
        js, ks = np.nonzero(good)
        for j, k in zip(js, ks):
            fits.append((i, j, k + 1))
    if not return_detail:
        return len(fits), len({(i, j) for i, j, _ in fits})
    names = [(ODD[(q // 2) % S] if True else None) for q in range(P1.shape[0])]
    return fits, VV, order


def decode(q):
    # P1 row q -> (stat, pol, axis): rows ordered [pol(+)S stats ; pol(-)S stats] x axis
    blk, ax = divmod(q, 2)
    pol = 1 if blk < S else -1
    return ODD[blk % S], pol, "xy"[ax]


if __name__ == "__main__":
    nnull = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    fams = {"F1": fam_F1, "F2": fam_F2, "F2b": fam_F2b, "F4": fam_F4}
    print("objects:", OBJ); print("n odd stats:", S)
    for fn, f in fams.items():
        ok, names = f(D)
        full = ok.all(1)
        print(f"{fn}: {len(names)} rules, {full.sum()} fit 10/10, max fit {ok.sum(1).max()}")
        for k in np.nonzero(full)[0][:40]:
            print("   ", names[k])
    nf, nshape = fam_F3(D)
    print(f"F3: {4*S}x{4*S} shapes, fitting (shape,k) combos {nf}, distinct shapes {nshape}")
    fits, VV, order = fam_F3(D, return_detail=True)
    shapes = {}
    for i, j, k in fits:
        shapes.setdefault((i, j), []).append(k)
    rows = []
    for (i, j), ks in shapes.items():
        v = np.sort(VV[i])
        lo = v[min(ks) - 1]; hi = v[max(ks)]
        rows.append((np.log10(max(hi, 1e-12) / max(lo, 1e-12)), decode(i), decode(j), ks, lo, hi))
    rows.sort(key=lambda r: -r[0])
    print("  top hybrid shapes by tau-interval width (log10 hi/lo): primary (stat,pol,axis) | fallback | k below | tau in [lo,hi)")
    for r in rows[:25]:
        print(f"   {r[0]:5.2f}  {r[1]} | {r[2]} | k={r[3]} | [{r[4]:.4g}, {r[5]:.4g})")
    json.dump([dict(w=float(r[0]), ks=[int(k) for k in r[3]], lo=float(r[4]), hi=float(r[5]), prim=[str(r[1][0]),int(r[1][1]),r[1][2]], fall=[str(r[2][0]),int(r[2][1]),r[2][2]]) for r in rows],
              open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_hybrids.json", "w"), indent=0)
    if nnull:
        cnt = {k: [] for k in list(fams) + ["F3"]}
        for t in range(nnull):
            flip = rng.random(NO) < 0.5
            if not flip.any():
                flip[rng.integers(NO)] = True      # exclude the observed (all-identity) configuration
            Dn = D.copy(); Dn[:, flip, :2] *= -1
            for fn, f in fams.items():
                cnt[fn].append(int(f(Dn)[0].all(1).sum()))
            cnt["F3"].append(fam_F3(Dn)[1])
        print(f"NULL ({nnull} random roll-flip configurations):")
        for k, v in cnt.items():
            v = np.array(v)
            print(f"   {k}: P(>=1 rule fits 10/10) = {np.mean(v>0):.3f}; mean #fitting {v.mean():.1f}; median {np.median(v):.0f}")
