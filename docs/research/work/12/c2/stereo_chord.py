"""Stage C re-run: a/b stereo triangulation of automatically detected cam a marker blobs (public ep 11 f0) and the
rigid pair-distance (chord) identity test. No GT is used to find or triangulate: cam a blobs = stored automatic
detections (detect2d + Hough, verifier dump), cam b match = NCC of the cam a patch (grey, rescaled) along the
epipolar curve from the factory extrinsic (X_b = R X_a + t, as stored; verified in stage B re-run). GT enters only
afterwards: the GT-projected cam b positions (b2/camb_proj_cands.json, E-raw) to score the matches."""
import numpy as np, json, sys, cv2, itertools
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W)
from pnp_check import variant
cal = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']
Ka, Da = variant(False)
Kb = np.array(cal['ego_cam_b']['intrinsic_matrix']); Db = np.array(cal['ego_cam_b']['distortion_coefficients'], float)
E = np.array(cal['ego_cam_a']['extrinsics_to_stereo_left']); R, t = E[:3, :3], E[:3, 3]
A = cv2.cvtColor(cv2.imread(W + '/b/fr/p11_a_0000.png'), cv2.COLOR_BGR2GRAY).astype(np.float32)
B = cv2.cvtColor(cv2.imread(W + '/b/fr/p11_b_0000.png'), cv2.COLOR_BGR2GRAY).astype(np.float32)
dump = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/dump_real_ep11_f000_comb.json'))
gtb = np.array(json.load(open(W + '/b2/camb_proj_cands.json'))['E-raw']['uv'])     # blue#0-3, beige#0-2
def norm_a(u): return cv2.undistortPoints(np.array(u, float).reshape(1, 1, 2), Ka, Da).reshape(2)
def proj_b(X): return cv2.projectPoints(X.reshape(-1, 3), np.zeros(3), np.zeros(3), Kb, Db)[0].reshape(-1, 2)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))
def match(u_a, half_a=40, zr=(0.30, 0.90), n=1500):
    xa = np.r_[norm_a(u_a), 1.]; Zs = np.linspace(*zr, n)
    Xb = (Zs[:, None] * xa) @ R.T + t; ub = proj_b(Xb)
    s = Kb[0, 0] / Ka[0, 0] * Zs / Xb[:, 2]                      # cam a -> cam b scale at each depth
    pa = cv2.getRectSubPix(A, (2 * half_a + 1, 2 * half_a + 1), tuple(map(float, u_a)))
    best = (-2, None)
    sc = []
    for k in range(0, n, 2):
        hb = max(5, int(round(half_a * s[k])))
        tb = cv2.resize(pa, (2 * hb + 1, 2 * hb + 1), interpolation=cv2.INTER_AREA)
        if not (hb < ub[k, 0] < B.shape[1] - hb and hb < ub[k, 1] < B.shape[0] - hb): sc.append(-2); continue
        pb = cv2.getRectSubPix(B, (2 * hb + 1, 2 * hb + 1), tuple(map(float, ub[k])))
        sc.append(ncc(tb, pb))
    sc = np.array(sc); k = 2 * int(sc.argmax())
    # 2nd peak at least 15 px away along the curve
    far = np.linalg.norm(ub[::2] - ub[k], axis=1) > 15; sec = sc[far].max() if far.any() else -2
    # local 2D refinement +-2 px (handles small extrinsic / sync error), 0.25 px grid
    hb = max(5, int(round(half_a * s[k]))); tb = cv2.resize(pa, (2 * hb + 1, 2 * hb + 1), interpolation=cv2.INTER_AREA)
    bestq = (-2, ub[k])
    for dx in np.arange(-2, 2.01, 0.25):
        for dy in np.arange(-2, 2.01, 0.25):
            q = ub[k] + [dx, dy]; v = ncc(tb, cv2.getRectSubPix(B, (2 * hb + 1, 2 * hb + 1), tuple(map(float, q))))
            if v > bestq[0]: bestq = (v, q)
    return dict(ub_epi=ub[k], ub=bestq[1], ncc=bestq[0], ncc_epi=float(sc.max()), second=float(sec), Z_epi=float(Zs[k]))
def tri(u_a, u_b):
    xa = norm_a(u_a); xb = cv2.undistortPoints(np.array(u_b, float).reshape(1, 1, 2), Kb, Db).reshape(2)
    P1 = np.hstack([np.eye(3), np.zeros((3, 1))]); P2 = np.hstack([R, t[:, None]])
    X = cv2.triangulatePoints(P1, P2, xa.reshape(2, 1), xb.reshape(2, 1)).ravel(); return X[:3] / X[3]
res = {}
gt_idx = {'blue_cup': [0, 1, 2, 3], 'beige_cup': [4, 5, 6]}
for n in ['blue_cup', 'beige_cup']:
    rows = []
    for u in dump[n]['blobs_uv']:
        m = match(u); X = tri(u, m['ub']); Xe = tri(u, m['ub_epi'])
        dgt = np.linalg.norm(gtb[gt_idx[n]] - m['ub'], axis=1); j = int(dgt.argmin())
        rows.append(dict(ua=u, ub=m['ub'].tolist(), ncc=round(m['ncc'], 3), second=round(m['second'], 3), Z=round(float(X[2]), 4),
                         Z_epi=round(m['Z_epi'], 4), off_epi_px=round(float(np.linalg.norm(m['ub'] - m['ub_epi'])), 2),
                         nearest_gt_b=f'{n}#{j}', d_gt_b_px=round(float(dgt[j]), 2), X=X.tolist(), X_epi=Xe.tolist()))
        print(n, 'a', np.round(u, 1), '-> b', np.round(m['ub'], 1), 'ncc %.3f (2nd %.3f) Z %.3f m (epi-only Z %.3f, refine %.2f px) | nearest GT-proj %s %.1f px' % (
            m['ncc'], m['second'], X[2], m['Z_epi'], rows[-1]['off_epi_px'], rows[-1]['nearest_gt_b'], dgt[j]))
    for i, j in itertools.combinations(range(len(rows)), 2):
        d = np.linalg.norm(np.subtract(rows[i]['X'], rows[j]['X'])) * 1000; de = np.linalg.norm(np.subtract(rows[i]['X_epi'], rows[j]['X_epi'])) * 1000
        print('   chord blob%d-blob%d: %.1f mm (epipolar-only %.1f)' % (i, j, d, de))
    res[n] = rows
json.dump(res, open(W + '/c2/stereo_chord_ep11_f0.json', 'w'), indent=1)
