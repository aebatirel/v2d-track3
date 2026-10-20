"""Verifier run 2 (C1): spoon mid-axis skew with side markers at the positions MEASURED by the verifier in ep36 f200/f260 and Stage A
(M1 lateral 19-26 mm roughly in-plane; M2 lateral 13-20 mm, raised 6-15 mm toward the CONCAVE face = -x_P). Bodies: dig 13 Stage B
round-handle MC (spoon_body). Frame/skew/influence code is my own. P(B) = Phi(skew_toM2*sqrt(n)/se1) averaged over the dig's
fitted n posterior (work/13/out/c_noisy_post.npy, reproduced by the earlier verifier).
Variants: 'meas' (all measured), 'meas_inplane' (M2 x offset 0), 'model' (dig placement: both at halfw+base+0.85r, in-plane).
Usage: v2_measured.py N seed -> out/v2_measured_<seed>.jsonl"""
import sys, json, numpy as np
from scipy.stats import norm
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from spoon_model import spoon_body, sphere, cylinder, assemble
N, seed = int(sys.argv[1]), int(sys.argv[2]); rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v2_measured_{seed}.jsonl"
ns, post = np.load("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_noisy_post.npy")


def draw():
    we = rng.uniform(0.0095, 0.012); ratio = rng.uniform(0.75, 1.05); Lb = rng.uniform(0.085, 0.10)
    body = dict(L=rng.uniform(0.28, 0.31), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
                tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015), asym_y=0.0,
                handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035), ns=300, nphi=48)
    m1 = rng.uniform(0.104, 0.124)
    return dict(body=body, m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.05), r=rng.uniform(0.0066, 0.0076), bh=rng.uniform(0.002, 0.006),
                kf=rng.uniform(0.5, 0.95), lat1=rng.uniform(0.019, 0.026), x1=rng.uniform(-0.004, 0.004),
                lat2=rng.uniform(0.013, 0.020), x2=-rng.uniform(0.006, 0.015))


def marker(axis_pt, c, r, bh, kf, flat=True):
    d = c - axis_pt
    if flat: d[2] = 0
    d /= np.linalg.norm(d)
    s1 = c - d * 0.85 * r; s0 = s1 - d * bh
    return [cylinder(s0, s1, 0.0055), sphere(c, r, keep_dir=d, keep_frac=kf)]


def build(p, variant):
    b = p["body"]; L, Lb = b["L"], b["Lb"]; V, F, halfw = spoon_body(**b); parts = [(V, F)]
    ramp = lambda z: b["handle_off_x"] * np.clip((z - Lb) / (L - Lb), 0, 1); r, bh = p["r"], p["bh"]
    for nm, side, lat, xo in (("m1", 1, p["lat1"], p["x1"]), ("m2", -1, p["lat2"], p["x2"])):
        z = p[nm + "_z"]; ax = np.array([ramp(z), 0.0, z])
        if variant == "model":
            lat = halfw(z) + bh + 0.85 * r; xo = 0.0
        elif variant == "meas_inplane" and nm == "m2":
            xo = 0.0
        c = np.array([ramp(z) + xo, side * lat, z]); parts += marker(ax, c, r, bh, p["kf"])
    c = np.array([ramp(L), 0, L + bh + 0.85 * r]); parts += marker(np.array([ramp(L), 0, L - 0.05]), c, r, bh, p["kf"], flat=False)
    return assemble(parts)


def analyse(V, F, nsamp=200000):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = a.sum()
    c = (a[:, None] * T.mean(1)).sum(0) / A; Q = T - c
    C = (sum(np.einsum("n,ni,nj->ij", a, Q[:, k], Q[:, k]) for k in range(3)) + np.einsum("n,ni,nj->ij", a, Q.sum(1), Q.sum(1))) / 12 / A
    w, E = np.linalg.eigh(C); sk = []
    for i in range(3):
        f = Q @ E[:, i]; x, y, z = f.T
        h3 = x ** 3 + y ** 3 + z ** 3 + x * x * (y + z) + y * y * (x + z) + z * z * (x + y) + x * y * z
        sk.append((a * h3).sum() / 10 / A / w[i] ** 1.5)
    # influence-function SE of the sample skew (area-weighted surface samples)
    idx = rng.choice(len(F), nsamp, p=a / A); u1, u2 = rng.random(nsamp), rng.random(nsamp); m = u1 + u2 > 1
    u1[m], u2[m] = 1 - u1[m], 1 - u2[m]; P = T[idx, 0] + u1[:, None] * (T[idx, 1] - T[idx, 0]) + u2[:, None] * (T[idx, 2] - T[idx, 0])
    se1 = []
    for i in range(3):
        u = ((P - c) @ E[:, i]) / np.sqrt(w[i]); g = sk[i]
        se1.append(np.std(u ** 3 - 3 * u - 1.5 * g * (u ** 2 - 1)))
    toM2 = sk[1] * np.sign(-E[1, 1]); toH = sk[2] * np.sign(E[2, 2]); toConc = sk[0] * np.sign(-E[0, 0])
    PB = float((norm.cdf(toM2 * np.sqrt(ns) / se1[1]) * post).sum())
    midIsY = bool(np.argmax(np.abs(E[1])) == 1)
    return dict(toM2=float(toM2), toH=float(toH), toConc=float(toConc), se1y=float(se1[1]), PB=PB, midIsY=midIsY, sd_mm=(np.sqrt(w) * 1e3).round(2).tolist())


if __name__ == "__main__":
    for i in range(N):
        p = draw(); rec = {"i": i, "p": {k: v for k, v in p.items() if k != "body"}, "res": {}}
        for v in ("model", "meas_inplane", "meas"):
            V, F = build(p, v); rec["res"][v] = analyse(V, F)
        with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
        print(i, f"lat1 {p['lat1']*1e3:.1f} lat2 {p['lat2']*1e3:.1f} x2 {p['x2']*1e3:.1f} |",
              " ".join(f"{v}: toM2 {r['toM2']:+.3f} PB {r['PB']:.2f} conc {r['toConc']:+.3f}" for v, r in rec["res"].items()), flush=True)
