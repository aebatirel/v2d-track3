"""GRASP-style window optimiser for tools/physics_solve/solve.py --method grasp (2026-11-01).

GRASP (Liu, Wang, Bao, Yang, "Gradient-Guided Sampling for Contact-Rich Physics-Based Motion Retargeting", Harvard 2026,
https://computationalrobotics.seas.harvard.edu/GRASP, code github.com/ComputationalRobotics/GRASP_code @ 992c737, MIT):
per receding-horizon window, tempered sequential Monte Carlo from an AR(1) prior over control knots (centred on the
previous window's plan) to p0(x) exp(-beta J(x)). Every stage resamples on an adaptive ESS schedule, fits a local quadratic
model of the cost to the ARCHIVE of every rollout evaluated so far in the window (accepted or not), and moves particles
with Langevin (MALA) proposals along the model's gradient, preconditioned by the prior covariance; the Metropolis-Hastings
test uses the TRUE simulator cost, so the model only steers proposals and never decides acceptance.

Provenance. Adapted (re-written in numpy, same maths) from GRASP's own MIT-licensed optimiser files, which are NOT among
the SPIDER-derived (CC BY-NC 4.0) files listed in GRASP's THIRD_PARTY_NOTICES.md:
  grasp/optim/surrogate.py  make_dct_basis, fit_quadratic_surrogate (trust region, winsorising, Gaussian window, ridge
                            on everything but the intercept)            -> dct_basis, fit_surrogate (+ a 'diag' option)
  grasp/optim/sampler.py    _ess_ratio_from_log_weights, _next_temperature, _systematic_resample_np, the surrogate_mala
                            proposal and its MH ratio, the adaptive step  -> ess_ratio, next_temperature, resample, run
  grasp/optim/prior_ar1.py  WindowAR1Prior (warm-start bias, conditioning on the committed knot)    -> the w <-> x maps
  grasp/mpc/grasp_mpc.py    initial particle 0 = the prior's conditional mean (the warm start); carrying samples to the
                            next window (its light-window library, here a shifted share of the final population)
No SPIDER-derived file (grasp/sim/*, grasp/config.py, grasp/utils/*, grasp/pipeline/* listed there) was used or copied.
MIT License, Copyright (c) 2026 Yang Liu, Tong Wang, Yiming Bao, Heng Yang. Permission is hereby granted, free of charge,
to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject
to the following conditions: The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Coordinates. x (nk, D): knot deviations from the window's warm-start plan on the active action dims (the plan is the
previous window's unexecuted suffix, as in solve.py's annealed sampler and GRASP's --warm-start-plan). The prior is the
AR(1) chain x_0 = D_0 w_0, x_k = rho x_(k-1) + D_k w_k with w ~ N(0, I): GRASP's window prior conditioned on the committed
knot with the warm-start bias (deviation 0 at the committed knot). Sampling runs in whitened w, where GRASP's
prior_full-preconditioned MALA is plain MALA with an identity metric (the step is in units of the prior width, GRASP's
step_size / prior sigma). The cost is solve.py's own J (the kit's ADD on sphere points + the offset regulariser, mean over
the robust copies whose target noise is FIXED for the window, so J is a deterministic function and the MH test is exact).

Differences from GRASP, forced by the CPU budget or by solve.py (labelled in the pre-registration):
  - budget: a window gets exactly as many rollout batches as the annealed sampler (1 initial + MCMC moves); tempering
    stops when the budget is spent even if the temperature has not reached 1 (GRASP runs to 1, max 64 stages);
  - selection: the lowest-cost plan evaluated in the window (the same rule as the annealed sampler; GRASP takes the
    population argmin, optionally re-simulated);
  - beta is relative: beta = BETA_REL / J(warm start) (GRASP's tau is set for its own reward scale);
  - quad='diag' fits a diagonal quadratic in the DCT basis when the archive is far smaller than the full model
    (GRASP: full quadratic, 2,000 particles);
  - no joint start, no pin of the first knot (solve.py commits whole knots; frame 0 stays the reset pose).
"""
from __future__ import annotations

import numpy as np


# ------------------------------------------------------------------------------------------- GRASP sampler helpers
def ess_ratio(log_w):
    s = np.asarray(log_w, np.float64); s = s - s.max(); w = np.exp(s); w = w / w.sum()
    return float(1.0 / np.sum(w * w) / w.size)


def next_temperature(lam, loglik, target_ess, steps=48):
    """Largest lam' <= 1 whose incremental weights exp((lam' - lam) loglik) keep ESS >= target (bisection)."""
    if lam >= 1.0:
        return 1.0
    if ess_ratio((1.0 - lam) * loglik) >= target_ess:
        return 1.0
    lo, hi = float(lam), 1.0
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        if ess_ratio((mid - lam) * loglik) < target_ess:
            hi = mid
        else:
            lo = mid
    return float(lo)


