"""C2 circularity check (public ep 11 frame 0, cam a). The real-frame test fixes the camera to a PnP solve on the
6 marker pixels with GT-placed scan markers of BOTH cups, then measures spin error against GT with that camera.
Here: spin of each cup that best explains its own marker pixels (known correspondences, GT centre/tilt) under
cameras obtained (a) from all 6 points [as in real_ep11], (b) from the OTHER cup's 3 points only (P3P branch
nearest (a)), (c) leave-one-point-out 5-point solves, (d) joint camera + this cup's spin, (e) bootstrap: 6-point
camera re-solved after adding 3 px Gaussian noise to all pixels (and the same noisy pixels used for the spin)."""
import numpy as np, json, sys, itertools, cv2
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
sys.path.insert(0, W12)
import os; os.chdir(W12)
from pnp_check import variant, world_markers, T_of
from selfsim import good_markers
from scipy.spatial.transform import Rotation as Rr
from scipy.optimize import least_squares
K, D = variant(False)
UV = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
AX = json.load(open(f'{W12}/out/axes2.json'))

def pnp(Xp, uv, rv0=None, tv0=None):
    und = cv2.undistortPoints(uv.reshape(-1, 1, 2), K, D).reshape(-1, 2)
    if rv0 is None:
        ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, flags=cv2.SOLVEPNP_SQPNP)
    else: rv, tv = rv0.copy(), tv0.copy()
    ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, rv, tv, True, flags=cv2.SOLVEPNP_ITERATIVE)
    return rv, tv

def proj(Xp, rv, tv): return cv2.projectPoints(np.ascontiguousarray(Xp, float), rv, tv, K, D)[0].reshape(-1, 2)

# best assignment (as pnp_check)
best = (1e9, None)
for perm in itertools.permutations(range(len(X)), len(UV)):
    Xp = X[list(perm)]
    try: rv, tv = pnp(Xp, UV)
    except cv2.error: continue
    Rc = cv2.Rodrigues(rv)[0]
    if ((Xp @ Rc.T + tv.ravel())[:, 2] <= 0).any(): continue
    e = np.linalg.norm(proj(Xp, rv, tv) - UV, axis=1).mean()
    if e < best[0]: best = (e, list(perm), rv, tv)
e6, perm, rv6, tv6 = best
L = [lab[i] for i in perm]; print('6-pt camera %.2f px; assignment' % e6, L)
Xa = X[perm]

def spun(name, d_deg):
    """GT-placed markers of `name` spun by d about its revolution axis (body frame axes2 p,a)."""
    T = T_of(objs[name]['pose']); mk = good_markers(name); p, a = np.array(AX[name]['p']), np.array(AX[name]['a'])
    mk2 = (mk - p) @ Rr.from_rotvec(a * np.radians(d_deg)).as_matrix().T + p
    return mk2 @ T[:3, :3].T + T[:3, 3]

def best_spin(name, rv, tv, uv):
    idx = [k for k, l in enumerate(L) if l.startswith(name)]; ids = [int(L[k].split('#')[1]) for k in idx]
    ds = np.arange(-20, 20.01, 0.05)
    err = [np.linalg.norm(proj(spun(name, d)[ids], rv, tv) - uv[idx], axis=1).mean() for d in ds]
    j = int(np.argmin(err)); return ds[j], err[j]

out = {}
for name in ('blue_cup', 'beige_cup'):
    own = [k for k, l in enumerate(L) if l.startswith(name)]; oth = [k for k in range(6) if k not in own]
    r = {}
    r['a_all6'] = best_spin(name, rv6, tv6, UV)
    # (b) other cup only: P3P solutions, pick nearest to 6-pt rotation
    und = cv2.undistortPoints(UV[oth].reshape(-1, 1, 2), K, D).reshape(-1, 2)
    n, rvs, tvs = cv2.solveP3P(np.ascontiguousarray(Xa[oth]), und, np.eye(3), None, flags=cv2.SOLVEPNP_P3P)
    cands = [(np.linalg.norm(cv2.Rodrigues(rv)[0] - cv2.Rodrigues(rv6)[0]), rv, tv) for rv, tv in zip(rvs, tvs)]
    cands.sort(key=lambda c: c[0])
    r['b_other3'] = best_spin(name, cands[0][1], cands[0][2], UV) if cands else None
    r['b_other3_rotdiff_deg'] = float(np.degrees(np.linalg.norm(Rr.from_matrix(cv2.Rodrigues(cands[0][1])[0] @ cv2.Rodrigues(rv6)[0].T).as_rotvec()))) if cands else None
    # (c) leave one out
    loo = []
    for k in range(6):
        keep = [i for i in range(6) if i != k]; rv, tv = pnp(Xa[keep], UV[keep], rv6, tv6); loo.append(best_spin(name, rv, tv, UV)[0])
    r['c_loo'] = loo
    # (d) joint camera + spin (spin of this cup free)
    def res(q):
        rv, tv = q[:3].reshape(3, 1), q[3:6].reshape(3, 1); Xq = Xa.copy()
        ids = [int(L[k].split('#')[1]) for k in own]; Xq[own] = spun(name, q[6])[ids]
        return (proj(Xq, rv, tv) - UV).ravel()
    sol = least_squares(res, np.r_[rv6.ravel(), tv6.ravel(), 0.0])
    r['d_joint'] = (float(sol.x[6]), float(np.abs(sol.fun.reshape(-1, 2)).sum(1).mean()))
    # (e) bootstrap
    rng = np.random.default_rng(5); bs = []
    for t in range(200):
        uvn = UV + rng.normal(0, 3.0, UV.shape); rv, tv = pnp(Xa, uvn, rv6, tv6); bs.append(best_spin(name, rv, tv, uvn)[0])
    bs = np.array(bs); r['e_boot3px'] = dict(mean=float(bs.mean()), sd=float(bs.std()), p5=float(np.percentile(bs, 5)), p95=float(np.percentile(bs, 95)))
    out[name] = r
    print(name, json.dumps(r, default=float))
json.dump(out, open('/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/c2_circ.json', 'w'), default=float, indent=1)
