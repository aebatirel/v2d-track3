"""Verifier run 2 (C1): sensitivity of skew toward M2 to UNEQUAL captured sphere fractions of M1 vs M2 (public scans show
within-object marker capture ratios up to ~1.7, out/markers.log), plus a random combined prior.
Usage: v2_kfasym.py N seed -> out/v2_kfasym_<seed>.jsonl"""
import sys, json, numpy as np
sys.argv, args = sys.argv[:1] + ["0", "0"], sys.argv[1:]
import v2_latasym as M
from spoon_model import spoon_body, sphere, cylinder, assemble
N, seed = int(args[0]), int(args[1]); M.rng = np.random.default_rng(seed); rng = np.random.default_rng(seed + 7)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v2_kfasym_{seed}.jsonl"

def build(p, kf1, kf2, dm2=0.0):
    b = p["body"]; L, Lb = b["L"], b["Lb"]; V, F, halfw = spoon_body(**b); parts = [(V, F)]
    ramp = lambda z: b["handle_off_x"] * np.clip((z - Lb) / (L - Lb), 0, 1); r, bh, rb = p["r_marker"], p["base_h"], 0.0055
    for nm, side, extra, kf in (("m1", 1, 0.0, kf1), ("m2", -1, dm2, kf2)):
        z = p[nm + "_z"]; xm = p["marker_x"] + ramp(z); ye = side * (halfw(z) + extra)
        parts.append(cylinder(np.array([xm, ye, z]), np.array([xm, ye + side * bh, z]), rb))
        parts.append(sphere(np.array([xm, ye + side * (bh + 0.85 * r), z]), r, keep_dir=np.array([0, side, 0.0]), keep_frac=kf))
    xm = p["marker_x"] + ramp(L)
    parts.append(cylinder(np.array([xm, 0, L - 0.001]), np.array([xm, 0, L + bh]), rb))
    parts.append(sphere(np.array([xm, 0, L + bh + 0.85 * r]), r, keep_dir=np.array([0, 0, 1.0]), keep_frac=p["keep_frac"]))
    return assemble(parts)

for i in range(N):
    p = M.draw(); rec = {"i": i, "res": {}}
    for nm, (k1, k2) in {"eq.75": (.75, .75), "M1.95_M2.55": (.95, .55), "M1.55_M2.95": (.55, .95), "M1.85_M2.65": (.85, .65)}.items():
        V, F = build(p, k1, k2); rec["res"][nm] = M.skews(V, F)[0]
    # combined random prior: kf each U(0.5,0.95) independent; lateral M2-vs-M1 extra ~ U(-3,+3) mm
    k1, k2, d = rng.uniform(.5, .95), rng.uniform(.5, .95), rng.uniform(-3, 3)
    V, F = build(p, k1, k2, d / 1000); rec["rand"] = dict(kf1=k1, kf2=k2, dm2=d, toM2=M.skews(V, F)[0])
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(i, {k: round(v, 3) for k, v in rec["res"].items()}, {k: round(v, 3) for k, v in rec["rand"].items()}, flush=True)
