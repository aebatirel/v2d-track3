"""Verifier r2, C3: shift the wrong beige branch needs for an exact two-marker fit, with spin about the true revolution
axis (OFFAXIS unset) or about the off-axis surface centroid as in branch_margin.py (OFFAXIS=1). Unbounded 3D shift +
spin (4 unknowns, 4 equations); report |shift| split along the viewing ray and lateral, per view-pair (min over wrong
assignments that reach < 0.5 px). Same view grid and 95 deg cone as branch_margin.py."""
import numpy as np, json, sys, itertools, os
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rr
import pandas as pd
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c'); os.chdir(W12)
from selfsim import good_markers
OBJ = os.environ.get('OBJ', 'beige_cup'); G = good_markers(OBJ)
d = pd.read_parquet('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_000011.parquet')
o = [x for x in d['observation.objects'].iloc[0] if x['name'] == OBJ][0]['pose']
up = Rr.from_quat([o[4], o[5], o[6], o[3]]).as_matrix().T @ np.array([0, 0, 1.])
R0 = Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix()
AX = json.load(open(f'{W12}/out/axes2.json'))[OBJ]; p = np.array(AX['p']) @ R0.T
M = G @ R0.T - np.r_[p[:2], (G @ R0.T)[:, 2].mean()]
C0 = np.zeros(3)
if os.environ.get('OFFAXIS'):
    import mc_spin as mc
    g_, tex = mc.load(OBJ); P_, _, _ = mc.sample(g_, tex, 60000, seed=3); C0 = P_.mean(0) @ R0.T - np.r_[p[:2], (G @ R0.T)[:, 2].mean()]; C0[2] = 0
K = np.array(json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']['ego_cam_a']['intrinsic_matrix'])
th = np.arctan2(M[:, 1], M[:, 0]); nrm = np.c_[np.cos(th), np.sin(th), np.zeros(len(M))]
def cam(az, el, D):
    a, e = np.radians(az), np.radians(el); pos = D * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    z = -pos / D; x = np.cross(z, [0, 0, 1.]); x /= np.linalg.norm(x); y = np.cross(z, x); return np.stack([x, y, z]), pos
def proj(X, R, pos): Xc = (X - pos) @ R.T; return (Xc[:, :2] / Xc[:, 2:3]) * K[0, 0] + K[:2, 2]
def Rz(t): c, s = np.cos(t), np.sin(t); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
res = []
for D in (0.45, 0.60):
    for el in (30, 45, 60):
        for az in range(0, 360, 10):
            R, pos = cam(az, el, D); ray = -pos / np.linalg.norm(pos)
            v = pos - M; v /= np.linalg.norm(v, axis=1, keepdims=True); vis = np.flatnonzero((v * nrm).sum(1) > np.cos(np.radians(95)))
            for i, j in itertools.combinations(vis, 2):
                uv = proj(M[[i, j]], R, pos); best = None
                for k, l in itertools.permutations(range(len(M)), 2):
                    if (k, l) == (i, j): continue
                    t0 = np.angle(np.exp(1j * (th[i] - th[k])) + np.exp(1j * (th[j] - th[l])))
                    f = lambda q: np.r_[(proj((M[[k, l]] - C0) @ Rz(q[0]).T + C0 + q[1:4], R, pos) - uv).ravel(), 1e-3 * q[1:4] / 0.01]
                    r = least_squares(f, np.r_[t0, 0, 0, 0], x_scale=np.r_[1, 0.005, 0.005, 0.005])
                    e = np.sqrt((r.fun[:4].reshape(-1, 2) ** 2).sum(1).mean())
                    if e < 0.5:
                        sh = r.x[1:4]; n = np.linalg.norm(sh)
                        if best is None or n < best[0]: best = (n, abs(sh @ ray), np.linalg.norm(sh - (sh @ ray) * ray), np.max(np.abs(sh)), np.degrees(r.x[0]))
                if best: res.append(best)
res = np.array(res)
print(OBJ, 'OFFAXIS' if os.environ.get('OFFAXIS') else 'axis spin', 'exact wrong fits (<0.5 px) found for', len(res), 'view-pairs')
print('  |shift| mm median %.1f p10 %.1f; along-ray median %.1f; lateral median %.1f; max |per-axis| median %.1f p10 %.1f' % (
    np.median(res[:, 0]) * 1e3, np.percentile(res[:, 0], 10) * 1e3, np.median(res[:, 1]) * 1e3, np.median(res[:, 2]) * 1e3,
    np.median(res[:, 3]) * 1e3, np.percentile(res[:, 3], 10) * 1e3))
