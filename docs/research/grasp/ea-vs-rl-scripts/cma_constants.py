"""CMA-ES default learning rates (Hansen 2016 tutorial, as implemented in tools/grasp_evolve.py) and the implied
adaptation time constants, for the genome sizes and population sizes we use or propose (2026-10-24)."""
import numpy as np
print('| n (genome) | lambda | mu_eff | c1 | c_mu | covariance time ~1/(c1+c_mu) [generations] | step-size path 1/c_s [generations] |')
print('|---|---|---|---|---|---|---|')
for n in (6, 8, 11, 14, 28, 56):
    for lam in (8, 16, 64, 256):
        mu = lam // 2; w = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1)); w /= w.sum(); mueff = 1 / (w ** 2).sum()
        c1 = 2 / ((n + 1.3) ** 2 + mueff); cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((n + 2) ** 2 + mueff)); cs = (mueff + 2) / (n + mueff + 5)
        print(f'| {n} | {lam} | {mueff:.1f} | {c1:.4f} | {cmu:.4f} | {1 / (c1 + cmu):.1f} | {1 / cs:.1f} |')
