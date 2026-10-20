"""Stage C: statistics of s26 (room-registration transfer of the mocap camera heading). Leave-one-out style: for each
fitted public q, predict psi_q from every other fitted p and compare with q's own GT-silhouette fit."""
import json, sys, numpy as np
T = json.load(open(sys.argv[1]))["pairs"]; F = json.load(open(sys.argv[2])); GOOD = [int(x) for x in sys.argv[3].split(",")]
w = lambda a: (a + 180) % 360 - 180
u = lambda a: np.mod(np.asarray(a, float), 360.0)  # headings near 180: keep in [0,360)
print("fitted psi:", {e: round(F[str(e)]["psi"], 2) for e in GOOD})
res = []; out = {}
for q in GOOD:
    pr = list(u([T[f"p{q}|{p}"]["psi"] for p in GOOD if p != q]))
    inl = [T[f"p{q}|{p}"]["inl"] for p in GOOD if p != q]
    med = float(np.median(pr)); r = w(med - F[str(q)]["psi"]); res.append(r)
    out[f"p{q}"] = dict(pred_median=med, fit=F[str(q)]["psi"], resid=float(r), preds=[round(x, 2) for x in pr], inl=inl)
    print(f"public {q:2d}: fit {F[str(q)]['psi']:7.2f} pred(median over others) {med:7.2f} resid {r:+5.2f} preds {np.round(pr,1)} inl {inl}")
res = np.array(res); print(f"LOO resid: mean {res.mean():+.2f} sd {res.std(ddof=1):.2f} rms {np.sqrt((res**2).mean()):.2f} max {np.abs(res).max():.2f}")
allpair = [w(T[f"p{q}|{p}"]["psi"] - F[str(q)]["psi"]) for q in GOOD for p in GOOD if p != q]
print(f"all ordered pairs: rms {np.sqrt(np.mean(np.square(allpair))):.2f}  (n {len(allpair)})")
raw = u([F[str(e)]["psi"] for e in GOOD]); print(f"population prior (no registration): mean {raw.mean():.2f} sd {raw.std(ddof=1):.2f}")
for tag, eps in (("p", [0, 11, 12, 13, 18, 21, 22, 23, 26, 31, 39, 41]), ("e", [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38])):
    for q in eps:
        if tag == "p" and q in GOOD: continue
        pr = list(u([T[f"{tag}{q}|{p}"]["psi"] for p in GOOD if f"{tag}{q}|{p}" in T]))
        inl = [T[f"{tag}{q}|{p}"]["inl"] for p in GOOD if f"{tag}{q}|{p}" in T]
        th = [T[f"{tag}{q}|{p}"]["th"] for p in GOOD if f"{tag}{q}|{p}" in T]
        out[f"{tag}{q}"] = dict(pred_median=float(np.median(pr)), spread=float(np.std(pr)), preds=[round(x, 2) for x in pr], inl=inl, pitch=float(np.median(th)))
        print(f"{'public' if tag=='p' else 'eval  '} {q:2d}: W=psi {np.median(pr):7.2f}  spread {np.std(pr):4.2f}  pitch {np.median(th):5.1f}  min inl {min(inl)}")
json.dump(out, open(sys.argv[1].replace(".json", "_stats.json"), "w"), indent=1)