def resample(rng, weights):
    n = weights.shape[0]; pos = rng.uniform(0.0, 1.0 / n) + np.arange(n) / n
    c = np.cumsum(weights); c[-1] = 1.0
    return np.searchsorted(c, pos, side='right')


def dct_basis(horizon, dim, rank):
    """(H*dim, rank*dim) orthonormal DCT-II basis over knots, per channel; row layout x.reshape(H*dim) (knot-major)."""
    t = np.arange(horizon, dtype=np.float64); cols = []
    for f in range(rank):
        c = np.cos(np.pi * (t + 0.5) * f / float(horizon)) * np.sqrt((1.0 if f == 0 else 2.0) / float(horizon))
        cols.append(c)
    return np.kron(np.stack(cols, 1), np.eye(dim))


def fit_surrogate(X, J, center, scale, basis, ridge=1e-3, window=3.0, quad='diag'):
    """Locally weighted ridge quadratic J ~ c + b.y + y.A.y/2, y = basis^T (x - center) / scale (GRASP surrogate.py).
    Returns (b, A, weighted R^2) in basis coordinates; A is (r, r) (full) or a diagonal (r, r)."""
    X = np.asarray(X, np.float64); J = np.asarray(J, np.float64); scale = np.maximum(scale, 1e-8)
    z = (X - center[None]) / scale[None]; nd2 = np.sum(z * z, 1) / z.shape[1]
    keep = np.isfinite(J) & np.all(np.isfinite(z), 1); trusted = keep & (nd2 <= (3.0 * window) ** 2)
    if trusted.any():
        keep = trusted
    z, J = z[keep], J[keep]
    med, up = np.quantile(J, [0.5, 0.9]); cap = med + 10.0 * max(up - med, 1e-9); inl = J <= cap
    if inl.sum() >= max(8, z.shape[1]):
        z, J = z[inl], J[inl]
    n = z.shape[0]
    w = np.exp(-np.sum(z * z, 1) / (2.0 * window ** 2 * z.shape[1]))
    y = z @ basis; r = y.shape[1]
    if quad == 'full':
        iu, ju = np.triu_indices(r); F = np.concatenate([np.ones((n, 1)), y, y[:, iu] * y[:, ju]], 1)
    else:
        F = np.concatenate([np.ones((n, 1)), y, y * y], 1)
    sw = np.sqrt(w)[:, None]; Dm = sw * F; tgt = sw[:, 0] * J; G = Dm.T @ Dm
    idx = np.arange(1, G.shape[0]); G[idx, idx] += ridge * max(1, n)
    if np.any(w > 0):
        th = np.linalg.solve(G, Dm.T @ tgt)
    else:
        th = np.zeros(F.shape[1]); th[0] = float(np.median(J))
    pred = F @ th; wm = np.sum(w * J) / max(np.sum(w), 1e-12)
    r2 = 1.0 - np.sum(w * (J - pred) ** 2) / max(np.sum(w * (J - wm) ** 2), 1e-12)
    b = th[1:1 + r]
    if quad == 'full':
        A = np.zeros((r, r)); A[iu, ju] = th[1 + r:]; A = A + A.T
    else:
        A = np.diag(2.0 * th[1 + r:])
    return b, A, float(r2)


# ------------------------------------------------------------------------------------------- AR(1) prior maps
class AR1:
    """x_0 = D_0 w_0, x_k = rho x_(k-1) + D_k w_k (per channel); D (nk, dim) > 0."""

    def __init__(self, D, rho):
        self.D = np.asarray(D, np.float64); self.rho = float(rho); self.nk = self.D.shape[0]

    def x_of_w(self, W):
        X = np.empty_like(W); prev = np.zeros_like(W[:, 0])
        for k in range(self.nk):
            prev = self.rho * prev + self.D[k] * W[:, k]; X[:, k] = prev
        return X

    def w_of_x(self, X):
        prev = np.concatenate([np.zeros_like(X[:, :1]), X[:, :-1]], 1)
        return (X - self.rho * prev) / self.D[None]

    def lt(self, V):
        """L^T v for the map x = L w (gradient pull-back: grad_w = L^T grad_x)."""
        Z = np.empty_like(V); nxt = np.zeros_like(V[:, 0])
        for k in range(self.nk - 1, -1, -1):
            nxt = V[:, k] + self.rho * nxt; Z[:, k] = nxt
        return Z * self.D[None]


