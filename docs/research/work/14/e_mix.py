"""Stage C: per-episode scores for 'policy tracks' vs 'policy fails discretely', on clean (GT) and
perception-noisy references, scored vs GT with the kit's Track 3 metrics. Output feeds a mixture
model E[score] = (1-q) * good + q * fail with q = p**N for best-of-N trained seeds. Research only:
public GT used for analysis, nothing here is an inference path."""
import sys, time
import numpy as np
import pandas as pd
from common14 import metrics
from track_err import (EPS, compose, PERC_A, PERC_M, PERC_B, POL_GOOD, POL_MID,
                       never_moves, freeze_mid, lowpass)

REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
REFS = {"GT": None, "PERC_A": PERC_A, "PERC_M": PERC_M, "PERC_B": PERC_B}
POLS = {
    "good": POL_GOOD,
    "mid": POL_MID,
    "lag30": lowpass(0.30),                     # saturated soft wrist, real speed [H]
    "never": compose(POL_GOOD, never_moves()),  # failed grasp of most-moving object
    "drop50": compose(POL_GOOD, freeze_mid(0.5)),
}
rows = []
t0 = time.time()
for e in EPS:
    for rn, rf in REFS.items():
        for pn, pf in POLS.items():
            reps = 1 if (rf is None and pn in ("lag30",)) else REPS
            for r in range(reps):
                rng = np.random.default_rng(1000 * e["ep"] + r)
                ref = e["p"] if rf is None else rf(e["p"], rng, e)
                ach = pf(ref, rng, e)
                m = metrics(ach, e["p"], e["names"])
                rows.append(dict(ep=e["ep"], ref=rn, pol=pn, rep=r, nobj=len(e["names"]), **m))
    print(f"ep {e['ep']} done {time.time() - t0:.0f}s", flush=True)
df = pd.DataFrame(rows)
df.to_csv("e_mix.csv", index=False)
print(df.groupby(["ref", "pol"])[["AUC", "SPSR", "MPSR", "RPE", "MPPE"]].mean().round(3).to_string())
