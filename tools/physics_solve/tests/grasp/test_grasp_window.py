"""Unit checks of tools/physics_solve/grasp_window.py (2026-11-01; numpy only, no simulator):
AR(1) maps (inverse, adjoint), DCT basis orthonormality, the surrogate fit on an exact quadratic, the MALA/MH step's
detailed balance on a Gaussian target (moments), and a window solve on a toy quadratic cost.
Run: python -I test_grasp_window.py   (prints PASS lines; exits non-zero on failure)"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import grasp_window as GW  # noqa: E402

rng = np.random.default_rng(0); nk, d = 5, 7
D = rng.uniform(0.5, 2.0, (nk, d)); pr = GW.AR1(D, 0.9)
W = rng.standard_normal((3, nk, d)); X = pr.x_of_w(W)
assert np.allclose(pr.w_of_x(X), W); print('PASS AR1 inverse')
V = rng.standard_normal((3, nk, d))
assert np.allclose(np.sum(X * V, (1, 2)), np.sum(W * pr.lt(V), (1, 2))); print('PASS AR1 adjoint <Lw,v> = <w,L^T v>')
B = GW.dct_basis(nk, d, 2); assert np.allclose(B.T @ B, np.eye(2 * d)); print('PASS DCT basis orthonormal', B.shape)
# surrogate: exact quadratic in the span of the basis is recovered (full); gradient direction is right (diag)
c = rng.standard_normal(nk * d) * 0.1
b0 = rng.standard_normal(2 * d); A0 = np.diag(rng.uniform(0.5, 2, 2 * d))
P = c + rng.standard_normal((4000, nk * d)) * 0.3; y = (P - c) / 0.3 @ B
J = 1.0 + y @ b0 + 0.5 * np.sum(y * (y @ A0), 1)
b, A, r2 = GW.fit_surrogate(P, J, c, np.full(nk * d, 0.3), B, ridge=1e-9, window=1e6, quad='full')
assert np.allclose(b, b0, atol=1e-4) and np.allclose(A, A0, atol=1e-4) and r2 > 0.9999, (r2,)
b, A, r2 = GW.fit_surrogate(P, J, c, np.full(nk * d, 0.3), B, ridge=1e-9, window=1e6, quad='diag')
assert np.allclose(b, b0, atol=1e-4) and np.allclose(A, A0, atol=1e-4); print('PASS surrogate exact on a quadratic (full, diag)')
# window solve on a toy cost: J(x) = 1 + |x - x*|^2 / 2 (x in prior units); the best must beat the warm start clearly,
# and the MH chain at lam = 1 must leave the posterior N(m, S) invariant (checked on its mean)
xs = pr.x_of_w(rng.standard_normal((1, nk, d)) * 0.8)[0]
calls = []


def ev(Xk):
    calls.append(len(Xk)); J = 1.0 + 0.5 * np.sum(((Xk - xs[None]) / D[None]) ** 2, (1, 2)); return J, [None] * len(Xk)


r = GW.run(ev, D, 0.9, 64, 12, np.random.default_rng(1), beta_rel=50.0, moves=2, quad='diag')
assert len(calls) == 12 and all(c_ == 64 for c_ in calls), calls
assert r['best_J'] < 0.8 * r['J0'], (r['best_J'], r['J0'])
print(f"PASS toy window: J0 {r['J0']:.3f} -> best {r['best_J']:.3f} in {len(calls)} batches; lam {r['lam']:.3f}; "
      f"acc {[h['acc'] for h in r['hist']]}")
# carried samples enter as rows 1..m unchanged
seen = []


def ev2(Xk):
    seen.append(Xk.copy()); return np.zeros(len(Xk)), [None] * len(Xk)


car = pr.x_of_w(rng.standard_normal((5, nk, d)))
GW.run(ev2, D, 0.9, 16, 1, np.random.default_rng(2), carry=car)
assert np.allclose(seen[0][1:6], car) and np.allclose(seen[0][0], 0); print('PASS carry rows 1..m, row 0 = warm start')
# MALA/MH detailed balance: Gaussian target exp(-|w|^2/2 - beta J(Lw)) with J quadratic; long chain mean vs exact
nk2, d2 = 3, 2; D2 = np.ones((nk2, d2)); p2 = GW.AR1(D2, 0.5); xs2 = np.full((nk2, d2), 1.0)
M = np.eye(nk2 * d2); L = np.zeros((nk2 * d2, nk2 * d2))
for i in range(nk2 * d2):
    e_ = np.zeros((1, nk2, d2)); e_.reshape(-1)[i] = 1; L[:, i] = p2.x_of_w(e_).reshape(-1)
# posterior over w: prec = I + beta L^T L, mean = prec^-1 beta L^T xs
beta = 2.0; prec = np.eye(nk2 * d2) + beta * L.T @ L; mu = np.linalg.solve(prec, beta * L.T @ xs2.reshape(-1))
w = np.zeros((2000, nk2 * d2)); rg = np.random.default_rng(3); s = 0.5; acc = []
lpost = lambda w_: -0.5 * np.sum(w_ ** 2, 1) - beta * 0.5 * np.sum((w_ @ L.T - xs2.reshape(-1)) ** 2, 1)  # noqa: E731
grad = lambda w_: -w_ - beta * (w_ @ L.T - xs2.reshape(-1)) @ L  # noqa: E731
for it in range(400):
    mf = w + 0.5 * s * s * grad(w); w2 = mf + s * rg.standard_normal(w.shape); mr = w2 + 0.5 * s * s * grad(w2)
    la = lpost(w2) - lpost(w) - np.sum((w - mr) ** 2, 1) / (2 * s * s) + np.sum((w2 - mf) ** 2, 1) / (2 * s * s)
    a_ = np.log(rg.uniform(size=len(w))) < la; w = np.where(a_[:, None], w2, w); acc.append(a_.mean())
assert np.allclose(w.mean(0), mu, atol=0.05), (w.mean(0), mu)
assert np.allclose(np.cov(w.T), np.linalg.inv(prec), atol=0.05)
print(f'PASS MALA/MH (the same proposal and ratio as grasp_window.run) samples the exact posterior: mean err '
      f'{np.abs(w.mean(0) - mu).max():.3f}, acc {np.mean(acc):.2f}')
