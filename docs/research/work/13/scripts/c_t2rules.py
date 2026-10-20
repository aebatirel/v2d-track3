"""Stage C: test Track 3 sign-rule hypotheses on the public Track 2 scans (fresh holdout).
Role order (min, mid, max variance): Track 3 = (x, y, z); Track 2 stored = (y, x, z).
Features: Stage B catalogue (b_feats.feats) along recomputed PCA axes oriented to the STORED axes, index 0 sign fixed.
Writes out/c_t2feats.json (cache) and prints counts. Usage: c_t2rules.py"""
import os, sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import b_feats
from b_feats import feats, quad_points
import b_search as B
AXES = os.environ.get("C_T2_AXES", "stored")   # "stored": statistics along the stored axes (default); "pca": recomputed PCA


def r1_stored(V, F, ref=np.eye(3)):
    P, W, _ = quad_points(V, F)
    c = W @ P
    E = ref.copy()
    lam = np.array([((W * ((P - c) @ E[:, i]) ** 2)).sum() for i in range(3)])
    return c, E, lam


if AXES == "stored":
    b_feats.r1_frame = r1_stored

D2 = "/Users/aebatirel/Documents/Code/v2d-research/work/13/t2"
CACHE = f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_t2feats_{os.environ.get('C_T2_AXES', 'stored')}.json"
FIRST7 = {"cane", "baseball_bat", "squeegee", "iron", "spray_bottle", "big_red_bowl", "light_blue_book"}
EVEN = {"kurt", "skew_se1"}

cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
names = sorted(f[:-4] for f in os.listdir(D2) if f.endswith(".npz"))
REF = np.column_stack([[0, 1, 0], [1, 0, 0], [0, 0, 1]]).astype(float)   # role order min,mid,max = stored y,x,z
for n in names:
    if n in cache:
        continue
    z = np.load(f"{D2}/{n}.npz")
    S = feats(z["V"], z["F"], ref=REF, hull=True)
    if AXES != "stored":
        for k, v in S.items():
            if not k.startswith("_") and k not in EVEN:
                v[0] = -v[0]        # det fix flipped E[:,0] to -stored y; restore stats along +stored y
    cache[n] = S
    json.dump(cache, open(CACHE, "w"))
    print("feats", n, np.round(S["skew"], 3), "sd_mm", np.round(S["_sd_mm"], 1), "dev", np.round(S["_axis_dev_deg"], 2), flush=True)

T3 = B.R; O3 = B.OBJ
ODD = B.ODD


def arr(R, objs, s):
    return np.array([R[o][s] for o in objs])


ratio = {n: cache[n]["_sd_mm"][0] / cache[n]["_sd_mm"][1] for n in names}
degen = {n for n in names if ratio[n] > 0.91}
zdegen = {n for n in names if cache[n]["_sd_mm"][1] / cache[n]["_sd_mm"][2] > 0.91}
print("\nTrack 2 scans:", len(names), "| roll-degenerate (min/mid sd > 0.91):", sorted(degen), "| z-degenerate:", sorted(zdegen))
for n in names:
    print(f"  {n:20s} sd(min,mid,max) {np.round(cache[n]['_sd_mm'], 1)} skew {np.round(cache[n]['skew'], 3)} dev {np.round(cache[n]['_axis_dev_deg'], 2)}"
          f"{' FIRST7' if n in FIRST7 else ''}{' DEGEN' if n in degen else ''}")

sets = {"T2_all_nondeg": [n for n in names if n not in degen], "T2_fresh22_nondeg": [n for n in names if n not in degen and n not in FIRST7]}
zsets = {"T2_all": [n for n in names if n not in zdegen], "T2_fresh22": [n for n in names if n not in zdegen and n not in FIRST7]}
print("\nSingle statistics, #positive along stored direction (min / mid / max)  [Track 3 10 scans | T2 non-degenerate sets]")
for s in ODD:
    a3 = arr(T3, O3, s); line = f"  {s:14s} T3 {int((a3[:, 0] > 0).sum()):2d} {int((a3[:, 1] > 0).sum()):2d} {int((a3[:, 2] > 0).sum()):2d}/10"
    for k, objs in sets.items():
        a = arr(cache, objs, s); zz = arr(cache, zsets[k.replace('_nondeg', '')], s)
        line += f" | {k} {int((a[:, 0] > 0).sum())}/{len(objs)} {int((a[:, 1] > 0).sum())}/{len(objs)} {int((zz[:, 2] > 0).sum())}/{len(zz)}"
    print(line)


def run_fams(R, objs):
    D = np.array([[R[o][s] for o in objs] for s in ODD])
    B.SE = np.array([R[o]["skew_se1"] for o in objs]); B.KU = np.array([R[o]["kurt"] for o in objs]); B.NO = len(objs)
    ok2, n2 = B.fam_F2(D); okb, nb = B.fam_F2b(D)
    return ok2, n2, okb, nb


ok2_3, n2_3, okb_3, nb_3 = run_fams(T3, O3)
fit2 = [k for k in range(len(n2_3)) if ok2_3[k].all()]; fitb = [k for k in range(len(nb_3)) if okb_3[k].all()]
print(f"\nStage B survivors re-derived on Track 3: F2 {len(fit2)}, F2b {len(fitb)}")
from math import comb
def binom_tail(k, n): return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
for k, objs in sets.items():
    ok2, n2, okb, nb = run_fams(cache, objs)
    print(f"\n{k} (n={len(objs)}):")
    for i in fit2:
        c = int(ok2[i].sum()); print(f"  {str(n2[i]):45s} {c}/{len(objs)}  P(>=|random)={binom_tail(c, len(objs)):.3f}")
    for i in fitb:
        c = int(okb[i].sum()); print(f"  {str(nb[i]):45s} {c}/{len(objs)}  P(>=|random)={binom_tail(c, len(objs)):.3f}")
    # textbook cascade: top-2 |skew| axes by positive skew (F2b rank skew, sign skew, p=+1)
    j = nb.index(("F2b", "skew", "skew", 1)); c = int(okb[j].sum())
    print(f"  textbook cascade (|skew| top-2 by +skew)      {c}/{len(objs)}  P={binom_tail(c, len(objs)):.3f}")
    sk = arr(cache, objs, "skew"); c = int((sk[:, 1] > 0).sum())
    print(f"  H1 mid-axis skew>0                            {c}/{len(objs)}  P={binom_tail(c, len(objs)):.3f}")
    c = int((sk[:, 0] > 0).sum()); print(f"  min-axis skew>0                               {c}/{len(objs)}  P={binom_tail(c, len(objs)):.3f}")
for k, objs in zsets.items():
    sk = arr(cache, objs, "skew"); c = int((sk[:, 2] > 0).sum())
    print(f"H3 z skew>0 on {k} (n={len(objs)}): {c}/{len(objs)}  P={binom_tail(c, len(objs)):.4f}; min |skew_z| {np.min(np.abs(sk[:, 2])):.4f}")
