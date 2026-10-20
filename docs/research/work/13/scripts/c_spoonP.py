"""Stage C: P(spoon frame B) under the fitted noisy 'mid-axis by positive skew' model, mechanism (a): exact axes, skew
estimated from n points -> P(B) = Phi(-skew_y * sqrt(n) / se1_y), skew_y along +y_P (M1 side) from Stage B spoon MC records;
averaged over the joint posterior of n (out/c_noisy_post.npy). Also P(z correct) = Phi(skew_z sqrt(n)/se1_z)."""
import json, glob, numpy as np
from scipy.stats import norm
ns, post = np.load("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_noisy_post.npy")
for mode in ("round", "oval", "nomark"):
    S = [json.loads(l)["S"] for f in glob.glob(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_spoon_{mode}_*.jsonl") for l in open(f)]
    sy = np.array([s["skew"][1] for s in S]); se = np.array([s["skew_se1"][1] for s in S])
    sz = np.array([s["skew"][2] for s in S]); sez = np.array([s["skew_se1"][2] for s in S])
    PB = np.array([norm.cdf(-sy * np.sqrt(n) / se).mean() for n in ns]); Pz = np.array([norm.cdf(sz * np.sqrt(n) / sez).mean() for n in ns])
    at = lambda arr, n: arr[np.argmin(np.abs(ns - n))]
    print(f"{mode:7s} N={len(S)} skew_y {sy.mean():+.4f}+-{sy.std():.4f} se1_y {se.mean():.2f} | P(B) post-avg {float((PB*post).sum()):.3f}"
          f"  at n=1e3 {at(PB,1e3):.3f} 3e3 {at(PB,3e3):.3f} 1e4 {at(PB,1e4):.3f} 3e4 {at(PB,3e4):.3f} | P(z ok) post-avg {float((Pz*post).sum()):.4f}")
