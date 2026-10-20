"""Stage C: expected CD-O (kit scorer function) and R1-frame stability of spoon reconstruction options (Monte Carlo).
Truth = parametric spoon + 3 markers (Stage B 'round' prior). Each option builds an estimate in the SAME physical
coordinates (no pose error), so frame deltas isolate reconstruction-shape effects.
Usage: c_cdo.py N seed [truth_markers=1]  -> appends JSON lines to out/c_cdo_<seed>_m<truth_markers>.jsonl"""
import sys, json, copy, importlib.util, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from spoon_model import sphere, cylinder, assemble, frame_and_skews

spec = importlib.util.spec_from_file_location(
    "cdo", "/Users/aebatirel/Documents/Code/v2d-research/kit/v2d_submission_kit/metric_code/track_3/CD-O.py")
cdo = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdo)

MAIN = __name__ == "__main__"
N = int(sys.argv[1]) if MAIN else 0; seed = int(sys.argv[2]) if MAIN else 0
TM = int(sys.argv[3]) if MAIN and len(sys.argv) > 3 else 1
rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_cdo_{seed}_m{TM}.jsonl"


def body(L, Lb, wb, wn, we, tb, th, Db, neck, ns=300, nphi=48, asym_y=0.0, handle_off_x=0.0, fill=False, drop_under=False):
    """Copy of spoon_model.spoon_body with options: fill = concave side flattened at the rim plane (visual hull);
    drop_under = remove the convex back of the bowl (never-seen underside, open mesh)."""
    s = np.linspace(0.0, L, ns)
    u = np.clip((s - Lb / 2) / (Lb / 2), -1, 1)
    wbowl = wb * np.sqrt(np.clip(1 - u ** 2, 0, None))
    sh = np.clip((s - Lb) / (L - Lb), 0, 1)
    wh = wn + (we - wn) * sh
    w = np.where(s < Lb * 0.75, wbowl, np.maximum(wbowl, wh))
    endr = 0.010; k = np.clip((L - s) / endr, 0, 1); w = np.where(s > L - endr, wh * np.sqrt(1 - (1 - k) ** 2), w)
    w[0] = 0; w[-1] = 0
    bl = np.clip((s - Lb * 0.8) / neck, 0, 1)
    t = tb * (1 - bl) + th * bl
    t = np.minimum(t, 2 * w + 1e-6)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    S, P = np.meshgrid(s, phi, indexing="ij")
    W = np.interp(S, s, w); Tt = np.interp(S, s, t)
    cy = np.cos(P); sx = np.sin(P)
    U = (S - Lb / 2) / (Lb / 2)
    D = Db * np.clip(1 - cy ** 2 - U ** 2, 0, None)
    Dm = np.where(sx > 0, D, 0.0) if fill else D
    X = 0.5 * Tt * sx + Dm + handle_off_x * np.clip((S - Lb) / (L - Lb), 0, 1)
    Y = W * cy * (1 + asym_y * cy)
    V = np.stack([X, Y, S], -1).reshape(-1, 3)
    idx = np.arange(ns * nphi).reshape(ns, nphi); F = []
    for i in range(ns - 1):
        a = idx[i]; b = idx[i + 1]; a2 = np.roll(a, -1); b2 = np.roll(b, -1)
        F += [np.stack([a, b, b2], 1), np.stack([a, b2, a2], 1)]
    F = np.concatenate(F)
    if drop_under:
        sxv = sx.reshape(-1); sv = S.reshape(-1)
        fm = sxv[F].mean(1); fs = sv[F].mean(1)
        F = F[~((fm > 0.25) & (fs < Lb))]
    T = V[F]; ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return V, F[ar > 1e-14], (lambda z: np.interp(z, s, w))


def spoon(p, markers=True, **kw):
    b = p["body"]; L = b["L"]; Lb = b["Lb"]
    V, F, halfw = body(**b, **kw)
    if not markers:
        return V, F
    parts = [(V, F)]
    ramp = lambda z: b["handle_off_x"] * np.clip((z - Lb) / (L - Lb), 0, 1)
    r, bh, rb, kf = p["r_marker"], p["base_h"], 0.0055, p["keep_frac"]
    for name, side in (("m1", +1), ("m2", -1)):
        z = p[name + "_z"]; xm = p["marker_x"] + ramp(z); ye = side * halfw(z)
        if p["bases"]:
            parts.append(cylinder(np.array([xm, ye, z]), np.array([xm, ye + side * bh, z]), rb))
        parts.append(sphere(np.array([xm, ye + side * (bh + 0.85 * r), z]), r, keep_dir=np.array([0, side, 0.0]), keep_frac=kf))
    xm = p["marker_x"] + ramp(L)
    if p["bases"]:
        parts.append(cylinder(np.array([xm, 0, L - 0.001]), np.array([xm, 0, L + bh]), rb))
    parts.append(sphere(np.array([xm, 0, L + bh + 0.85 * r]), r, keep_dir=np.array([0, 0, 1.0]), keep_frac=kf))
    return assemble(parts)


