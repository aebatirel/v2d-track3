"""Stage B retry: rule families NOT in b_search.py, all three sign bits required (z not pre-fixed).
 G1  kurtosis-ordered cascade: top-2 axes by {kurt desc, kurt asc, |kurt| desc, |kurt| asc} signed by p*s, third completed
 G2  fixed pair, same statistic: axes {xy, xz, yz} signed by p*s, third completed (variance-ordered cascade)
 G2m fixed pair, two statistics: z by p1*s1, then a in {x,y} by p2*s2, third completed
 G7  majority vote of 7 moment/extreme statistics per axis; signed pair = top-2 by |skew| or fixed (y,z)
Null: roll bit (x,y jointly) flipped per scan with prob 1/2 (z kept), same search; LOO share for the union.
Usage: b2_cascades.py [n_null] [seed]"""
import sys, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import b_search as B
D, KU, SE, ODD, NO = B.D, B.KU, B.SE, B.ODD, B.NO
OK = [i for i, s in enumerate(ODD) if s not in B.ZBAD]
MAJ = [ODD.index(s) for s in ("skew", "m5", "ssq", "s4", "negmed", "q10", "ext")]
iskew = ODD.index("skew")
ar = np.arange(NO)


def pairfit(Dm, a1, a2, s1, s2, p1, p2):
    """a1,a2: (NO,) axis idx; returns bool (NO,) that both fixed axes come out positive => published frame."""
    return (p1 * Dm[s1, ar, a1] > 0) & (p2 * Dm[s2, ar, a2] > 0)


def families(Dm):
    out = {"G1": [], "G2": [], "G2m": [], "G7": []}; names = {k: [] for k in out}
    for on, key in (("kurt_desc", -KU), ("kurt_asc", KU), ("abskurt_desc", -np.abs(KU)), ("abskurt_asc", np.abs(KU))):
        top = np.argsort(key, 1)[:, :2]
        for s in OK:
            for p in (1, -1):
                out["G1"].append(pairfit(Dm, top[:, 0], top[:, 1], s, s, p, p)); names["G1"].append((on, ODD[s], p))
    for pn, (a, b) in (("xy", (0, 1)), ("xz", (0, 2)), ("yz", (1, 2))):
        A = np.full(NO, a); Bb = np.full(NO, b)
        for s in OK:
            for p in (1, -1):
                out["G2"].append(pairfit(Dm, A, Bb, s, s, p, p)); names["G2"].append((pn, ODD[s], p))
    Z = np.full(NO, 2)
    for s1 in OK:
        for p1 in (1, -1):
            zf = p1 * Dm[s1, ar, 2] > 0
            if not zf.all() and Dm is D:
                pass
            for a in (0, 1):
                for s2 in OK:
                    for p2 in (1, -1):
                        out["G2m"].append(zf & (p2 * Dm[s2, ar, a] > 0)); names["G2m"].append((ODD[s1], p1, "xy"[a], ODD[s2], p2))
    vote = np.sign(np.sign(Dm[MAJ]).sum(0))          # (NO,3)
    top = np.argsort(-np.abs(Dm[iskew]), 1)[:, :2]
    out["G7"].append((vote[ar, top[:, 0]] > 0) & (vote[ar, top[:, 1]] > 0)); names["G7"].append("maj7|top2|skew|")
    out["G7"].append((vote[:, 1] > 0) & (vote[:, 2] > 0)); names["G7"].append("maj7|yz")
    out["G7"].append((vote[:, 0] > 0) & (vote[:, 2] > 0)); names["G7"].append("maj7|xz")
    return {k: np.array(v) for k, v in out.items()}, names


if __name__ == "__main__":
    nnull = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    ok, names = families(D)
    print("objects:", B.OBJ)
    for k, v in ok.items():
        full = v.all(1)
        print(f"{k}: {len(v)} rules, {full.sum()} fit 10/10, max fit {v.sum(1).max()}, #fit 9 {np.sum(v.sum(1)==9)}")
        for i in np.nonzero(full)[0][:30]:
            print("    FIT", names[k][i])
        if k == "G7":
            for i in range(len(v)):
                print("    G7", names[k][i], v[i].astype(int))
    if nnull:
        cnt = {k: [] for k in ok}; cnt["union"] = []
        for t in range(nnull):
            flip = rng.random(NO) < 0.5
            if not flip.any():
                flip[rng.integers(NO)] = True
            Dn = D.copy(); Dn[:, flip, :2] *= -1
            o, _ = families(Dn)
            u = 0
            for k, v in o.items():
                c = int(v.all(1).sum()); cnt[k].append(c); u += c
            cnt["union"].append(u)
        print(f"NULL ({nnull} random roll configurations, z kept):")
        for k, v in cnt.items():
            v = np.array(v); obs = sum(ok[k].all(1).sum() for k in ok) if k == "union" else ok[k].all(1).sum()
            print(f"   {k}: P(>=1 fits) = {np.mean(v>0):.3f}; mean #fit {v.mean():.2f}; P(#fit >= observed {obs}) = {np.mean(v>=max(obs,1)):.3f}")
