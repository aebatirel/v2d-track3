"""Verifier run 2 (C1): sensitivity of the spoon's mid-axis skew sign to a LATERAL asymmetry between the side markers
M1 (+y_P, near bowl) and M2 (-y_P, further up the handle). Dig 13's MC puts both at halfw(z)+base_h+0.85r (near-equal).
Here M2's lateral offset is changed by dM2 (mm, + = further out), M1 kept. Geometry from dig 13 primitives; frame/skew
code is my own (exact area moments, degree-3 triangle formula). Rule: PCA axes, mid axis signed by positive skew.
Output per shape: model lateral centres of M1/M2 and skew along the mid axis oriented to M2 (>0 => frame B).
Usage: v2_latasym.py N seed -> out/v2_latasym_<seed>.jsonl"""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from spoon_model import spoon_body, sphere, cylinder, assemble
N, seed = int(sys.argv[1]), int(sys.argv[2]); rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v2_latasym_{seed}.jsonl"
DM2 = [-9, -6, -4, -2, -1, 0, 1, 2, 4]


def draw():
    we = rng.uniform(0.0095, 0.012); ratio = rng.uniform(0.75, 1.05); Lb = rng.uniform(0.085, 0.10)
    body = dict(L=rng.uniform(0.28, 0.31), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
                tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015), asym_y=0.0,
                handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035), ns=300, nphi=48)
    m1 = rng.uniform(0.104, 0.124)
    return dict(body=body, m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.05), marker_x=rng.uniform(-0.003, 0.003),
                r_marker=rng.uniform(0.0066, 0.0076), base_h=rng.uniform(0.002, 0.006), keep_frac=rng.uniform(0.5, 0.95))


def build(p, dm2=0.0):
    b = p["body"]; L, Lb = b["L"], b["Lb"]; V, F, halfw = spoon_body(**b); parts = [(V, F)]
    ramp = lambda z: b["handle_off_x"] * np.clip((z - Lb) / (L - Lb), 0, 1); r, bh, rb = p["r_marker"], p["base_h"], 0.0055
    lat = {}
    for nm, side, extra in (("m1", 1, 0.0), ("m2", -1, dm2)):
        z = p[nm + "_z"]; xm = p["marker_x"] + ramp(z); ye = side * (halfw(z) + extra)
        parts.append(cylinder(np.array([xm, ye, z]), np.array([xm, ye + side * bh, z]), rb))
        cy = ye + side * (bh + 0.85 * r); lat[nm] = abs(cy)
        parts.append(sphere(np.array([xm, cy, z]), r, keep_dir=np.array([0, side, 0.0]), keep_frac=p["keep_frac"]))
    xm = p["marker_x"] + ramp(L)
    parts.append(cylinder(np.array([xm, 0, L - 0.001]), np.array([xm, 0, L + bh]), rb))
    parts.append(sphere(np.array([xm, 0, L + bh + 0.85 * r]), r, keep_dir=np.array([0, 0, 1.0]), keep_frac=p["keep_frac"]))
    V, F = assemble(parts)
    return V, F, lat


def skews(V, F):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = a.sum()
    c = (a[:, None] * T.mean(1)).sum(0) / A; Q = T - c
    C = (sum(np.einsum("n,ni,nj->ij", a, Q[:, k], Q[:, k]) for k in range(3)) + np.einsum("n,ni,nj->ij", a, Q.sum(1), Q.sum(1))) / 12 / A
    w, E = np.linalg.eigh(C); out = []
    for i in range(3):
        f = Q @ E[:, i]; x, y, z = f.T
        h3 = x ** 3 + y ** 3 + z ** 3 + x * x * (y + z) + y * y * (x + z) + z * z * (x + y) + x * y * z
        out.append((a * h3).sum() / 10 / A / w[i] ** 1.5)
    toM2 = out[1] * np.sign(-E[1, 1]); toH = out[2] * np.sign(E[2, 2])
    return float(toM2), float(toH), float(A), np.sqrt(w)


if __name__ == "__main__":
    for i in range(N):
        p = draw(); rec = {"seed": seed, "i": i, "res": {}}
        for d in DM2:
            V, F, lat = build(p, d / 1000)
            toM2, toH, A, sd = skews(V, F)
            rec["res"][d] = dict(toM2=toM2, toH=toH, latM1=lat["m1"] * 1e3, latM2=lat["m2"] * 1e3)
        rec["A_cm2"] = A * 1e4; rec["sd_mm"] = (sd * 1e3).tolist()
        with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
        r0 = rec["res"][0]
        print(i, f"lat M1 {r0['latM1']:.1f} M2 {r0['latM2']:.1f} mm |", " ".join(f"{d:+d}:{rec['res'][d]['toM2']:+.3f}" for d in DM2), flush=True)