def draw():
    we = rng.uniform(0.0095, 0.012); ratio = rng.uniform(0.75, 1.05); Lb = rng.uniform(0.085, 0.10)
    bd = dict(L=rng.uniform(0.28, 0.31), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
              tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015),
              asym_y=rng.uniform(-0.02, 0.02), handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035))
    m1 = rng.uniform(0.104, 0.124)
    return dict(body=bd, m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.05), marker_x=rng.uniform(-0.003, 0.003),
                r_marker=rng.uniform(0.0066, 0.0076), base_h=rng.uniform(0.002, 0.006),
                keep_frac=rng.uniform(0.5, 0.95), bases=bool(rng.random() < 0.85))


PRIOR_MEAN = dict(body=dict(L=0.295, Lb=0.0925, wb=0.026, wn=0.0085, we=0.01075, tb=0.00475, th=2 * 0.01075 * 0.9,
                            Db=0.0105, asym_y=0.0, handle_off_x=0.0, neck=0.025),
                  m1_z=0.114, m2_z=0.154, marker_x=0.0, r_marker=0.0072, base_h=0.004, keep_frac=0.75, bases=True)


def fitted(p, rel_plan=0.02, rel_th=0.15, rel_db=0.30, rel_tb=0.25, marker_mm=2.0):
    """Template fitted to silhouettes + stereo: planform to ~2%, thickness ~15%, bowl depth ~30%, markers ~2 mm;
    unobservable asymmetry/offset set to 0."""
    q = copy.deepcopy(p); b = q["body"]
    for k in ("L", "Lb", "wb", "wn", "we"):
        b[k] *= 1 + rel_plan * rng.standard_normal()
    b["th"] *= 1 + rel_th * rng.standard_normal(); b["Db"] *= max(0.2, 1 + rel_db * rng.standard_normal())
    b["tb"] *= max(0.4, 1 + rel_tb * rng.standard_normal()); b["neck"] *= max(0.5, 1 + 0.2 * rng.standard_normal())
    b["asym_y"] = 0.0; b["handle_off_x"] = 0.0
    for k in ("m1_z", "m2_z"):
        q[k] += marker_mm * 1e-3 * rng.standard_normal()
    q["marker_x"] = 0.0
    return q


def noisy(V, F, sigma=0.0015, ncomp=12):
    """Smooth, spatially correlated displacement (wavelength 2-6 cm), mostly normal-ish (random direction field)."""
    k = rng.normal(size=(ncomp, 3)); k /= np.linalg.norm(k, axis=1, keepdims=True)
    k *= (2 * np.pi / rng.uniform(0.02, 0.06, ncomp))[:, None]
    ph = rng.uniform(0, 2 * np.pi, ncomp); dirs = rng.normal(size=(ncomp, 3))
    field = np.sin(V @ k.T + ph) @ dirs
    field *= sigma / np.sqrt((field ** 2).sum(1).mean())
    return V + field, F


def frame(V, F):
    c, w, E, sk, A = frame_and_skews(V, F)
    return c, E, sk, A


def compare(ft, fe):
    ct, Et, skt, At = ft; ce, Ee, ske, Ae = fe
    ang = [float(np.degrees(np.arccos(min(1.0, abs(Et[:, i] @ Ee[:, i]))))) for i in range(3)]
    return dict(dc_mm=float(1000 * np.linalg.norm(ce - ct)), dc_vec_mm=(1000 * (ce - ct)).round(2).tolist(), ang_deg=np.round(ang, 3).tolist(),
                sk=np.round(ske, 4).tolist(), same_sign=[bool(np.sign(ske[i]) == np.sign(skt[i])) for i in range(3)],
                area_ratio=float(Ae / At))


if __name__ == "__main__":
    for i in range(N):
        p = draw(); sd = int(rng.integers(1 << 30))
        Vt, Ft = spoon(p, markers=bool(TM)); ft = frame(Vt, Ft)
        q = fitted(p); q_nf = fitted(p, rel_plan=0.05, rel_th=0.3, rel_db=0.5, marker_mm=5.0)
        Vn, Fn = noisy(*spoon(p, markers=True), sigma=0.0015)
        opts = {
            "F_retess_floor": spoon(p, bool(TM), ns=257, nphi=40),
            "T0_prior_mean": spoon(PRIOR_MEAN, True),
            "T1_fit": spoon(q, True),
            "T1_fit_nomark": spoon(q, False),
            "T1_fit_loose": spoon(q_nf, True),
            "T3_hull_filled": spoon(p, True, fill=True),
            "T3_hull_filled_nomark": spoon(p, False, fill=True),
            "T4_stereo_noise1.5": (Vn, Fn),
            "T4_noise_nounder": noisy(*spoon(p, True, drop_under=True), sigma=0.0015),
            "T5_category_draw": spoon(draw(), True),
            "T5_category_draw_nomark": spoon(draw(), False),
        }
        rec = dict(i=i, p=p, sk_true=np.round(ft[2], 4).tolist(), opts={})
        for nm, (Ve, Fe) in opts.items():
            cd = cdo._object_chamfer_cm((Vt, Ft), (Ve, Fe), sd)
            rec["opts"][nm] = dict(cdo_cm=round(float(cd), 4), **compare(ft, frame(Ve, Fe)))
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(i, {k: v["cdo_cm"] for k, v in rec["opts"].items()}, flush=True)
