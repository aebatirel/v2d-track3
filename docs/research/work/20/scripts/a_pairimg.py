# Stage A7: image-level pairing check (no GT, no angular-velocity model). Warp undistorted cam a frame
# a[k+j] into cam b by the infinity homography H = K_b R_ab K_a^-1 (calibration rotation), and score the
# similarity with b[k] by NCC of blurred gradient magnitude over the upper 45% of the image (distant room).
# Fast-motion frames only. Prints the mean NCC per j and the share of frames where each j wins.
# Usage: a_pairimg.py <split> <ep> [k0 k1]
import sys, json, numpy as np, cv2
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
W20 = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
cal = json.load(open(f'{D}/public/meta/camera_calibration.json'))['cameras']
split, ep = sys.argv[1], int(sys.argv[2]); k0, k1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 10 ** 9)
z = np.load(f'{W20}/motion/{split[0]}{ep}.npz')
wb = np.degrees(np.linalg.norm(z['b_rv'], axis=1))
J = [-1, 0, 1, 2, 3]
n = len(wb) + 1
cand = [k for k in range(2, n - 4) if k0 <= k < k1 and max(wb[k - 1], wb[k]) > 0.45]
cand = cand[:: max(1, len(cand) // 40)]
def KD(c, s):
    v = cal[f'ego_cam_{c}']; K = np.array(v['intrinsic_matrix'], float); K[:2] *= s
    return K, np.array(v['distortion_coefficients'], float), (int(v['resolution'][0] * s), int(v['resolution'][1] * s))
Ka, da, sa = KD('a', 0.5); Kb, db, sb = KD('b', 1.0)
ma = cv2.initUndistortRectifyMap(Ka, da, None, Ka, sa, cv2.CV_32FC1); mb = cv2.initUndistortRectifyMap(Kb, db, None, Kb, sb, cv2.CV_32FC1)
Rab = np.array(cal['ego_cam_a']['extrinsics_to_stereo_left'])[:3, :3]   # X_b = R X_a + t
H = Kb @ Rab @ np.linalg.inv(Ka)
need_b = set(cand); need_a = set(k + j for k in cand for j in J)
def load(c, need, m, s):
    cap = cv2.VideoCapture(f'{D}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'); out = {}; i = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if i in need:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            if s != 1: g = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            out[i] = cv2.remap(g, m[0], m[1], cv2.INTER_LINEAR)
        i += 1
    return out
A = load('a', need_a, ma, 0.5); B = load('b', need_b, mb, 1.0)
def feat(g):
    g = cv2.GaussianBlur(g.astype(np.float32), (0, 0), 2.0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    return cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 2.0)
ones = np.ones(sa[::-1], np.float32)
valid = cv2.warpPerspective(ones, H, sb) > 0.99
roi = np.zeros(sb[::-1], bool); roi[: int(0.45 * sb[1]), :] = True; roi &= valid
scores = []
for k in cand:
    fb = feat(B[k])[roi]; fb = (fb - fb.mean()) / (fb.std() + 1e-6); row = []
    for j in J:
        if k + j not in A: row.append(np.nan); continue
        wa = cv2.warpPerspective(feat(A[k + j]), H, sb)[roi]; wa = (wa - wa.mean()) / (wa.std() + 1e-6)
        row.append(float(np.mean(wa * fb)))
    scores.append(row)
S = np.array(scores); win = np.nanargmax(S, axis=1)
print(f'{split[0]}{ep} rows [{k0},{min(k1,n)}) frames {len(cand)} | mean NCC per j {dict(zip(J, np.round(np.nanmean(S, 0), 3)))} | '
      f'win share {dict(zip(J, [round(float(np.mean(win == i)), 2) for i in range(len(J))]))}', flush=True)
