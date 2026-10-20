"""Does the verifier's re-fitted beige @171 centre (1.75 mm from stage A, whose fit radius was 8.3 mm) fit the real
frame better? Public ep 11 f0 cam a, same 6 pixels as pnp_check.py, PnP over all assignments, GT poses (analysis only)."""
import numpy as np, json, sys, os
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); os.chdir(W12)
import pnp_check as pc
from selfsim import good_markers
uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
K, D = pc.variant(False)
X, lab, objs = pc.world_markers(11, 0, ['blue_cup', 'beige_cup'])
err, (perm, rv, tv, e) = pc.solve(uv, X, K, D)
print('stage-A markers: mean %.2f px per-pt %s assign %s' % (err, np.round(e, 1), [lab[i] for i in perm]))
mine = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/r2/c2_layout_beige_cup.json'))
G = good_markers('beige_cup'); M = np.array([z['centre'] for z in mine])
for k in range(3):
    j = np.argmin(np.linalg.norm(M - G[k], axis=1)); print('  stage-A beige#%d -> mine %d, %.2f mm' % (k, j, np.linalg.norm(M[j] - G[k]) * 1e3))
T = pc.T_of(objs['beige_cup']['pose']); nb = sum(1 for l in lab if l.startswith('blue'))
for variant in ('all3', 'only171'):
    X2 = X.copy()
    for k in range(3):
        j = np.argmin(np.linalg.norm(M - G[k], axis=1))
        if variant == 'only171' and np.linalg.norm(M[j] - G[k]) < 1e-3: continue
        X2[nb + k] = T[:3, :3] @ M[j] + T[:3, 3]
    err2, (perm2, rv2, tv2, e2) = pc.solve(uv, X2, K, D)
    print('verifier centres (%s): mean %.2f px per-pt %s assign %s' % (variant, err2, np.round(e2, 1), [lab[i] for i in perm2]))
