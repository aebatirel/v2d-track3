import json, numpy as np
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
d = json.load(open(f"{W}/c4_gravity.json"))
rows = [(int(e), r) for e, v in d.items() for r in v["rows"]]
for lab, sel in (("all", rows), ("t==0", [x for x in rows if x[1]["t"] == 0]), ("t>=50", [x for x in rows if x[1]["t"] >= 50])):
    t = np.array([r["tilt"] for _, r in sel]); z = np.array([r["ztab"] for _, r in sel])
    print(f"{lab}: n={len(t)} tilt median {np.median(t):.3f} p90 {np.percentile(t, 90):.3f} max {t.max():.2f} | z median {np.median(z):.4f} p10-p90 {np.percentile(z, 10):.4f}-{np.percentile(z, 90):.4f}")
a5 = json.load(open(f"{W}/a5_stereo_table.json"))
print(type(a5), list(a5.keys())[:10] if isinstance(a5, dict) else len(a5))
