"""[E] Model average of the spoon roll over rule hypotheses, weighted by their likelihood on the 10 published rolls.
Classes (equal prior 1/3 each, uniform within class): RAND (roll unrelated to geometry, lik 2^-10);
DET = parameter-free cascades F1/F2/F2b/F4 (lik 1 if fits 10/10 else 0); NOISY = sign of p*s(a) on n samples
(112 models, n log-uniform on the b_noisy grid). Spoon P(A|rule) from the b_spoon MC (exact signs)."""
import sys, json, glob, collections, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import b_search as B, b_noisy as BN
fams = [B.fam_F1, B.fam_F2, B.fam_F2b, B.fam_F4]
K_det = sum(len(f(B.D)[1]) for f in fams)
fit = [n for f in fams for k, n in zip(range(10**6), f(B.D)[1]) if f(B.D)[0][k].all()]
L = BN.best(BN.D)                                   # (2 axes, 2 pol, S, nN) log-lik
marg = np.exp(L).mean(-1)                           # average over n grid
w_rand, w_det, w_noisy = 2.0**-10, len(fit) / K_det, marg.mean()
Z = w_rand + w_det + w_noisy
print(f"class evidence (avg lik): RAND {w_rand:.2e}  DET {w_det:.2e} ({len(fit)}/{K_det} fit)  NOISY {w_noisy:.2e}")
print(f"posterior class weights: RAND {w_rand/Z:.2f}  DET {w_det/Z:.2f}  NOISY {w_noisy/Z:.2f}")
rows = collections.defaultdict(list)
for f in glob.glob("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_*.jsonl"):
    rows[f.split("b_spoon_")[1].rsplit("_", 1)[0]] += [json.loads(l) for l in open(f)]
for mode, R in sorted(rows.items()):
    # DET: average P(A) over fitting rules present in the MC record
    pa_det = np.mean([np.mean([r["R"][k].startswith("A") for r in R]) for k in R[0]["R"] if k.startswith("F2")])
    # NOISY: weight each (axis,pol,stat) by marginal lik; spoon sign from saved stats where available
    num = den = 0.0; miss = 0.0
    for a in (0, 1):
        for p in (0, 1):
            for si, s in enumerate(BN.stats):
                w = marg[a, p, si]
                if s not in R[0]["S"]:
                    miss += w; continue
                pol = 1 if p == 0 else -1
                # rule fixes axis a: keep if pol*S>0; frame A iff resulting x = +x_P (z kept: skew_z>0 in all samples)
                pa = np.mean([(pol * r["S"][s][a] > 0) for r in R])
                num += w * pa; den += w
    pa_noisy = num / den
    pa = (w_rand * 0.5 + w_det * pa_det + w_noisy * pa_noisy) / Z
    print(f"{mode:7s}: P(A|DET) {pa_det:.2f}  P(A|NOISY) {pa_noisy:.2f} (weight w/o saved stat {miss/(miss+den):.2f})  "
          f"=> model-averaged P(A) {pa:.2f}, P(B) {1-pa:.2f}")
