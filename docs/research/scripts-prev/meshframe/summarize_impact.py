import pandas as pd, numpy as np, os
HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(HERE, "score_impact_rows.csv"))
keys = ["AUC", "SPSR", "MPSR", "RPE", "MPPE", "spoon_pos_cm", "spoon_rot_deg"]
out = []
for (setting, nz), g in df.groupby(["setting", "noise"], sort=False):
    subsets = {"all": g}
    if setting == "slot0":
        subsets["moving(maxrot>30deg)"] = g[g.host_maxrot_deg > 30]
    for sname, gg in subsets.items():
        n = gg.ep.nunique()
        base = gg[gg.pert == "none"].set_index("ep")[keys]
        tab = gg.groupby("pert", sort=False)[keys].mean()
        print(f"\n### setting={setting} noise={nz} hosts={sname} (n={n})")
        print(tab.round(3).to_string())
        t2 = tab.copy(); t2.insert(0, "setting", setting); t2.insert(1, "noise", nz); t2.insert(2, "hosts", sname); t2.insert(3, "n", n)
        out.append(t2.reset_index())
pd.concat(out).to_csv(os.path.join(HERE, "score_impact_summary.csv"), index=False)
