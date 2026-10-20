# Stage A5: b/c epipolar residual vs time shift (geometric sync check, no GT).
# Rectify c (left) and b (right) with the calibration; match b[k] <-> c[k]; track c features to k-1, k+1;
# evaluate the rectified vertical residual y_b(k) - y_c(k+delta) with c interpolated quadratically in time.
# delta* (frames) minimising the residual => o_c - o_b = -delta* * 50 ms.
# Usage: a_epi.py <split> <ep> [nframes=40]
import sys, json, numpy as np, cv2
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
C = json.load(open(f'{D}/public/meta/camera_calibration.json'))
cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
Kc = np.array(cam['ego_cam_c']['intrinsic_matrix']); dc = np.array(cam['ego_cam_c']['distortion_coefficients'])
Kb = np.array(cam['ego_cam_b']['intrinsic_matrix']); db = np.array(cam['ego_cam_b']['distortion_coefficients'])
E = np.array(sp['left_to_right']); R, T = E[:3, :3].astype(np.float64).copy(), E[:3, 3].astype(np.float64).reshape(3, 1).copy()
sz = (1280, 800)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, sz, R, T, alpha=0, flags=cv2.CALIB_ZERO_DISPARITY)
m1 = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, sz, cv2.CV_32FC1)
m2 = cv2.initUndistortRectifyMap(Kb, db, R2, P2, sz, cv2.CV_32FC1)
split, ep = sys.argv[1], int(sys.argv[2]); NF = int(sys.argv[3]) if len(sys.argv) > 3 else 40
z = np.load(f'{OUT}/motion/{split[0]}{ep}.npz')
wb = np.degrees(np.linalg.norm(z['b_rv'], axis=1))
# pick NF frames k (1..n-2) with the largest pitch-ish motion around them (sum of |w| of intervals k-1, k)
sc = np.r_[0, wb[:-1] + wb[1:], 0]; sc[0] = sc[-1] = 0
ks = sorted(np.argsort(-sc)[:NF].tolist())
def read(c, need):
    cap = cv2.VideoCapture(f'{D}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4')
    out = {}; i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        if i in need:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            mm = m1 if c == 'c' else m2
            out[i] = cv2.remap(g, mm[0], mm[1], cv2.INTER_LINEAR)
        i += 1
    return out
need = set(k + d for k in ks for d in (-1, 0, 1))
fc, fb = read('c', need), read('b', need)
lk = dict(winSize=(21, 21), maxLevel=5, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
deltas = np.arange(-1.0, 1.0001, 0.02)
dy0 = []; vy = []; ay = []
for k in ks:
    c0 = fc[k]; p = cv2.goodFeaturesToTrack(c0, 1500, 0.005, 10, blockSize=7)
    if p is None: continue
    init = p.copy(); init[:, 0, 0] -= 40.0       # typical disparity guess (b is right camera)
    pb, s1, _ = cv2.calcOpticalFlowPyrLK(c0, fb[k], p, init, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(fb[k], c0, pb, None, **lk)
    pm, s3, _ = cv2.calcOpticalFlowPyrLK(c0, fc[k - 1], p, None, **lk)
    pp, s4, _ = cv2.calcOpticalFlowPyrLK(c0, fc[k + 1], p, None, **lk)
    q = p.reshape(-1, 2); qb = pb.reshape(-1, 2); qc = pc.reshape(-1, 2); qm = pm.reshape(-1, 2); qp = pp.reshape(-1, 2)
    disp = q[:, 0] - qb[:, 0]
    ok = (s1[:, 0] & s2[:, 0] & s3[:, 0] & s4[:, 0]).astype(bool) & (np.linalg.norm(qc - q, axis=1) < 0.5) \
         & (disp > 2) & (disp < 250) & (np.abs(qb[:, 1] - q[:, 1]) < 8)
    # quadratic in time through (-1, qm), (0, q), (+1, qp): y(d) = y0 + d*(yp-ym)/2 + d^2*(yp-2y0+ym)/2
    v = 0.5 * (qp[:, 1] - qm[:, 1]); a = 0.5 * (qp[:, 1] - 2 * q[:, 1] + qm[:, 1])
    dy0.append((qb[:, 1] - q[:, 1])[ok]); vy.append(v[ok]); ay.append(a[ok])
dy0 = np.concatenate(dy0); vy = np.concatenate(vy); ay = np.concatenate(ay)
fast = np.abs(vy) > 3.0
res = []
for d in deltas:
    r = dy0 - (d * vy + d * d * ay); r = r - np.median(r[fast])   # remove constant rectification offset
    res.append((np.median(np.abs(r[fast])), np.median(np.abs(r[~fast])), np.median(np.abs(r))))
res = np.array(res); i = int(np.argmin(res[:, 0]))
# robust LS: dy0 = c0 + delta*vy over fast features (Theil-like via iterative trimming)
Am = np.c_[np.ones(fast.sum()), vy[fast]]; yy = dy0[fast]; keep = np.ones(len(yy), bool)
for _ in range(5):
    coef = np.linalg.lstsq(Am[keep], yy[keep], rcond=None)[0]; rr = np.abs(yy - Am @ coef)
    keep = rr < max(3 * 1.4826 * np.median(rr[keep]), 0.3)
print(f'{split[0]}{ep}: feats {len(dy0)} fast(|vy|>3px/fr) {fast.sum()} | median|vy| fast {np.median(np.abs(vy[fast])):.1f} px/fr | '
      f'grid delta* {deltas[i]:+.2f} fr (=> o_c-o_b {-deltas[i]*50:+.1f} ms) med|res| fast {res[i,0]:.3f} px vs delta0 {res[50,0]:.3f}, '
      f'delta+-1: {res[0,0]:.2f}/{res[-1,0]:.2f} | LS delta {coef[1]:+.3f} fr (=> {-coef[1]*50:+.2f} ms), const {coef[0]:+.3f} px | slow med|res| {res[50,1]:.3f} px', flush=True)
np.savez(f'{OUT}/epi_{split[0]}{ep}.npz', deltas=deltas, res=res, dy0=dy0, vy=vy, ay=ay)
