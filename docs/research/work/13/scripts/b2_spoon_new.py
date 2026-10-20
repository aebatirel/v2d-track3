"""Stage B retry: spoon roll under the new near-survivors, from the stored Stage B spoon MC statistics
(construction frame P: +z bowl->handle, +x to the CONVEX back, +y to M1; A = x to convex, B = x to concave)."""
import json, glob, numpy as np
MAJ = ("skew", "m5", "ssq", "s4", "negmed", "q10", "ext")
for mode in ("round", "oval", "nomark"):
    recs = [json.loads(l) for f in sorted(glob.glob(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_{mode}_*.jsonl")) for l in open(f)]
    lab = {"G7 maj7 top2|skew|": [], "G2m z:skew y:far3d": [], "x up at rest (concave-up)": [], "z by maj7": []}
    for r in recs:
        S = {k: np.array(v) for k, v in r["S"].items()}
        vote = np.sign(sum(np.sign(S[k]) for k in MAJ))
        top = np.argsort(-np.abs(S["skew"]))[:2]
        s = {int(t): vote[t] for t in top}
        miss = ({0, 1, 2} - set(s)).pop(); s[miss] = int(np.prod(list(s.values())))
        lab["G7 maj7 top2|skew|"].append(("A" if s[0] > 0 else "B") + ("" if s[2] > 0 else "-zflip"))
        sz = np.sign(S["skew"][2]); sy = np.sign(S["far3d"][1]); sx = sy * sz
        lab["G2m z:skew y:far3d"].append(("A" if sx > 0 else "B") + ("" if sz > 0 else "-zflip"))
        lab["x up at rest (concave-up)"].append("B")
        lab["z by maj7"].append("ok" if vote[2] > 0 else "zflip")
    print(mode, len(recs), {k: dict(zip(*np.unique(v, return_counts=True))) for k, v in lab.items()})
