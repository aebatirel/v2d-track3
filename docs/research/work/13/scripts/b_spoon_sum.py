"""Summarise b_spoon MC: P(frame A) per rule and mode; skew_x sign drivers."""
import json, glob, collections, numpy as np
rows = collections.defaultdict(list)
for f in sorted(glob.glob("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_*.jsonl")):
    mode = f.split("b_spoon_")[1].rsplit("_", 1)[0]
    rows[mode] += [json.loads(l) for l in open(f)]
for mode, R in rows.items():
    sk = np.array([r["S"]["skew"] for r in R]); se = np.array([r["S"]["skew_se1"] for r in R])
    dev = np.array([r["dev"] for r in R])
    print(f"== {mode}: N={len(R)}  skew_z>0 {np.mean(sk[:,2]>0):.3f} (min {sk[:,2].min():+.3f}); axes dev max {dev.max():.1f} deg; "
          f"sd_x/sd_y {np.median([r['sd_mm'][0]/r['sd_mm'][1] for r in R]):.2f}")
    for i, a in enumerate("xyz"):
        print(f"   skew_{a}: mean {sk[:,i].mean():+.4f} sd {sk[:,i].std():.4f} [{np.percentile(sk[:,i],5):+.4f}, {np.percentile(sk[:,i],95):+.4f}]  "
              f"P(>0) {np.mean(sk[:,i]>0):.3f}  median |skew|/SE(n=1e5) {np.median(np.abs(sk[:,i])/(se[:,i]/np.sqrt(1e5))):.1f}")
    keys = [k for k in R[0]["R"] if k not in ("F3_shareA", "F3_top5")]
    print("   P(frame A = x to convex back / y to M1) per rule  [zflip share]:")
    for k in keys:
        v = [r["R"][k] for r in R]
        print(f"     {k:28s} P(A)={np.mean([x.startswith('A') for x in v]):.3f}  zflip={np.mean(['zflip' in x for x in v]):.3f}")
    print(f"     F3 hybrids (154, tau = geometric mid): mean share A {np.mean([r['R']['F3_shareA'] for r in R]):.3f}; "
          f"top-5 widest P(A): " + " ".join(f"{np.mean([r['R']['F3_top5'][j].startswith('A') for r in R]):.2f}" for j in range(5)))
    # drivers of skew_x
    X = np.array([[r["p"].get("ratio", np.nan), r["p"]["body"]["Db"]*1e3, r["p"]["body"]["handle_off_x"]*1e3, r["p"]["body"]["tb"]*1e3,
                   r["p"]["body"]["th"]*1e3] for r in R])
    for j, nm in enumerate(["th/2w", "Db mm", "handle_off_x mm(+=toward convex)", "tb mm", "th mm"]):
        c = np.corrcoef(X[:, j], sk[:, 0])[0, 1]
        q = np.quantile(X[:, j], [0, 1/3, 2/3, 1])
        bins = [np.mean(sk[(X[:, j] >= q[b]) & (X[:, j] <= q[b+1]), 0] > 0) for b in range(3)]
        print(f"   skew_x vs {nm:34s} corr {c:+.2f}; P(skew_x>0) by tercile {np.round(bins,2)} (edges {np.round(q,1)})")
