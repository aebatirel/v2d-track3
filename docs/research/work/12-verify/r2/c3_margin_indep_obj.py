"""Verifier r2, C3: independent re-implementation of the two-marker branch margin (own camera, projection, optimiser).
Markers: 'A' = stage-A centres (selfsim.good_markers), 'V' = verifier re-fit centres (r2/c2_layout.py).
Upright cup, origin on the spin axis at marker height, up = GT ep 11 f0 (analysis only). Camera at distance D (to the
marker-height axis point), elevation el, azimuth az, looking at the origin; cam a K. For each visible true pair
(i,j), every wrong ordered assignment (k,l) is fitted with free spin + shift bounded |d| <= s per axis.
Variants: 'box' (3D shift), 'plane' (z shift fixed at 0: height known from the table plane).
Usage: c3_margin_indep.py <A|V> <box|plane> [cone_deg]"""
import numpy as np, json, sys, itertools, os
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rr
import pandas as pd
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c'); os.chdir(W12)
from selfsim import good_markers
src, mode = sys.argv[1], sys.argv[2]; cone = float(sys.argv[3]) if len(sys.argv) > 3 else 95.0
OBJ = os.environ.get('OBJ', 'beige_cup'); G = good_markers(OBJ)
if src == 'V':
    mine = np.array([z['centre'] for z in json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/r2/c2_layout_beige_cup.json'))])
    G = np.array([mine[np.argmin(np.linalg.norm(mine - g, axis=1))] for g in G])
d = pd.read_parquet('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_000011.parquet')
o = [x for x in d['observation.objects'].iloc[0] if x['name'] == OBJ][0]['pose']
up = Rr.from_quat([o[4], o[5], o[6], o[3]]).as_matrix().T @ np.array([0, 0, 1.])
R0 = Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix()
M = G @ R0.T
# axis point: least-squares circle through the 3 markers' xy is biased; use the wall axis from the stage-A axes file
AX = json.load(open(f'{W12}/out/axes2.json'))[OBJ]; p = np.array(AX['p']) @ R0.T
M = M - np.r_[p[:2], M[:, 2].mean()]
# emulate branch_margin.py's gauge: spin about the surface-sample centroid c0 (off-axis), camera looking at c0
OFF = os.environ.get('OFFAXIS'); C0 = np.zeros(3); LOOK = np.zeros(3)
if OFF:
    import mc_spin as mc
    g_, tex = mc.load(OBJ); P_, _, _ = mc.sample(g_, tex, 60000, seed=3); c0 = P_.mean(0)
    C0 = c0 @ R0.T - np.r_[p[:2], (G @ R0.T)[:, 2].mean()]; C0[2] = 0 if OFF == 'rot' else C0[2]
    if OFF == 'both': LOOK = C0.copy()
    print('c0 in axis frame (mm)', np.round(C0 * 1e3, 2))
SINGLE = os.environ.get('SINGLE')
cal = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']['ego_cam_a']
K = np.array(cal['intrinsic_matrix'])
th = np.arctan2(M[:, 1], M[:, 0]); nrm = np.c_[np.cos(th), np.sin(th), np.zeros(len(M))]
def cam(az, el, D):
    a, e = np.radians(az), np.radians(el); pos = D * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    z = -pos / D; x = np.cross(z, [0, 0, 1.]); x /= np.linalg.norm(x); y = np.cross(z, x); return np.stack([x, y, z]), pos
def proj(X, R, pos):
    Xc = (X - pos) @ R.T; return (Xc[:, :2] / Xc[:, 2:3]) * K[0, 0] + K[:2, 2]
def Rz(t): c, s = np.cos(t), np.sin(t); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
S = [0, 1, 2, 3, 5, 8]; rows = []
for D in (0.45, 0.60):
    for el in (30, 45, 60):
        for az in range(0, 360, 10):
            R, pos = cam(az, el, D); pos = pos + LOOK
            v = pos - M; v /= np.linalg.norm(v, axis=1, keepdims=True); vis = np.flatnonzero((v * nrm).sum(1) > np.cos(np.radians(cone)))
            for i, j in itertools.combinations(vis, 2):
                uv = proj(M[[i, j]], R, pos); best = {s: 1e9 for s in S}
                for k, l in itertools.permutations(range(len(M)), 2):
                    if (k, l) == (i, j): continue
                    t0 = np.angle(np.exp(1j * (th[i] - th[k])) + np.exp(1j * (th[j] - th[l])))
                    for s in S:
                        b = 1e-3 * s + 1e-9; nz = 3 if mode == 'box' else 2
                        def f(q):
                            sh = np.r_[q[1:1 + nz], [0] * (3 - nz)]
                            return (proj((M[[k, l]] - C0) @ Rz(q[0]).T + C0 + sh, R, pos) - uv).ravel()
                        best_s = 1e9
                        for tt in ((t0,) if SINGLE else (t0, t0 + 0.3, t0 - 0.3)):
                            r = least_squares(f, np.r_[tt, [0] * nz], bounds=(np.r_[-np.inf, [-b] * nz], np.r_[np.inf, [b] * nz]), max_nfev=300)
                            best_s = min(best_s, np.sqrt((r.fun.reshape(-1, 2) ** 2).sum(1).mean()))
                        best[s] = min(best[s], best_s)
                rows.append(dict(D=D, el=el, az=az, pair=[int(i), int(j)], nvis=len(vis), rms=best))
print('src', src, 'mode', mode, 'cone', cone, 'view-pairs', len(rows), 'views with >=2 visible', len({(q['D'], q['el'], q['az']) for q in rows}), 'of', 2 * 3 * 36)
for s in S:
    r = np.array([q['rms'][s] for q in rows])
    print('  s %d mm: median %.1f p10 %.1f; share < 3 px %.2f, < 6 px %.2f' % (s, np.median(r), np.percentile(r, 10), (r < 3).mean(), (r < 6).mean()))
json.dump(rows, open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/r2/c3_indep_{OBJ}_{src}_{mode}_{int(cone)}_{OFF}_{SINGLE}.json', 'w'))
