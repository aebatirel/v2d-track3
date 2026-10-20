# Stage A6 (analysis only, uses public GT): which stream do parquet rows (mocap GT) align with?
# Object-ROI motion energy (rotation-compensated frame difference) in cam a and cam b vs GT object speed.
# Camera: s25 frame-0 cam_a fit (work/11, mocap world) propagated by our integrated cam_a rotations (C fixed).
# Model: E_X[k] ~ g[k + s_X]; if rows align to stream X then s_X ~ 0.
# Usage: a_gtalign.py <ep> ...
import sys, json, glob, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
from scipy.interpolate import CubicSpline
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
W20 = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
CAM = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/11/s24_campose_native.json')); CAM.update(json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/11/s25_refine_native.json')))
cal = json.load(open(f'{D}/public/meta/camera_calibration.json'))['cameras']

def Rwc(psi, th, ph):  # same convention as work/11/s24_campose.py
    p, t = np.radians(psi), np.radians(th)
    f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    Rr = Rot.from_rotvec(f * np.radians(ph)).as_matrix()
    return np.column_stack([Rr @ r, Rr @ d, f])

def kd(c, s):
    v = cal[f'ego_cam_{c}']; K = np.array(v['intrinsic_matrix'], float); K[:2] *= s
    return K, np.array(v['distortion_coefficients'], float)

def frames(ep, c, s):
    cap = cv2.VideoCapture(f'{D}/public/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'); out = []
    K, dist = kd(c, s); W, H = int(round(cal[f'ego_cam_{c}']['resolution'][0] * s)), int(round(cal[f'ego_cam_{c}']['resolution'][1] * s))
    mx, my = cv2.initUndistortRectifyMap(K, dist, None, K, (W, H), cv2.CV_32FC1)
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if s != 1: g = cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA)
        out.append(cv2.remap(g, mx, my, cv2.INTER_LINEAR).astype(np.float32))
    return out, K

def lag(E, g, grid=np.arange(-3, 3.0001, 0.01)):
    k = np.arange(len(g), dtype=float); spl = CubicSpline(k, g)
    best = None; cs = []
    for s in grid:
        q = k + s; m = (q >= 0) & (q <= len(g) - 1) & np.isfinite(E)
        a = E[m] - E[m].mean(); b = spl(q[m]) - spl(q[m]).mean()
        c = float(a @ b / np.sqrt((a @ a) * (b @ b) + 1e-12)); cs.append(c)
    cs = np.array(cs); i = int(np.argmax(cs))
    ds = 0.0
    if 0 < i < len(cs) - 1:
        c0, c1, c2 = cs[i - 1:i + 2]; den = c0 - 2 * c1 + c2
        ds = 0.5 * (c0 - c2) / den if den < 0 else 0.0
    return grid[i] + ds * (grid[1] - grid[0]), cs[i]

