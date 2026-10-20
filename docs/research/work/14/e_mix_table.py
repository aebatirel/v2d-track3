"""Mixture: E[m] = (1-q) good + q fail, fail = 0.5 never + 0.5 drop50, q = p**N (independent seeds,
failure visible in metrics_output so selection picks a non-failing seed when one exists)."""
import pandas as pd
df = pd.read_csv("e_mix.csv")
g = df.groupby(["ref", "pol"])[["AUC", "SPSR", "MPSR", "MPPE"]].mean()
print(f"{'ref':7s} {'p':>4s} {'N':>2s} {'q':>6s}  {'AUC':>6s} {'SP-SR':>6s} {'MP-SR':>6s} {'MPPE':>6s}")
for ref in ["GT", "PERC_A", "PERC_M", "PERC_B"]:
    good = g.loc[(ref, "good")]; fail = 0.5 * g.loc[(ref, "never")] + 0.5 * g.loc[(ref, "drop50")]
    for p in [0.0, 0.1, 0.2, 0.3, 0.45]:
        for N in [1, 3]:
            if p == 0 and N == 3:
                continue
            q = p ** N; m = (1 - q) * good + q * fail
            print(f"{ref:7s} {p:4.2f} {N:2d} {q:6.3f}  {m.AUC:6.3f} {m.SPSR:6.3f} {m.MPSR:6.3f} {m.MPPE:6.2f}")
    print()
