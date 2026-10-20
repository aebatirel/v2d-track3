"""Stage C: P(spoon frame B) under mechanism (b): the organisers sample n surface points, take PCA axes AND skew signs from
that sample (mid axis and z by positive skew). Spoon meshes rebuilt from Stage B MC params (round/oval/nomark).
Usage: c_spoonPb.py mode n_shapes reps -> out/c_spoonPb_<mode>.log (stdout)."""
import sys, json, glob, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from c_cdo import spoon
mode, NS, REPS = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rng = np.random.default_rng(11)
recs = [json.loads(l) for f in sorted(glob.glob(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_{mode}_*.jsonl")) for l in open(f)]
NGRID = [1000, 3000, 10000, 30000, 100000]
res = {n: [] for n in NGRID}; resz = {n: [] for n in NGRID}
for r in recs[:NS]:
    p = r["p"]; V, F = spoon(p, markers=(mode != "nomark"))
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); cw = np.cumsum(a) / a.sum()
    for n in NGRID:
        hits = 0; hz = 0
        for _ in range(REPS):
            idx = np.minimum(np.searchsorted(cw, rng.random(n)), len(F) - 1)
            r1, r2 = rng.random(n), rng.random(n); s = np.sqrt(r1)[:, None]
            P = (1 - s) * T[idx, 0] + s * (1 - r2[:, None]) * T[idx, 1] + s * r2[:, None] * T[idx, 2]
            X = P - P.mean(0); w, E = np.linalg.eigh(X.T @ X / n)
            ey = E[:, 1] * np.sign(E[1, 1]); ez = E[:, 2] * np.sign(E[2, 2])     # orient to construction y_P, z_P
            py, pz = X @ ey, X @ ez
            hits += (py ** 3).mean() < 0                                          # B: positive-skew direction is -y_P (M2 side)
            hz += (pz ** 3).mean() > 0
        res[n].append(hits / REPS); resz[n].append(hz / REPS)
for n in NGRID:
    print(f"{mode} n={n:6d}  P(B) mean over {len(res[n])} shapes {np.mean(res[n]):.3f} (min {np.min(res[n]):.2f})  P(z ok) {np.mean(resz[n]):.3f}", flush=True)
