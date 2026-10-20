"""Summarise out/c2_budget_7.jsonl (native-budget spoon template vs high-res)."""
import json, numpy as np
R = [json.loads(l) for l in open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c2_budget_7.jsonl")]
print("N", len(R), "faces lo min/max", min(r["nF_lo"] for r in R), max(r["nF_lo"] for r in R),
      "verts lo max", max(r["nV_lo"] for r in R), "faces hi med", int(np.median([r["nF_hi"] for r in R])))
for k in R[0]["cdo"]:
    v = np.array([r["cdo"][k] for r in R]); print(f"CD-O {k:20s} mean {v.mean():.4f} sd {v.std():.4f} p90 {np.percentile(v, 90):.4f}")
for k in R[0]["frame"]:
    dc = np.array([r["frame"][k]["dc_mm"] for r in R]); ang = np.array([r["frame"][k]["ang_deg"] for r in R])
    ss = np.array([r["frame"][k]["same_sign"] for r in R]); sk = np.array([r["frame"][k]["sk"] for r in R])
    print(f"frame {k:20s} origin mm med {np.median(dc):.2f} max {dc.max():.2f} | axis deg max x/y/z {ang.max(0).round(2).tolist()}"
          f" | same sign x/y/z {ss.mean(0).round(2).tolist()} | min |skew| x/y/z {np.abs(sk).min(0).round(3).tolist()}")
skt = np.array([r["sk_true"] for r in R]); print("truth skew y mean/min/max", skt[:, 1].mean().round(4), skt[:, 1].min(), skt[:, 1].max())
