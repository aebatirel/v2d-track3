"""Eval-set composed prior with noise-induced increase of the random failure rate r (Track 2: +0.10-0.17; CHORD App. C: +0.35-0.5)."""
import io, contextlib
import pandas as pd
with contextlib.redirect_stdout(io.StringIO()):
    import eval_prior as E
out = []
for label, dr in (("Track2 +0.10..0.17", (0.10, 0.17)), ("AppC +0.35..0.50", (0.35, 0.50))):
    for N in (1, 3):
        vals = [E.evalset("PERC_M", "lag30", "soft", s, min(1.0, r + d), N)
                for s in (E.S_LO, E.S_HI) for r in (0.20, 0.45) for d in dr]
        lo, hi = pd.DataFrame(vals).min().values, pd.DataFrame(vals).max().values
        out.append(f"PERC_M real speed lag30 N={N} {label}: AUC {lo[0]:.3f}-{hi[0]:.3f} SP-SR {lo[1]:.2f}-{hi[1]:.2f} MP-SR {lo[2]:.2f}-{hi[2]:.2f}")
print("\n".join(out)); open("eval_prior_noisy.txt", "w").write("\n".join(out) + "\n")
