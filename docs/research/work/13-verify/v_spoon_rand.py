"""Verifier (C2): random combined asymmetries on the Stage B round-handle spoon: handle bend d~U(-D,D), bowl/section
lateral asymmetry a~U(-Amax,Amax), M3 lateral offset ~U(-2,2) mm. Reports skew along the mid axis oriented to M2.
Usage: v_spoon_rand.py N seed Dmm Amax -> out/v_spoon_rand_<seed>_<Dmm>_<Amax>.jsonl"""
import sys, json, numpy as np
sys.argv, args = sys.argv[:1] + ["0", "0"], sys.argv[1:]
import v_spoon_asym as M
N, seed, Dmm, Amax = int(args[0]), int(args[1]), float(args[2]), float(args[3])
M.rng = np.random.default_rng(seed); rng = np.random.default_rng(seed + 1000)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v_spoon_rand_{seed}_{Dmm:g}_{Amax:g}.jsonl"
for i in range(N):
    p = M.draw(); d = rng.uniform(-Dmm, Dmm) / 1000; a = rng.uniform(-Amax, Amax); m3 = rng.uniform(-0.002, 0.002)
    V, F = M.build(p, m3_dy=m3, asym=a); V = M.deform(V, p, d, 0.0)
    E, toM2, toH = M.frame(V, F)
    rec = dict(d_mm=d * 1000, a=a, m3_mm=m3 * 1000, skew_toM2=float(toM2), skew_toHandle=float(toH))
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(i, json.dumps({k: round(v, 4) for k, v in rec.items()}), flush=True)