for ep in map(int, sys.argv[1:]):
    cp = CAM[str(ep)]; R0 = Rwc(cp['psi'], cp['th'], cp['ph']); C = np.array(cp['C'])
    z = np.load(f'{W20}/motion/p{ep}.npz')
    df = pq.read_table(f'{D}/public/data/chunk-000/episode_{ep:06d}.parquet').to_pandas()
    names = [o['name'] for o in df['observation.objects'].iloc[0]]
    P = {n: np.array([[float(x) for x in o['pose']] for o in row for oo in [o] if o['name'] == n] if False else
                     [[float(x) for x in [o for o in row if o['name'] == n][0]['pose']] for row in df['observation.objects']])
         for n in names}
    geo = {}
    for n in names:
        g = glob.glob(f'{D}/public/mesh/{n}/*.glb')
        m = trimesh.load(g[0], force='mesh'); v = np.asarray(m.vertices)
        cen = 0.5 * (v.min(0) + v.max(0)); geo[n] = (cen, float(np.linalg.norm(v - cen, axis=1).max()))
    n = len(df)
    # cam a orientation per frame: R_wc(k+1) = R_wc(k) R_k^T  (f_{k+1} = R_k f_k)
    Ra = [R0]
    for k in range(n - 1):
        rv = z['a_rv'][k]; Rk = Rot.from_rotvec(rv if np.isfinite(rv).all() else np.zeros(3)).as_matrix()
        Ra.append(Ra[-1] @ Rk.T)
    Eab = np.array(cal['ego_cam_a']['extrinsics_to_stereo_left'])  # a -> b: X_b = R X_a + t
    res = {}
    for c, s in (('a', 0.5), ('b', 1.0)):
        fr, K = frames(ep, c, s); H, W = fr[0].shape
        rv = z[f'{c}_rv']
        lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        f8 = [np.clip(f, 0, 255).astype(np.uint8) for f in fr]
        for nm in names:
            V = np.full((n - 1, 2), np.nan); G = np.full((n - 1, 2), np.nan)
            for k in range(n - 1):
                kp = min(k + 1, n - 1) if c == 'b' else k          # b[k] ~ a[k+1] in time (A2); ROI/geometry only
                Rw = Ra[kp] if c == 'a' else Ra[kp] @ Eab[:3, :3].T
                def proj(row):
                    pos = P[nm][row, :3]; q = P[nm][row, 3:7]
                    Ro = Rot.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()
                    X = Rw.T @ (pos + Ro @ geo[nm][0] - C)
                    return None if X[2] < 0.1 else (K @ (X / X[2]))[:2], X[2]
                p0 = proj(k); p1 = proj(k + 1)
                if p0 is None or p1 is None: continue
                (u0, z0), (u1, _) = p0, p1
                G[k] = u1 - u0
                rad = K[0, 0] * geo[nm][1] / z0 * 1.2 + 30 * s * 2
                x0, x1 = int(max(0, u0[0] - rad)), int(min(W, u0[0] + rad)); y0, y1 = int(max(0, u0[1] - rad)), int(min(H, u0[1] + rad))
                if x1 - x0 < 10 or y1 - y0 < 10 or not np.isfinite(rv[k]).all(): continue
                mask = np.zeros((H, W), np.uint8); mask[y0:y1, x0:x1] = 1
                pts = cv2.goodFeaturesToTrack(f8[k], 300, 0.005, 5, mask=mask, blockSize=5)
                if pts is None or len(pts) < 8: continue
                p1t, st, _ = cv2.calcOpticalFlowPyrLK(f8[k], f8[k + 1], pts, None, **lk)
                ok = st[:, 0] == 1
                if ok.sum() < 8: continue
                Rk = Rot.from_rotvec(rv[k]).as_matrix(); Hm = K @ Rk @ np.linalg.inv(K)
                q0 = pts.reshape(-1, 2)[ok]; q1 = p1t.reshape(-1, 2)[ok]
                qh = (np.c_[q0, np.ones(len(q0))] @ Hm.T); qh = qh[:, :2] / qh[:, 2:]
                r = q1 - qh; mv = np.linalg.norm(r, axis=1) > 1.5 * s * 2
                V[k] = np.median(r[mv], axis=0) if mv.sum() >= 5 else np.zeros(2)
            if np.nanmax(np.linalg.norm(G, axis=1)) < 3: continue
            # lag: V[k] ~ G(k + s_lag), 2D, correlation over both components
            kk = np.arange(n - 1, dtype=float); okg = np.isfinite(G).all(1)
            spl = CubicSpline(kk[okg], G[okg], axis=0); cs = []; grid = np.arange(-3, 3.0001, 0.01)
            for sh in grid:
                qq = kk + sh; m = (qq >= 0) & (qq <= n - 2) & np.isfinite(V).all(1)
                A = V[m]; B = spl(qq[m]); cs.append(float(np.sum(A * B) / np.sqrt(np.sum(A * A) * np.sum(B * B) + 1e-12)))
            cs = np.array(cs); i = int(np.argmax(cs)); ds = 0.0
            if 0 < i < len(cs) - 1:
                c0_, c1_, c2_ = cs[i - 1:i + 2]; den = c0_ - 2 * c1_ + c2_; ds = 0.5 * (c0_ - c2_) / den if den < 0 else 0.0
            sl = grid[i] + ds * 0.01
            res.setdefault(nm, {})[c] = (round(sl * 50, 1), round(cs[i], 3), round(cs[300], 3), round(cs[200], 3), round(cs[400], 3))
            np.save(f'{W20}/gtalign2_p{ep}_{nm}_{c}.npy', np.c_[V, G])
    for nm, r in res.items():
        print(f'p{ep} {nm:18s} ' + ' | '.join(f'{c}: lag {v[0]:+6.1f} ms corr {v[1]:.3f} (at -1/0/+1 fr: {v[3]:.3f}/{v[2]:.3f}/{v[4]:.3f})' for c, v in r.items()), flush=True)
