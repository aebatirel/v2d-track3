"""Marker-subset ambiguity: for 1 or 2 visible markers, how many other spins reproduce them within tol (3D, axis known)."""
import json, numpy as np, itertools
M = json.load(open('out/markers2.json'))
phis = np.radians(np.arange(0, 360, 0.5))
for n, d in M.items():
    th, h, r = np.radians(d['theta']), np.array(d['h']) * 1000, np.array(d['r']) * 1000
    P = lambda i, ph: np.array([r[i] * np.cos(th[i] + ph), r[i] * np.sin(th[i] + ph), np.full_like(ph, h[i])])
    k = len(th); out = {}
    for tol in (6, 10):
        one = []
        for i in range(k):
            c = 0
            for a in range(k):
                if a == i: continue
                res = np.linalg.norm(P(a, phis) - P(i, 0 * phis)[:, :1], axis=0).min(); c += res < tol
            one.append(1 + c)
        pairs = 0; tot = 0; worst = []
        for i, j in itertools.combinations(range(k), 2):
            tot += 1; best = np.inf
            for a, b in itertools.permutations(range(k), 2):
                if {a, b} == {i, j} and (a, b) == (i, j): continue
                e = (np.linalg.norm(P(a, phis) - P(i, 0 * phis)[:, :1], axis=0) + np.linalg.norm(P(b, phis) - P(j, 0 * phis)[:, :1], axis=0)) / 2
                best = min(best, e.min())
            pairs += best < tol; worst.append(best)
        out[tol] = (one, pairs, tot, np.round(sorted(worst)[:3], 1))
    print(f"{n:14s} 1 visible -> candidate spins per marker: tol6 {out[6][0]}, tol10 {out[10][0]};  2 visible -> pairs with a lookalike: tol6 {out[6][1]}/{out[6][2]}, tol10 {out[10][1]}/{out[10][2]}; smallest pair residuals mm {out[6][3]}")
