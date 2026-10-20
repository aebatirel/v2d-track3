"""Gate distances (C9 formula) at chosen keyframes for s5 and r3s5r1."""
import json, numpy as np
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
def cen(T): return -T[:3, :3].T @ T[:3, 3]
for P in ("s5", "r3s5r1"):
    for e, t in ((3, 85), (35, 175), (35, 235), (10, 100)):
        K = {r["frame"]: r for r in json.load(open(f"{W}/c1/{P}_e{e}.json"))["frames"]}
        V = {r["frame"]: T44(r["c_from_c0"]) for r in json.load(open(f"{W}/c3/vo_e{e}.json"))["frames"] if "c_from_c0" in r}
        M = T44(K[t]["c_from_world"]); pr = [V[t] @ np.linalg.inv(V[u]) @ T44(K[u]["c_from_world"]) for u in (t - 5, t + 5)]
        d = [1000 * np.linalg.norm(cen(M) - cen(p)) for p in pr]; dlr = 1000 * np.linalg.norm(cen(pr[0]) - cen(pr[1]))
        print(P, e, t, "dL %.2f dR %.2f dLR %.2f" % (d[0], d[1], dlr), "VO has t:", t in V)
