# Stage A6b (analysis only, public GT): camera-free GT-row timing. Whole-image rotation-compensated
# "mover" flow V_X[k] (median residual of moving features) ~ J_w * dp_GT(k + s), with J_w a 2x3 matrix fitted
# per window of WIN intervals (local projection Jacobian). Best for single-mover episodes.
# Usage: a_gtalign3.py <ep> [obj] ; prints lag_b, lag_a (ms) and their difference.
import sys, json, numpy as np, cv2, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
from scipy.interpolate import CubicSpline
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
W20 = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
cal = json.load(open(f'{D}/public/meta/camera_calibration.json'))['cameras']
WIN = 40
ep = int(sys.argv[1]); objsel = sys.argv[2] if len(sys.argv) > 2 else None
z = np.load(f'{W20}/motion/p{ep}.npz')
df = pq.read_table(f'{D}/public/data/chunk-000/episode_{ep:06d}.parquet').to_pandas()
names = [o['name'] for o in df['observation.objects'].iloc[0]]
P = {n: np.array([[float(x) for x in [o for o in row if o['name'] == n][0]['pose']] for row in df['observation.objects']]) for n in names}
mv = {n: np.linalg.norm(np.diff(P[n][:, :3], axis=0), axis=1).sum() for n in names}
obj = objsel or max(mv, key=mv.get)
dp = np.diff(P[obj][:, :3], axis=0)                       # [n-1, 3]
n = len(df)

def mover_flow(c, s):
    v = cal[f'ego_cam_{c}']; K = np.array(v['intrinsic_matrix'], float); K[:2] *= s
    dist = np.array(v['distortion_coefficients'], float)
    W, H = int(round(v['resolution'][0] * s)), int(round(v['resolution'][1] * s))
    mx, my = cv2.initUndistortRectifyMap(K, dist, None, K, (W, H), cv2.CV_32FC1)
    cap = cv2.VideoCapture(f'{D}/public/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if s != 1: g = cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA)
        fr.append(cv2.remap(g, mx, my, cv2.INTER_LINEAR))
    lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    V = np.full((n - 1, 2), np.nan); rv = z[f'{c}_rv']; thr = 3.0 * s
    for k in range(n - 1):
        if not np.isfinite(rv[k]).all(): continue
        p0 = cv2.goodFeaturesToTrack(fr[k], 1500, 0.003, 8, blockSize=5)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(fr[k], fr[k + 1], p0, None, **lk)
        ok = st[:, 0] == 1; q0 = p0.reshape(-1, 2)[ok]; q1 = p1.reshape(-1, 2)[ok]
        Hm = K @ Rot.from_rotvec(rv[k]).as_matrix() @ np.linalg.inv(K)
        qh = np.c_[q0, np.ones(len(q0))] @ Hm.T; qh = qh[:, :2] / qh[:, 2:]
        r = (q1 - qh) / s; m = np.linalg.norm(r, axis=1) > 3.0
        V[k] = np.median(r[m], axis=0) if m.sum() >= 10 else np.zeros(2)
    return V

def lag(V, grid=np.arange(-3, 3.0001, 0.01)):
    kk = np.arange(n - 1, dtype=float); spl = CubicSpline(kk, dp, axis=0); cost = []
    for sh in grid:
        q = kk + sh; tot = 0.0; den = 0.0
        for w0 in range(0, n - 1, WIN):
            m = (kk >= w0) & (kk < w0 + WIN) & (q >= 0) & (q <= n - 2) & np.isfinite(V).all(1)
            if m.sum() < 10: continue
            A = spl(q[m]); B = V[m]
            J, *_ = np.linalg.lstsq(np.c_[A, np.ones(len(A))], B, rcond=None)
            e = B - np.c_[A, np.ones(len(A))] @ J; tot += np.sum(e ** 2); den += np.sum((B - B.mean(0)) ** 2)
        cost.append(tot / max(den, 1e-9))
    cost = np.array(cost); i = int(np.argmin(cost)); ds = 0.0
    if 0 < i < len(cost) - 1:
        c0, c1, c2 = cost[i - 1:i + 2]; d2 = c0 - 2 * c1 + c2; ds = 0.5 * (c0 - c2) / d2 if d2 > 0 else 0.0
    return (grid[i] + ds * 0.01) * 50, cost[i], cost

Vb = mover_flow('b', 1.0); Va = mover_flow('a', 0.5)
lb, cb, cb_all = lag(Vb); la, ca, ca_all = lag(Va)
np.savez(f'{W20}/gtalign3_p{ep}.npz', Vb=Vb, Va=Va, dp=dp, obj=obj)
print(f'p{ep} {obj:18s} path {mv[obj]:.2f} m | b: lag {lb:+6.1f} ms cost {cb:.3f} (0fr {cb_all[300]:.3f}, -1fr {cb_all[250]:.3f}) | '
      f'a: lag {la:+6.1f} ms cost {ca:.3f} | a-b {la-lb:+6.1f} ms', flush=True)
