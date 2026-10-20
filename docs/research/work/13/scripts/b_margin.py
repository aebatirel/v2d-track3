"""Decisive per-object values of the surviving parameter-free roll rules (F2, F2b) + sampling SE at n points."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import numpy as np, b_search as B
D, ODD, NO = B.D, B.ODD, B.NO
def rank(rn): return np.abs(D[ODD.index(rn)]) if rn in ODD else np.abs(D[B.iskew]) / B.SE
for fam, f in (("F2", B.fam_F2), ("F2b", B.fam_F2b)):
    ok, names = f(D)
    for k in np.nonzero(ok.all(1))[0]:
        _, rn, sn, p = names[k]; rk = rank(rn); si = ODD.index(sn)
        if fam == "F2":
            ax = np.argmax(rk[:, :2], 1); vals = p * D[si, np.arange(NO), ax]
            desc = " ".join(f"{'xy'[a]}{v:+.4f}" for a, v in zip(ax, vals))
        else:
            top = np.argsort(-rk, 1)[:, :2]
            desc = " ".join(f"{''.join('xyz'[t] for t in tt)}:{min(p*D[si,o,tt[0]], p*D[si,o,tt[1]]):+.4f}" for o, tt in enumerate(top))
        mags = np.abs(vals) if fam == "F2" else None
        print(f"{fam} rank|{rn}| sign {'+' if p>0 else '-'}{sn}: {desc}" + (f"  min {mags.min():.4f}" if mags is not None else ""))