# ------------------------------------------------------------------------------------------- one window
def run(evaluate, D, rho, N, budget, rng, *, beta_rel=100.0, ess=0.9, moves=2, step=0.59, acc_target=0.05,
        acc_rate=3.0, step_min=0.1, rank=2, quad='diag', ridge=1e-3, window=3.0, carry=None, log=None):
    """GRASP window solve. evaluate(X (n, nk, dim) knot deviations) -> (J (n,), aux list per row): one rollout batch per
    call (n <= N). D: (nk, dim) AR(1) innovation widths. budget: rollout batches (calls). carry: optional (m, nk, dim)
    deviations of carried samples (the previous window's final population, shifted), used for init rows 1..m.
    Returns dict(best_x, best_J, best_aux, pop_x, hist, ...)."""
    nk, dim = D.shape; pr = AR1(D, rho)
    W = rng.standard_normal((N, nk, dim)); W[0] = 0.0                     # particle 0 = conditional mean = warm start
    if carry is not None and len(carry):
        m = min(len(carry), N - 1); W[1:1 + m] = pr.w_of_x(np.asarray(carry[:m], np.float64))
    X = pr.x_of_w(W); J, aux = evaluate(X); used = 1
    AX = [X.reshape(N, -1).copy()]; AJ = [J.copy()]
    i0 = int(np.argmin(J)); best = (float(J[i0]), X[i0].copy(), aux[i0])
    J0 = float(J[0]); beta = beta_rel / max(J0, 1e-9)
    basis = dct_basis(nk, dim, rank) if 0 < rank < nk else np.eye(nk * dim)
    lam = 0.0; s = float(step); s_lo = step * step_min; hist = []
    lp = lambda Wm: -0.5 * np.sum(Wm.reshape(len(Wm), -1) ** 2, 1)      # noqa: E731  log prior in w (up to a constant)
    while used < budget:
        ll = -beta * J; lam1 = next_temperature(lam, ll, ess); inc = (lam1 - lam) * ll
        e = ess_ratio(inc); wts = np.exp(inc - inc.max()); wts /= wts.sum()
        anc = resample(rng, wts); W, X, J = W[anc], X[anc], J[anc]; aux = [aux[i] for i in anc]
        PX = X.reshape(N, -1); center = PX.mean(0); scale = np.maximum(PX.std(0), 1e-3)
        b, A, r2 = fit_surrogate(np.concatenate(AX), np.concatenate(AJ), center, scale, basis, ridge, window, quad)

        def grad_w(Wm):                                                     # grad of log pi_lam1 under the surrogate
            Xm = pr.x_of_w(Wm).reshape(len(Wm), -1); y = ((Xm - center) / scale) @ basis
            gx = ((b[None] + y @ A) @ basis.T / scale).reshape(Wm.shape)
            return -Wm - lam1 * beta * pr.lt(gx)
        accs = []
        for mv in range(moves):
            if used >= budget:
                break
            g = grad_w(W); mf = W + 0.5 * s * s * g
            W2 = mf + s * rng.standard_normal(W.shape); X2 = pr.x_of_w(W2)
            J2, aux2 = evaluate(X2); used += 1
            AX.append(X2.reshape(N, -1).copy()); AJ.append(J2.copy())
            g2 = grad_w(W2); mr = W2 + 0.5 * s * s * g2
            lq_f = -np.sum((W2 - mf).reshape(N, -1) ** 2, 1) / (2 * s * s)
            lq_r = -np.sum((W - mr).reshape(N, -1) ** 2, 1) / (2 * s * s)
            ok = np.isfinite(J2)
            la = (lp(W2) - lam1 * beta * np.where(ok, J2, J)) - (lp(W) - lam1 * beta * J) + lq_r - lq_f
            acc = ok & (np.log(rng.uniform(size=N).clip(1e-38)) < la)
            W = np.where(acc[:, None, None], W2, W); X = np.where(acc[:, None, None], X2, X); J = np.where(acc, J2, J)
            aux = [aux2[i] if acc[i] else aux[i] for i in range(N)]; accs.append(float(acc.mean()))
            j2 = int(np.argmin(np.where(ok, J2, np.inf)))
            if ok[j2] and J2[j2] < best[0]:
                best = (float(J2[j2]), X2[j2].copy(), aux2[j2])
        acc_m = float(np.mean(accs)) if accs else float('nan')
        hist.append(dict(lam=round(lam1, 6), ess=round(e, 3), r2=round(r2, 3), step=round(s, 4), acc=round(acc_m, 3),
                         Jmin=round(float(J.min()), 5), Jmed=round(float(np.median(J)), 5), Jbest=round(best[0], 5)))
        if accs:
            s = float(np.clip(s * np.exp(acc_rate * (acc_m - acc_target)), s_lo, step))
        lam = lam1
    if log is not None:
        log(f'    grasp: beta {beta:.1f} J0 {J0:.5f} best {best[0]:.5f} stages {len(hist)} '
            + ' | '.join(f"lam {h['lam']:.3g} acc {h['acc']} R2 {h['r2']}" for h in hist))
    return dict(best_J=best[0], best_x=best[1], best_aux=best[2], pop_x=X, pop_J=J, J0=J0, beta=beta, hist=hist, used=used,
                archive=int(sum(len(a) for a in AJ)), lam=lam)
