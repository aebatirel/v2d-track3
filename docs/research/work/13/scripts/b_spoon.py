"""Stage B: spoon roll predicted by each candidate rule on realistic spoon shapes (Monte Carlo).
Construction frame P: z_P bowl tip -> handle end, x_P toward the CONVEX back of the bowl, y_P = z_P x x_P (M1 side, [V] video).
Frame label: published axis i = s_i * P axis i. Roll 'A' = s_x=+1 (x to convex back, y to M1); 'B' = s_x=-1 (x to concave
inside, y to M2). s_z from skew_z (expected +1).
Usage: b_spoon.py N seed [mode]   mode: round (th/2w 0.75-1.05, default) | oval (0.5-0.75) | nomark (round, no markers)
Writes out/b_spoon_<mode>_<seed>.jsonl (one sample per line, appended as computed)."""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from spoon_model import spoon_body, sphere, cylinder, assemble
from b_feats import feats
import b_search as B

N = int(sys.argv[1]); seed = int(sys.argv[2]); mode = sys.argv[3] if len(sys.argv) > 3 else "round"
rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_{mode}_{seed}.jsonl"


def spoon(p):
    b = p["body"]; L = b["L"]; Lb = b["Lb"]
    V, F, halfw = spoon_body(**b)
    parts = [(V, F)]
    if not p["markers"]:
        return V, F
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
    we = rng.uniform(0.0095, 0.012)
    ratio = rng.uniform(0.75, 1.05) if mode in ("round", "nomark") else rng.uniform(0.5, 0.75)
    Lb = rng.uniform(0.085, 0.10)
    body = dict(L=rng.uniform(0.28, 0.31), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
                tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015),
                asym_y=rng.uniform(-0.02, 0.02), handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035),
                ns=360, nphi=56)
    m1 = rng.uniform(0.104, 0.124)
    return dict(body=body, ratio=ratio, markers=(mode != "nomark"), m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.05),
                marker_x=rng.uniform(-0.003, 0.003), r_marker=rng.uniform(0.0066, 0.0076), base_h=rng.uniform(0.002, 0.006),
                keep_frac=rng.uniform(0.5, 0.95), bases=bool(rng.random() < 0.85))


def frame_from(fix, S):
    """fix: dict axis->sign for 1 or 2 axes; z from skew if not fixed; complete right-handed."""
    s = dict(fix)
    if 2 not in s and len(s) < 2:
        s[2] = 1 if S["skew"][2] > 0 else -1
    if len(s) == 2:
        miss = ({0, 1, 2} - set(s)).pop(); s[miss] = int(np.prod(list(s.values())))
    return s


def label(s):
    return ("A" if s[0] > 0 else "B") + ("" if s[2] > 0 else "-zflip")


def rank_of(S, rn):
    return np.abs(np.array(S["skew"])) / np.array(S["skew_se1"]) if rn == "skewz" else np.abs(np.array(S[rn]))


def rules(S):
    out = {}
    sg = lambda v: 1 if v > 0 else -1
    sk = S["skew"]
    out["n07_skew_x"] = label(frame_from({0: sg(sk[0])}, S))
    out["n07_skew_y"] = label(frame_from({1: sg(sk[1])}, S))
    out["n07_hybrid.02"] = out["n07_skew_y"] if abs(sk[1]) >= 0.02 else out["n07_skew_x"]
    out["n07_larger_abs"] = out["n07_skew_x"] if abs(sk[0]) >= abs(sk[1]) else out["n07_skew_y"]
    for nm, (st, pol, ax) in {"noisy_q10_y": ("q10", 1, 1), "noisy_-mloabs_y": ("m_lo_abs", -1, 1), "noisy_m5_y": ("m5", 1, 1),
                              "noisy_s4_y": ("s4", 1, 1), "noisy_-shalf_x": ("shalf", -1, 0), "noisy_far3d_x": ("far3d", 1, 0)}.items():
        out[nm] = label(frame_from({ax: sg(pol * S[st][ax])}, S))
    for (_, rn, sn, p) in F2_FIT:
        a = int(np.argmax(rank_of(S, rn)[:2]))
        out[f"F2|{rn}|{'+' if p > 0 else '-'}{sn}"] = label(frame_from({a: sg(p * S[sn][a])}, S))
    for (_, rn, sn, p) in F2B_FIT:
        top = np.argsort(-rank_of(S, rn))[:2]
        out[f"F2b|{rn}|{'+' if p > 0 else '-'}{sn}"] = label(frame_from({int(t): sg(p * S[sn][t]) for t in top}, S))
    hy = []
    for h in HYB:
        (s1, p1, a1), (s2, p2, a2) = h["prim"], h["fall"]
        a1 = "xy".index(a1); a2 = "xy".index(a2); tau = np.sqrt(max(h["lo"], 1e-12) * h["hi"])
        if abs(S[s1][a1]) >= tau:
            hy.append(label(frame_from({a1: sg(p1 * S[s1][a1])}, S)))
        else:
            hy.append(label(frame_from({a2: sg(p2 * S[s2][a2])}, S)))
    out["F3_shareA"] = float(np.mean([h.startswith("A") for h in hy]))
    out["F3_top5"] = hy[:5]
    return out


ok2, n2 = B.fam_F2(B.D); F2_FIT = [n2[k] for k in np.nonzero(ok2.all(1))[0]]
okb, nb = B.fam_F2b(B.D); F2B_FIT = [nb[k] for k in np.nonzero(okb.all(1))[0]]
HYB = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_hybrids.json"))

if __name__ == "__main__":
    KEEP = ["skew", "kurt", "skew_se1", "ssq", "s4", "shalf", "afrac", "negmed", "q05", "q10", "m5", "far3d", "m_lo_abs", "ext"]
    for i in range(N):
        p = draw(); V, F = spoon(p)
        S = feats(V, F, hull=True)
        rec = dict(p=p, dev=S["_axis_dev_deg"], sd_mm=S["_sd_mm"], c_mm=S["_c_mm"], S={k: S[k] for k in KEEP}, R=rules(S))
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        if i % 25 == 0:
            print(i, "skew", np.round(S["skew"], 3), "dev", np.round(S["_axis_dev_deg"], 2), rec["R"]["n07_skew_x"], rec["R"]["n07_skew_y"], flush=True)
