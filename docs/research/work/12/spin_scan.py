import numpy as np, cv2
from pnp_check import *
from selfsim import axis_for
from meshlib import load, sample, rot
uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
K, D = variant(False)
und = cv2.undistortPoints(uv.reshape(-1, 1, 2), K, D).reshape(-1, 2)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
# all assignments ranked
res = []
for perm in itertools.permutations(range(len(X)), len(uv)):
    Xp = X[list(perm)]
    ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, flags=cv2.SOLVEPNP_SQPNP)
    if not ok or rv is None or rv.size == 0: continue
    ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, rv, tv, True, flags=cv2.SOLVEPNP_ITERATIVE)
    Rc = cv2.Rodrigues(rv)[0]
    if ((Xp @ Rc.T + tv.ravel())[:, 2] <= 0).any(): continue
    e = np.linalg.norm(cv2.projectPoints(Xp, rv, tv, K, D)[0].reshape(-1, 2) - uv, axis=1).mean()
    res.append((e, perm))
res.sort(); print('best 4 assignments:', [(round(e, 1), [lab[i] for i in p]) for e, p in res[:4]])
best_perm = list(res[0][1])
# spin scan: rotate one cup's markers about its own revolution axis (in body frame), keep assignment, re-solve camera
for n in ['beige_cup', 'blue_cup']:
    g, tex = load(n); P, _, _ = sample(g, tex, 200000, seed=7); p, a = axis_for(n, P)
    T = T_of(objs[n]['pose']); mk = good_markers(n)
    out = []
    for d in np.arange(-180, 180, 1.0):
        X2 = X.copy()
        mk2 = (mk - p) @ rot(a, np.radians(d)).T + p
        j = 0
        for i, l in enumerate(lab):
            if l.startswith(n): X2[i] = T[:3, :3] @ mk2[int(l.split('#')[1])] + T[:3, 3]
        Xp = X2[best_perm]
        ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, flags=cv2.SOLVEPNP_SQPNP)
        ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, rv, tv, True, flags=cv2.SOLVEPNP_ITERATIVE)
        e = np.linalg.norm(cv2.projectPoints(Xp, rv, tv, K, D)[0].reshape(-1, 2) - uv, axis=1).mean()
        out.append((d, e))
    out = np.array(out); k = out[:, 1].argmin()
    print(n, 'spin with min reproj: %.0f deg (err %.2f px); err at 0: %.2f; at +-5: %.2f/%.2f; +-10: %.2f/%.2f' % (out[k, 0], out[k, 1], out[180, 1], out[175, 1], out[185, 1], out[170, 1], out[190, 1]))
    np.save(f'out/spin_scan_ep11_{n}.npy', out)
