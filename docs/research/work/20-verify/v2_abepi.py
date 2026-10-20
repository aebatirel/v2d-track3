"""Verifier round 2 (A1): geometric a<->b integer pairing test, no motion model.
For frames k with fast VERTICAL image motion in cam b (epipolar lines a->b are ~horizontal, so tilt motion is what
the epipolar residual sees), SIFT-match a[k+j] (j=-1..3) to b[k] and measure the distance of each b point to the
epipolar line of its a match under the CALIBRATION a->b extrinsic (as given; X_b = R X_a + t).  The true pairing
gives the smallest residual.  Also b[k] vs c[k+j] with the calibration c->b ('left_to_right') for the mono pair.
usage: v2_abepi.py <split> <ep> [row_lo row_hi] -> prints per-j median residual and inlier share"""
import sys, json, numpy as np, cv2
ROOT = '/Users/aebatirel/Documents/Code/v2d-research'; D3 = f'{ROOT}/data/track_3'
CAL = json.load(open(f'{D3}/public/meta/camera_calibration.json'))
CAM = CAL['cameras']; PAIR = [p for p in CAL['stereo_pairs'] if p['camera'] == 'ego'][0]
split, ep = sys.argv[1], int(sys.argv[2]); lo, hi = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 10**6)
JS = [-1, 0, 1, 2, 3]; NSEL = 30

def KD(c, sc=1.0):
    K = np.array(CAM[f'ego_cam_{c}']['intrinsic_matrix'], float).copy(); K[:2] *= sc
    return K, np.array(CAM[f'ego_cam_{c}']['distortion_coefficients'], float)

def path(c): return f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'

def read(c, want=None, sc=1.0):
    cap = cv2.VideoCapture(path(c)); out = {}; k = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if want is None or k in want:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            if sc != 1: g = cv2.resize(g, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            out[k] = g
        k += 1
    return out, k

def skew(t): return np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])

# pass 1: vertical flow of b between k and k+1 (median of LK tracks), choose fast-tilt frames
B, n = read('b', None, 0.5)
lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
vy = np.zeros(n)
for k in range(n - 1):
    p = cv2.goodFeaturesToTrack(B[k], 400, 0.01, 8)
    if p is None: continue
    q, st, _ = cv2.calcOpticalFlowPyrLK(B[k], B[k + 1], p, None, **lk)
    d = (q - p)[st[:, 0] == 1, 0]
    if len(d) > 20: vy[k] = 2 * np.median(d[:, 1])   # full-res px/frame
del B
# central speed at k: mean of intervals k-1 and k
vc = np.r_[vy[0], 0.5 * (vy[1:] + vy[:-1])]; sp = np.abs(vc)
cand = [k for k in np.argsort(-sp) if lo + 1 <= k <= min(hi, n - 4) - 1 and k >= 1]
sel = []
for k in cand:
    if all(abs(k - s) >= 3 for s in sel): sel.append(int(k))
    if len(sel) >= NSEL: break
sel.sort()
wantA = {k + j for k in sel for j in JS}; wantC = wantA
A, _ = read('a', wantA, 0.5); Bf, _ = read('b', set(sel)); C, _ = read('c', wantC)
Ka, Da = KD('a', 0.5); Kb, Db = KD('b'); Kc, Dc = KD('c')
T = np.array(CAM['ego_cam_a']['extrinsics_to_stereo_left'], float); Rab, tab = T[:3, :3], T[:3, 3]
Eab = skew(tab) @ Rab
L2R = np.array(PAIR['left_to_right'], float); Rcb, tcb = L2R[:3, :3], L2R[:3, 3]; Ecb = skew(tcb) @ Rcb
sift = cv2.SIFT_create(4000); bf = cv2.BFMatcher(cv2.NORM_L2)

def match(g1, g2):
    k1, d1 = sift.detectAndCompute(g1, None); k2, d2 = sift.detectAndCompute(g2, None)
    if d1 is None or d2 is None: return None, None
    m12 = bf.knnMatch(d1, d2, k=2); m21 = {m[0].queryIdx: m[0].trainIdx for m in bf.knnMatch(d2, d1, k=2) if len(m) == 2}
    good = [m[0] for m in m12 if len(m) == 2 and m[0].distance < 0.8 * m[1].distance and m21.get(m[0].trainIdx) == m[0].queryIdx]
    if len(good) < 15: return None, None
    p1 = np.float32([k1[m.queryIdx].pt for m in good]); p2 = np.float32([k2[m.trainIdx].pt for m in good])
    return p1, p2

def epi(p_src, Ks, Ds, p_b, E):
    xs = cv2.undistortPoints(p_src.reshape(-1, 1, 2), Ks, Ds)[:, 0]; xb = cv2.undistortPoints(p_b.reshape(-1, 1, 2), Kb, Db)[:, 0]
    xs = np.c_[xs, np.ones(len(xs))]; xb = np.c_[xb, np.ones(len(xb))]; l = xs @ E.T
    l = l * np.sign(l[:, 1:2]); return (xb * l).sum(1) / np.linalg.norm(l[:, :2], axis=1) * Kb[0, 0]   # signed, line normal toward +y

res = {('a', j): [] for j in JS}; res.update({('c', j): [] for j in JS}); KS = {key: [] for key in res}
for k in sel:
    for j in JS:
        for cam, src, Ks, Ds, E in (('a', A, Ka, Da, Eab), ('c', C, Kc, Dc, Ecb)):
            if k + j not in src: continue
            p1, p2 = match(src[k + j], Bf[k])
            if p1 is None: continue
            d = epi(p1, Ks, Ds, p2, E); res[(cam, j)].append(d); KS[(cam, j)].append(k)
print(f'{split[0]}{ep} rows [{lo},{hi}] frames {len(sel)} (b vertical speed median {np.median(sp[sel]):.1f} px/frame, min {sp[sel].min():.1f}; +/- {np.sum(vc[sel]>0)}/{np.sum(vc[sel]<0)})')
for key in KS: KS[key] = np.array(KS[key], int)
for cam in ('a', 'c'):
    row = []
    for j in JS:
        L = res[(cam, j)]
        if not L: row.append(f'j{j:+d}: -'); continue
        per = np.array([np.median(np.abs(d)[np.abs(d) < 15]) if (np.abs(d) < 15).sum() > 5 else np.nan for d in L])
        sg = np.array([np.median(d[np.abs(d) < 15]) if (np.abs(d) < 15).sum() > 5 else np.nan for d in L]); v = vc[KS[(cam, j)]]
        ok = np.isfinite(sg); sl, ic = np.polyfit(v[ok], sg[ok], 1); rs = np.std(sg[ok] - (sl * v[ok] + ic))
        row.append(f'j{j:+d}: |d| {np.nanmedian(per):4.2f} px, signed = {ic:+.2f} {sl:+.3f}*vy (sd {rs:.2f})')
    print(f'  {cam}[k+j] vs b[k] | ' + ' | '.join(row))
