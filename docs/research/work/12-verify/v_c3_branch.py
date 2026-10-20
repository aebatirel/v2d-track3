"""C3 check, public ep 11 f0 cam a, beige cup: how well does each spin branch explain the two detected true beige blobs
(mk0 front-left at (1261,1058), mk1 right silhouette at (1480,982); from dump_real_ep11_f000_comb.json)?
Camera = the 6-pt evaluation PnP (as in real_ep11). For each branch start (0, -131, +120, -120 deg from GT) and each
assignment of the 2 blobs to 2 distinct scan markers, fit spin + table-plane centre shift (x, y) with a 5 mm Gaussian
prior on the shift (sigma in px units 4 px for the blobs). Report residual px and shift mm. Also pure (no-refit) branch
projections. Also: which marker is predicted where under the best wrong branch (does it predict a visible 3rd marker?)."""
import numpy as np, json, sys, itertools, cv2, os
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
sys.path.insert(0, W12); os.chdir(W12)
from pnp_check import variant, world_markers, T_of, solve as pnp_solve
from selfsim import good_markers
from scipy.spatial.transform import Rotation as Rr
from scipy.optimize import least_squares
K, D = variant(False)
UV6 = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
err, (perm, rv, tv, e) = pnp_solve(UV6, X, K, D)
AX = json.load(open(f'{W12}/out/axes2.json'))
name = 'beige_cup'; T = T_of(objs[name]['pose']); mk = good_markers(name); p, a = np.array(AX[name]['p']), np.array(AX[name]['a'])
B = np.array([[1261, 1058], [1480, 982]], float)
def place(d_deg, sh):
    mk2 = (mk - p) @ Rr.from_rotvec(a * np.radians(d_deg)).as_matrix().T + p
    W = mk2 @ T[:3, :3].T + T[:3, 3]; W[:, :2] += sh; return W
def proj(W): return cv2.projectPoints(np.ascontiguousarray(W, float), rv, tv, K, D)[0].reshape(-1, 2)
print('camera reproj %.2f px' % err)
for d0 in (0, -131, 120, -120, 131):
    P0 = proj(place(d0, np.zeros(2)))
    print('branch %+4d no refit: projections' % d0, np.round(P0).astype(int).tolist())
    best = None
    for i, j in itertools.permutations(range(3), 2):
        f = lambda q: np.r_[(proj(place(q[0], q[1:3]))[[i, j]] - B).ravel() / 4.0, q[1:3] / 0.005]
        s = least_squares(f, np.r_[d0, 0, 0])
        r = proj(place(s.x[0], s.x[1:3]))[[i, j]] - B
        if abs(((s.x[0] - d0) + 180) % 360 - 180) > 25: continue
        cand = (np.linalg.norm(r, axis=1).max(), i, j, s.x, np.linalg.norm(r, axis=1))
        if best is None or cand[0] < best[0]: best = cand
    if best:
        mx, i, j, x, rr = best; third = [k for k in range(3) if k not in (i, j)][0]
        P = proj(place(x[0], x[1:3]))
        print('   refit: blobs<-mk%d,mk%d spin %+.1f shift %.1f,%.1f mm resid %s px; 3rd mk%d predicted at %s' % (
            i, j, x[0], x[1] * 1e3, x[2] * 1e3, np.round(rr, 1).tolist(), third, np.round(P[third]).astype(int).tolist()))
