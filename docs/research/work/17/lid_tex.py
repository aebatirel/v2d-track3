"""Lid small marker that exists only in texture (flattened geometry): estimate centre from bright disc inside dark ring."""
import numpy as np
from markers_cat import load, sample
g, tex = load('white_pot_lid'); P, C, N, _ = sample(g, tex, 3_000_000, seed=1)
N = N * np.sign(np.mean(((P - P.mean(0)) * N).sum(1)))
c0 = np.array([0.0, -0.0177, -0.050])
m = (np.hypot(P[:, 1] - c0[1], P[:, 2] - c0[2]) < 0.012) & (P[:, 0] > 0)
lum = C[m].mean(1); Q = P[m]; NN = N[m]
print('n', m.sum(), 'x range mm', np.round(np.percentile(Q[:, 0], [5, 50, 95]) * 1000, 1), 'lum pct', np.round(np.percentile(lum, [5, 50, 95]), 2))
dark = lum < 0.3; bright = (lum > 0.55) & (np.hypot(Q[:, 1] - c0[1], Q[:, 2] - c0[2]) < 0.006)
dc = Q[dark].mean(0); bc = Q[bright].mean(0)
nrm = NN[dark | bright].mean(0); nrm /= np.linalg.norm(nrm)
print('dark ring centre mm', np.round(dc * 1000, 1), 'n', dark.sum(), ' bright disc centre mm', np.round(bc * 1000, 1), 'n', bright.sum(), ' normal', np.round(nrm, 3))
# radius of the dark annulus outer edge and the bright disc
rd = np.hypot(*(Q[dark][:, 1:] - dc[1:]).T); rb = np.hypot(*(Q[bright][:, 1:] - bc[1:]).T)
print('dark ring r95 mm %.1f, bright disc r95 mm %.1f' % (np.percentile(rd, 95) * 1000, np.percentile(rb, 95) * 1000))
# compare with the geometric small marker: offset of its sphere centre above the local surface
s = np.array([0.0025, 0.0582, -0.0029])
k = (np.hypot(P[:, 1] - s[1], P[:, 2] - s[2]) < 0.012) & (np.hypot(P[:, 1] - s[1], P[:, 2] - s[2]) > 0.008) & (P[:, 0] > -0.01)
print('geometric small marker: surface x around it mm', np.round(np.percentile(P[k, 0], [10, 50, 90]) * 1000, 1), 'sphere centre x', s[0] * 1000)
