# Stage A1: per-camera inter-frame rotation (angular velocity) from KLT tracks.
# No GT used. Usage: a_motion.py <split public|evaluation> <ep> [cams=abc]
# Output: work/20/out/motion/<s><ep>.npz with, per cam X:
#   X_rv   [N-1,3]  rotation vector (rad) of frame k -> k+1 in cam X frame (bearing f_{k+1} = R f_k)
#   X_band [N-1,3,3] same, fitted on features in row bands (top/mid/bottom thirds of stored image)
#   X_bandy[N-1,3]  mean normalised row (0..1) of features used per band
#   X_n    [N-1]    inliers, X_res [N-1] inlier rms (deg), X_mad [N-1] mean abs diff of consecutive frames
import sys, os, json, numpy as np, cv2, time
from scipy.spatial.transform import Rotation as Rr
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/motion'
os.makedirs(OUT, exist_ok=True)
CAL = json.load(open(f'{D}/public/meta/camera_calibration.json'))['cameras']
SCALE = {'a': 0.5, 'b': 1.0, 'c': 1.0}

def kabsch(f1, f2, w=None):
    # R minimising sum w |f2 - R f1|^2
    if w is None: w = np.ones(len(f1))
    H = (f1 * w[:, None]).T @ f2
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T

def robust_rot(f1, f2):
    if len(f1) < 8: return None, 0, np.nan
    R = kabsch(f1, f2); inl = np.ones(len(f1), bool)
    for it in range(4):
        r = np.linalg.norm(f2 - f1 @ R.T, axis=1)
        med = np.median(r[inl]) if inl.sum() else np.median(r)
        thr = max(3.0 * 1.4826 * med, 0.0015)   # ~0.09 deg floor
        inl = r < thr
        if inl.sum() < 8: return None, 0, np.nan
        R = kabsch(f1[inl], f2[inl])
    r = np.linalg.norm(f2[inl] - f1[inl] @ R.T, axis=1)
    return R, int(inl.sum()), float(np.degrees(np.sqrt(np.mean(r ** 2))))

def bearings(pts, K, dist):
    u = cv2.undistortPoints(pts.reshape(-1, 1, 2).astype(np.float64), K, dist).reshape(-1, 2)
    f = np.c_[u, np.ones(len(u))]
    return f / np.linalg.norm(f, axis=1, keepdims=True)

def run(split, ep, cam):
    v = CAL[f'ego_cam_{cam}']; s = SCALE[cam]
    K = np.array(v['intrinsic_matrix'], float); K[:2] *= s
    dist = np.array(v['distortion_coefficients'], float)
    cap = cv2.VideoCapture(f'{D}/{split}/videos/chunk-000/observation.images.ego_cam_{cam}/episode_{ep:06d}.mp4')
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if s != 1.0: g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        frames.append(g)
    H, W = frames[0].shape
    n = len(frames)
    rv = np.full((n - 1, 3), np.nan); band = np.full((n - 1, 3, 3), np.nan); bandy = np.full((n - 1, 3), np.nan)
    nn = np.zeros(n - 1, int); res = np.full(n - 1, np.nan); mad = np.zeros(n - 1)
    lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    for k in range(n - 1):
        g0, g1 = frames[k], frames[k + 1]
        mad[k] = float(np.mean(np.abs(g0.astype(np.int16) - g1.astype(np.int16))))
        p0 = cv2.goodFeaturesToTrack(g0, maxCorners=900, qualityLevel=0.005, minDistance=12, blockSize=7)
        if p0 is None or len(p0) < 10: continue
        p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p0, None, **lk)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, p1, None, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm((pb - p0).reshape(-1, 2), axis=1) < 0.5)
        q0 = p0.reshape(-1, 2)[ok]; q1 = p1.reshape(-1, 2)[ok]
        if len(q0) < 10: continue
        f0 = bearings(q0, K, dist); f1 = bearings(q1, K, dist)
        R, ni, rr = robust_rot(f0, f1)
        if R is None: continue
        rv[k] = Rr.from_matrix(R).as_rotvec(); nn[k] = ni; res[k] = rr
        ym = 0.5 * (q0[:, 1] + q1[:, 1]) / H
        for b in range(3):
            m = (ym >= b / 3) & (ym < (b + 1) / 3)
            Rb, nb, _ = robust_rot(f0[m], f1[m])
            if Rb is not None and nb >= 15:
                band[k, b] = Rr.from_matrix(Rb).as_rotvec(); bandy[k, b] = float(np.mean(ym[m]))
    return dict(rv=rv, band=band, bandy=bandy, n=nn, res=res, mad=mad, nfr=n)

if __name__ == '__main__':
    split, ep = sys.argv[1], int(sys.argv[2]); cams = sys.argv[3] if len(sys.argv) > 3 else 'abc'
    fn = f'{OUT}/{split[0]}{ep}.npz'
    out = dict(np.load(fn)) if os.path.exists(fn) else {}
    for c in cams:
        t = time.time(); r = run(split, ep, c)
        for k, v in r.items(): out[f'{c}_{k}'] = np.asarray(v)
        print(split, ep, c, 'frames', r['nfr'], 'valid', int(np.isfinite(r['rv'][:, 0]).sum()),
              'med inl', int(np.median(r['n'])), 'med res deg', round(float(np.nanmedian(r['res'])), 3),
              'med |w| deg/fr', round(float(np.degrees(np.nanmedian(np.linalg.norm(r['rv'], axis=1)))), 3),
              f'{time.time()-t:.0f}s', flush=True)
        np.savez_compressed(fn, **out)
