"""Verifier (C5): does canonicalising a partial spoon (underside never seen) flip z? Own face-removal (by outward normal),
own frame code (v_spoon_asym.frame). Variants: bowl underside removed (n_x>0.3, z<Lb), whole underside removed (n_x>0.3),
half of bowl underside removed (n_x>0.3, z<Lb/2), filled bowl not tested here. Reports P(z flip), P(mid-axis flip).
Usage: v_partial.py N seed"""
import sys, json, numpy as np
args = sys.argv[1:]; sys.argv = sys.argv[:1] + ["0", "0"]
import v_spoon_asym as M
N, seed = int(args[0]), int(args[1]); M.rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v_partial_{seed}.jsonl"
for i in range(N):
    p = M.draw(); V, F = M.build(p); Lb = p["body"]["Lb"]
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    cen = T.mean(1)
    # global outward orientation: on the body (exclude markers: |y| small region irrelevant), outward normals point away from the local axis
    body = (cen[:, 2] > Lb + 0.03) & (cen[:, 2] < p["body"]["L"] - 0.02) & (np.abs(cen[:, 1]) < 0.015)
    sgn = np.sign(np.mean(np.sum(n[body][:, :2] * (cen[body][:, :2] - np.median(cen[body][:, :2], 0)), 1)))
    n *= sgn
    E0, m20, h0 = M.frame(V, F)
    res = {"full": (float(m20), float(h0))}
    for nm, sel in (("bowl_under", (n[:, 0] > 0.3) & (cen[:, 2] < Lb)), ("all_under", n[:, 0] > 0.3),
                    ("half_bowl_under", (n[:, 0] > 0.3) & (cen[:, 2] < Lb / 2)), ("bowl_under_70pct", (n[:, 0] > 0.3) & (cen[:, 2] < 0.7 * Lb))):
        E, toM2, toH = M.frame(V, F[~sel]); res[nm] = (float(toM2), float(toH))
    with open(OUT, "a") as f: f.write(json.dumps(res) + "\n")
    print(i, {k: (round(a, 3), round(b, 3)) for k, (a, b) in res.items()}, flush=True)
