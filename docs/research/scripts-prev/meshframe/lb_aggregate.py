"""Leaderboard-level delta from a spoon frame error: eval has 7 spoon-in-slot-1 episodes and
3 spoon-alone (slot 0) episodes out of 20; pose metrics are episode means."""
import pandas as pd, os
HERE = os.path.dirname(os.path.abspath(__file__))
s = pd.read_csv(os.path.join(HERE, "score_impact_summary.csv"))
keys = ["AUC", "SPSR", "MPSR", "RPE", "MPPE"]
perts = ["flip180_z", "flip180_x", "flip180_y", "rot90_z", "rot5_x", "rot5_z", "rot10_x", "rot10_z", "rot20_x", "rot20_z",
         "off0.5cm_z", "off1.0cm_z", "off2.0cm_z", "off1.0cm_x", "off2.0cm_y", "flip180_z+off1cm_z", "rot5_x+off1cm_z"]
out = []
for nz in s.noise.unique():
    s1 = s[(s.setting == "slot1") & (s.noise == nz)].set_index("pert")[keys]
    for hosts in ("all", "moving(maxrot>30deg)"):
        s0 = s[(s.setting == "slot0") & (s.noise == nz) & (s.hosts == hosts)].set_index("pert")[keys]
        d1 = s1 - s1.loc["none"]; d0 = s0 - s0.loc["none"]
        lb = (7 * d1 + 3 * d0) / 20
        lb = lb.loc[perts]; lb.insert(0, "noise", nz); lb.insert(1, "slot0_hosts", hosts)
        out.append(lb.reset_index())
df = pd.concat(out)
pd.set_option("display.width", 200)
print(df.round(3).to_string(index=False))
df.to_csv(os.path.join(HERE, "lb_aggregate.csv"), index=False)
