"""Exact numbers for the Stage C verdict rows: continuous term x failure probability range."""
import pandas as pd
g = pd.read_csv("e_mix.csv").groupby(["ref", "pol"])[["AUC", "SPSR", "MPSR"]].mean()
def mix(ref, cont, p, N):
    q = p ** N; fail = 0.5 * g.loc[(ref, "never")] + 0.5 * g.loc[(ref, "drop50")]
    return (1 - q) * g.loc[(ref, cont)] + q * fail
rows = [("GT realspeed", "GT", ["mid", "lag30"], [0.20, 0.45]),
        ("GT halfspeed-equiv", "GT", ["good"], [0.07, 0.25]),
        ("PERC_M realspeed", "PERC_M", ["mid", "lag30"], [0.30, 0.62]),
        ("PERC_A realspeed", "PERC_A", ["mid", "lag30"], [0.25, 0.50])]
for name, ref, conts, ps in rows:
    for N in (1, 3):
        vals = [mix(ref, c, p, N) for c in conts for p in ps]
        lo = pd.concat(vals, axis=1).min(axis=1); hi = pd.concat(vals, axis=1).max(axis=1)
        print(f"{name:20s} N={N} " + "  ".join(f"{k} {lo[k]:.3f}-{hi[k]:.3f}" for k in lo.index))
