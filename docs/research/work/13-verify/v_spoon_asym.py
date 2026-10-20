"""Verifier (claim C2): how robust is the spoon's mid-axis (y) skew sign to small real-object asymmetries that the
Stage B model leaves out? Uses dig 13's lofted body + marker primitives (geometry only), my own frame/skew code.
Perturbations applied to the assembled spoon (markers move with the wood):
  bend: y += d * ((z-Lb)/(L-Lb))^2 for z > Lb   (lateral handle bow, d = end offset)
  yaw : rotate the handle part (z > Lb) about x by angle g around the neck point (implemented as y += tan(g)*(z-Lb))
Frame rule: PCA axes; max and mid axes signed by positive skew; B if the mid axis points to -y_P (M2 side).
Usage: v_spoon_asym.py N seed  -> out/v_spoon_asym_<seed>.jsonl"""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from spoon_model import spoon_body, sphere, cylinder, assemble
N, seed = int(sys.argv[1]), int(sys.argv[2]); rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v_spoon_asym_{seed}.jsonl"


def draw():
    we = rng.uniform(0.0095, 0.012); ratio = rng.uniform(0.75, 1.05); Lb = rng.uniform(0.085, 0.10)
    body = dict(L=rng.uniform(0.28, 0.31), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
                tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015), asym_y=0.0,
                handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035), ns=300, nphi=48)
    m1 = rng.uniform(0.104, 0.124)
    return dict(body=body, m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.05), marker_x=rng.uniform(-0.003, 0.003),
                r_marker=rng.uniform(0.0066, 0.0076), base_h=rng.uniform(0.002, 0.006), keep_frac=rng.uniform(0.5, 0.95))


def build(p, markers=True, m3_dy=0.0, asym=0.0):
    b = dict(p["body"]); b["asym_y"] = asym; L, Lb = b["L"], b["Lb"]; V, F, halfw = spoon_body(**b); parts = [(V, F)]
    if not markers: return V, F
    ramp = lambda z: b["handle_off_x"] * np.clip((z - Lb) / (L - Lb), 0, 1); r, bh, rb = p["r_marker"], p["base_h"], 0.0055
    for nm, side in (("m1", 1), ("m2", -1)):
        z = p[nm + "_z"]; xm = p["marker_x"] + ramp(z); ye = side * halfw(z)
        parts.append(cylinder(np.array([xm, ye, z]), np.array([xm, ye + side * bh, z]), rb))
        parts.append(sphere(np.array([xm, ye + side * (bh + 0.85 * r), z]), r, keep_dir=np.array([0, side, 0.0]), keep_frac=p["keep_frac"]))
    xm = p["marker_x"] + ramp(L)
    parts.append(cylinder(np.array([xm, m3_dy, L - 0.001]), np.array([xm, m3_dy, L + bh]), rb))
    parts.append(sphere(np.array([xm, m3_dy, L + bh + 0.85 * r]), r, keep_dir=np.array([0, 0, 1.0]), keep_frac=p["keep_frac"]))
    return assemble(parts)


def frame(V, F):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = a.sum()
    c = (a[:, None] * T.mean(1)).sum(0) / A; Q = T - c
    C = (sum(np.einsum("n,ni,nj->ij", a, Q[:, k], Q[:, k]) for k in range(3)) + np.einsum("n,ni,nj->ij", a, Q.sum(1), Q.sum(1))) / 12 / A
    w, E = np.linalg.eigh(C); sk = []
    for i in range(3):
        f = Q @ E[:, i]; x, y, z = f.T
        h3 = x ** 3 + y ** 3 + z ** 3 + x * x * (y + z) + y * y * (x + z) + z * z * (x + y) + x * y * z
        sk.append((a * h3).sum() / 10 / A / w[i] ** 1.5)
    sk = np.array(sk)
    toM2 = sk[1] * np.sign(-E[1, 1]); toHandle = sk[2] * np.sign(E[2, 2])   # skew along mid axis oriented to -y_P, max axis to +z_P
    return E * np.sign(sk)[None, :], toM2, toHandle


def deform(V, p, d_bend, g_yaw):
    b = p["body"]; L, Lb = b["L"], b["Lb"]; V = V.copy(); z = V[:, 2]; u = np.clip((z - Lb) / (L - Lb), 0, None)
    V[:, 1] += d_bend * u ** 2 + np.tan(g_yaw) * np.clip(z - Lb, 0, None)
    return V


if __name__ == "__main__":
    PERT = [("none", 0, 0)] + [(f"bend{d:+.1f}mm", d / 1000, 0) for d in (-2, -1, -0.5, 0.5, 1, 2)] + \
           [(f"yaw{g:+.2f}deg", 0, np.radians(g)) for g in (-0.5, -0.25, 0.25, 0.5)] + \
           [(f"m3y{d:+.0f}mm", d / 1000, 0) for d in (-3, -1.5, 1.5, 3)] + [(f"asym{a:+.2f}", 0, a) for a in (-0.06, -0.03, 0.03, 0.06)]
    for i in range(N):
        p = draw(); V0, F = build(p); rec = {"p": p, "res": {}}
        for nm, d, g in PERT:
            if nm.startswith("m3y") or nm.startswith("asym"):
                Vx, Fx = build(p, m3_dy=d if nm.startswith("m3y") else 0.0, asym=g if nm.startswith("asym") else 0.0); Vx = deform(Vx, p, 0, 0)
            else:
                Vx, Fx = deform(V0, p, d, g), F
            E, toM2, toH = frame(Vx, Fx)
            rec["res"][nm] = dict(B=bool(toM2 > 0), zok=bool(toH > 0), skew_toM2=float(toM2), skew_toHandle=float(toH))
        with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
        print(i, {k: round(v["skew_toM2"], 4) for k, v in rec["res"].items()}, flush=True)
