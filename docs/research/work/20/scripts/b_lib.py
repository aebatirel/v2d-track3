# Stage B helpers: calibration, b/c rectification (left = ego_cam_c, right = ego_cam_b), cam a model, frame reading.
# Conventions (verified in notes 11/15 and Stage A): stored frames upright, calibration as given; left_to_right maps
# X_b = R X_c + T; ego_cam_a extrinsics_to_stereo_left maps X_b = Rab X_a + tab (target is ego_cam_b).
import json, numpy as np, cv2
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
C = json.load(open(f'{D}/public/meta/camera_calibration.json'))
cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
def K_(n): return np.array(cam[n]['intrinsic_matrix'], float)
def D_(n): return np.array(cam[n]['distortion_coefficients'], float)
Kc, dc, Kb, db, Ka, da = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), K_('ego_cam_a'), D_('ego_cam_a')
E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float); Rab, tab = Eab[:3, :3], Eab[:3, 3]
SZ = (1280, 800); RSZ = (1600, 1000)      # rectified size enlarged so the rectified focal (~597) >= native (~565)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R, T, alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MAPC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
MAPB = cv2.initUndistortRectifyMap(Kb, db, R2, P2, RSZ, cv2.CV_32FC1)
FR = P1[0, 0]; CXR, CYR = P1[0, 2], P1[1, 2]; BASE = -P2[0, 3] / P2[0, 0]   # rectified focal, centre, baseline (m)


def vid(split, ep, c):
    return f'{D}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'


def read_frames(split, ep, c, idx):
    """Return {i: BGR frame} for the requested indices (sequential decode)."""
    idx = set(idx); cap = cv2.VideoCapture(vid(split, ep, c)); out = {}; i = 0; mx = max(idx)
    while i <= mx:
        ok, f = cap.read()
        if not ok: break
        if i in idx: out[i] = f
        i += 1
    return out


def nframes(split, ep, c='b'):
    cap = cv2.VideoCapture(vid(split, ep, c)); return int(cap.get(cv2.CAP_PROP_FRAME_COUNT))


def rect(img, which):
    m = MAPC if which == 'c' else MAPB
    return cv2.remap(img, m[0], m[1], cv2.INTER_LINEAR)


def tri_rect(xl, yl, xr, yr):
    """Triangulate rectified left (c) / right (b) points (dy already removed) -> X in rectified-left frame (m)."""
    d = np.asarray(xl, float) - np.asarray(xr, float); Z = FR * BASE / d
    X = (np.asarray(xl) - CXR) * Z / FR; Y = (0.5 * (np.asarray(yl) + np.asarray(yr)) - CYR) * Z / FR
    return np.stack([X, Y, Z], -1)


def rect_to_c(Xr): return np.asarray(Xr) @ R1          # X_c = R1^T X_rect (row vectors)
def c_to_rect(Xc): return np.asarray(Xc) @ R1.T
def c_to_b(Xc): return np.asarray(Xc) @ R.T + T.ravel()
def b_to_a(Xb): return (np.asarray(Xb) - tab) @ Rab     # X_a = Rab^T (X_b - tab)
def a_to_b(Xa): return np.asarray(Xa) @ Rab.T + tab


def proj_a(Xa):
    p, _ = cv2.projectPoints(np.asarray(Xa, float).reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, da)
    return p.reshape(-1, 2)


def undist_a_pts(uv):
    """Distorted cam a pixels -> normalized rays (x, y, 1)."""
    p = cv2.undistortPoints(np.asarray(uv, float).reshape(-1, 1, 2), Ka, da, None, None, None,
                            (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 100, 1e-12)).reshape(-1, 2)
    return np.c_[p, np.ones(len(p))]


def rect_dy(gc, gb, mask=None):
    """Per-frame rectified vertical offset y_b - y_c from LK matches (median), plus match count."""
    p = cv2.goodFeaturesToTrack(gc, 2000, 0.005, 8, mask=mask, blockSize=7)
    init = p.copy(); init[:, 0, 0] -= 40.0
    lk = dict(winSize=(21, 21), maxLevel=5, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    pb, s1, _ = cv2.calcOpticalFlowPyrLK(gc, gb, p, init, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(gb, gc, pb, None, **lk)
    q, qb, qc = p.reshape(-1, 2), pb.reshape(-1, 2), pc.reshape(-1, 2)
    d = q[:, 0] - qb[:, 0]
    ok = (s1[:, 0] & s2[:, 0]).astype(bool) & (np.linalg.norm(qc - q, axis=1) < 0.5) & (d > 2) & (d < 250) & (np.abs(qb[:, 1] - q[:, 1]) < 8)
    dy = qb[ok, 1] - q[ok, 1]
    return float(np.median(dy)), int(ok.sum()), float(1.4826 * np.median(np.abs(dy - np.median(dy))))


def dy_field(rc, rb, n=6000):
    """Smooth rectified vertical misalignment y_b - y_c as a quadratic in (x, y) from 2-D-localisable LK matches."""
    p = cv2.goodFeaturesToTrack(rc, n, 0.002, 6, blockSize=7); init = p.copy(); init[:, 0, 0] -= 50
    lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.005))
    pb, s1, _ = cv2.calcOpticalFlowPyrLK(rc, rb, p, init, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(rb, rc, pb, None, **lk)
    q, qb, qc = p.reshape(-1, 2), pb.reshape(-1, 2), pc.reshape(-1, 2); d = q[:, 0] - qb[:, 0]
    ok = (s1[:, 0] & s2[:, 0]).astype(bool) & (np.linalg.norm(qc - q, axis=1) < 0.2) & (d > 3) & (d < 250) & (np.abs(qb[:, 1] - q[:, 1]) < 8)
    eig = cv2.cornerMinEigenVal(rc, 7); e = eig[q[:, 1].astype(int).clip(0, RSZ[1] - 1), q[:, 0].astype(int).clip(0, RSZ[0] - 1)]
    ok &= e > np.percentile(e[ok], 40)
    x, y, dyv = q[ok, 0], q[ok, 1], qb[ok, 1] - q[ok, 1]
    Xf = lambda x, y: np.c_[np.ones_like(x), x / 1000, y / 1000, (x / 1000) ** 2, x * y / 1e6, (y / 1000) ** 2]
    keep = np.ones(len(x), bool)
    for _ in range(4):
        cf = np.linalg.lstsq(Xf(x[keep], y[keep]), dyv[keep], rcond=None)[0]; r = dyv - Xf(x, y) @ cf
        keep = np.abs(r) < max(3 * 1.4826 * np.median(np.abs(r[keep])), 0.25)
    f = lambda xx, yy: (Xf(np.ravel(xx).astype(float), np.ravel(yy).astype(float)) @ cf).reshape(np.shape(xx))
    return f, dict(n=int(keep.sum()), rms=float(np.sqrt(np.mean(r[keep] ** 2))), coef=cf.tolist())


def rect_pair(gc, gb):
    """Rectify c/b and resample b by the fitted dy field so that rows correspond (residual dy ~0 everywhere)."""
    rc, rb = rect(gc, 'c'), rect(gb, 'b'); f, info = dy_field(rc, rb)
    yy, xx = np.mgrid[0:RSZ[1], 0:RSZ[0]].astype(np.float32)
    rbw = cv2.remap(rb, xx, (yy + f(xx, yy)).astype(np.float32), cv2.INTER_LINEAR)
    return rc, rbw, f, info
