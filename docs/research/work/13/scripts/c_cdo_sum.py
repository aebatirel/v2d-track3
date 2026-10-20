"""Summarise out/c_cdo_*_m{1,0}.jsonl: CD-O (cm) and R1-frame stability per reconstruction option."""
import json, glob, numpy as np
for tm in (1, 0):
    R = [json.loads(l) for f in sorted(glob.glob(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_cdo_*_m{tm}.jsonl")) for l in open(f)]
    if not R: continue
    print(f"\n=== truth {'WITH' if tm else 'WITHOUT'} markers, N={len(R)} ===")
    print(f"{'option':24s} {'CD-O mean':>9s} {'sd':>6s} {'p90':>6s} {'-floor':>7s} | {'origin mm med/p90':>17s} | {'x-axis deg med/p90':>18s} | {'z deg med':>9s} | sign agree x / y / z | area ratio")
    for k in R[0]["opts"]:
        cd = np.array([r["opts"][k]["cdo_cm"] for r in R]); fl = np.array([r["opts"]["F_retess_floor"]["cdo_cm"] for r in R])
        dc = np.array([r["opts"][k]["dc_mm"] for r in R]); ang = np.array([r["opts"][k]["ang_deg"] for r in R])
        ss = np.array([r["opts"][k]["same_sign"] for r in R]).mean(0); ar = np.array([r["opts"][k]["area_ratio"] for r in R])
        print(f"{k:24s} {cd.mean():9.3f} {cd.std():6.3f} {np.percentile(cd,90):6.3f} {np.mean(cd-fl):+7.3f} | {np.median(dc):7.1f} / {np.percentile(dc,90):6.1f} | "
              f"{np.median(ang[:,0]):7.2f} / {np.percentile(ang[:,0],90):6.2f} | {np.median(ang[:,2]):9.2f} | {ss[0]:.2f} / {ss[1]:.2f} / {ss[2]:.2f} | {np.median(ar):.2f}")
