"""Per-frame camera fit in the mocap world from GT-placed marker spheres seen in cams a, b, c (rig extrinsics fixed).
Detection: scale-normalised LoG blob candidates (scale-selected around the expected sphere radius) in a window around
each predicted marker; nearest candidate is associated; robust (soft-L1) least squares over the 6-DoF cam_a pose with an
optional Gaussian prior toward the initial pose."""
import numpy as np, cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import lib17 as L
FA = L.cam('a')[0][0, 0]
def gray(im): return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.
def candidates(G, uv, rpx, win):
    H, W = G.shape; s = max(rpx / np.sqrt(2), 0.8); pad = int(win + 6 * s + 3)
    x0, y0 = int(round(uv[0])) - pad, int(round(uv[1])) - pad
    if x0 < 0 or y0 < 0 or x0 + 2 * pad + 1 > W or y0 + 2 * pad + 1 > H: return []
    P = G[y0:y0 + 2 * pad + 1, x0:x0 + 2 * pad + 1]
    Ls = []
    for f in (1 / 1.5, 1.0, 1.5):
        B = cv2.GaussianBlur(P, (0, 0), s * f); Ls.append(-cv2.Laplacian(B, cv2.CV_32F, ksize=3) * (s * f) ** 2)
    Lm = Ls[1]
    mx = cv2.dilate(Lm, np.ones((3, 3), np.uint8))
    yy, xx = np.mgrid[0:P.shape[0], 0:P.shape[1]]
    pk = (Lm >= mx) & (Lm > 0.012) & (Lm >= Ls[0]) & (Lm >= Ls[2]) & ((xx - pad) ** 2 + (yy - pad) ** 2 <= win ** 2)
    out = []
    for v, u in zip(*np.nonzero(pk)):
        if not (1 <= u < P.shape[1] - 1 and 1 <= v < P.shape[0] - 1): continue
        dx = 0.5 * (Lm[v, u - 1] - Lm[v, u + 1]) / (Lm[v, u - 1] - 2 * Lm[v, u] + Lm[v, u + 1] - 1e-9)
        dy = 0.5 * (Lm[v - 1, u] - Lm[v + 1, u]) / (Lm[v - 1, u] - 2 * Lm[v, u] + Lm[v + 1, u] - 1e-9)
        out.append((x0 + u + float(np.clip(dx, -1, 1)), y0 + v + float(np.clip(dy, -1, 1)), float(Lm[v, u])))
    return out
def apply(R0, x): return Rot.from_rotvec(x[:3]).as_matrix() @ R0, x[3:]
def solve(R0, C0, X, uv, cams, prior=None, fscale=2.0):
    X, uv, cams = np.asarray(X), np.asarray(uv), np.asarray(cams)
    sc = {c: FA / L.cam(c)[0][0, 0] for c in 'abc'}
    def res(x):
        R, C = apply(R0, x); r = []
        for c in 'abc':
            m = cams == c
            if m.any(): p, _ = L.project(X[m], R, C, c); r.append(((p - uv[m]) * sc[c]).ravel())
        r = np.concatenate(r)
        if prior is not None: r = np.r_[r, x[:3] / prior[0], (x[3:] - C0) / prior[1]]
        return r
    sol = least_squares(res, np.r_[np.zeros(3), C0], loss='soft_l1', f_scale=fscale, x_scale=np.r_[1e-3, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3])
    R, C = apply(R0, sol.x)
    n = len(X) * 2; J = sol.jac[:n]
    try: cov = np.linalg.inv(sol.jac.T @ sol.jac) * max(1.4826 * np.median(np.abs(sol.fun[:n])), 0.3) ** 2
    except np.linalg.LinAlgError: cov = None
    return R, C, sol, cov
def fit_frame(gt, i, G, R, C, wins=(60, 30, 12, 8), prior=(np.radians(2.0), 0.03), objs=None, camset='abc', minc=0.02):
    R0p, C0p = R.copy(), C.copy(); info = None
    for win in wins:
        X, uv, cams, tags = [], [], [], []
        for c in camset:
            vis = L.visibility(gt, i, R, C, c)
            for j, n in enumerate(gt['names']):
                if vis[j] is None or (objs is not None and j not in objs): continue
                Mw = L.markers_world(gt, i, j)
                for k in range(len(Mw)):
                    if not vis[j]['vis'][k]: continue
                    w = win if c == 'a' else max(win * L.cam(c)[0][0, 0] / FA, 4)
                    cand = candidates(G[c], vis[j]['uv'][k], vis[j]['rpx'][k], w)
                    if not cand: continue
                    d = [np.hypot(u - vis[j]['uv'][k][0], v - vis[j]['uv'][k][1]) for u, v, _ in cand]
                    q = cand[int(np.argmin(d))]
                    X.append(Mw[k]); uv.append(q[:2]); cams.append(c); tags.append((c, j, k))
        if len(X) < 3: return None
        # prior is always relative to the ORIGINAL init (R0p, C0p)
        x_rot = Rot.from_matrix(R @ R0p.T).as_rotvec()
        Rn, Cn, sol, cov = solve(R0p, C0p, X, uv, cams, prior=prior)
        R, C = Rn, Cn
        info = dict(X=np.array(X), uv=np.array(uv), cams=np.array(cams), tags=tags, cov=cov, win=win)
    # final residuals
    e = []
    for c in 'abc':
        m = info['cams'] == c
        if m.any(): p, _ = L.project(info['X'][m], R, C, c); e.append(np.c_[np.flatnonzero(m), np.linalg.norm(p - info['uv'][m], axis=1)])
    e = np.concatenate(e); info['res'] = np.zeros(len(info['X'])); info['res'][e[:, 0].astype(int)] = e[:, 1]
    return R, C, info
