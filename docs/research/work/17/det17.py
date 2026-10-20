"""Marker blob detection near a predicted location (scale-normalised LoG at the expected sphere radius) and
camera refinement by robust PnP on detected marker centres."""
import numpy as np, cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import lib17 as L
def gray(im): return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.
def detect_one(G, uv, rpx, win):
    H, W = G.shape; s = max(rpx / np.sqrt(2), 1.0); pad = int(win + 4 * s + 2)
    x0, y0 = int(round(uv[0])) - pad, int(round(uv[1])) - pad; x1, y1 = x0 + 2 * pad + 1, y0 + 2 * pad + 1
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H: return None
    P = G[y0:y1, x0:x1]
    B = cv2.GaussianBlur(P, (0, 0), s); Lp = -cv2.Laplacian(B, cv2.CV_32F, ksize=3) * s * s
    c = pad; yy, xx = np.mgrid[0:P.shape[0], 0:P.shape[1]]
    mask = (xx - c) ** 2 + (yy - c) ** 2 <= win ** 2
    R = np.where(mask, Lp, -np.inf); k = np.unravel_index(np.argmax(R), R.shape)
    v, u = k
    if not (1 <= u < P.shape[1] - 1 and 1 <= v < P.shape[0] - 1): return None
    # subpixel (quadratic)
    dx = 0.5 * (Lp[v, u - 1] - Lp[v, u + 1]) / (Lp[v, u - 1] - 2 * Lp[v, u] + Lp[v, u + 1] + 1e-9)
    dy = 0.5 * (Lp[v - 1, u] - Lp[v + 1, u]) / (Lp[v - 1, u] - 2 * Lp[v, u] + Lp[v + 1, u] + 1e-9)
    # contrast: centre mean vs ring mean
    cm = P[max(v - int(s), 0):v + int(s) + 1, max(u - int(s), 0):u + int(s) + 1].mean()
    ring = ((xx - u) ** 2 + (yy - v) ** 2 > (1.6 * rpx) ** 2) & ((xx - u) ** 2 + (yy - v) ** 2 <= (2.4 * rpx) ** 2)
    rm = P[ring].mean() if ring.any() else cm
    return dict(u=x0 + u + float(np.clip(dx, -1, 1)), v=y0 + v + float(np.clip(dy, -1, 1)), resp=float(Lp[v, u]), contrast=float(cm - rm))
def pose_params(Rwc, C): return np.r_[np.zeros(3), C]
def apply(Rwc, x): return Rot.from_rotvec(x[:3]).as_matrix() @ Rwc, x[3:]
def refine(Rwc0, C0, X, uv, cams, w=None, fscale=3.0, prior=None):
    """X: Nx3 world, uv: Nx2 detections, cams: list of 'a'/'b'/'c' per row. prior: (sigma_rot_rad, sigma_C_m) toward init."""
    X, uv = np.asarray(X), np.asarray(uv); cams = np.asarray(cams); w = np.ones(len(X)) if w is None else np.asarray(w)
    def res(x):
        R, C = apply(Rwc0, x); r = []
        for c in np.unique(cams):
            m = cams == c; p, _ = L.project(X[m], R, C, c); s = 1.0 if c == 'a' else L.cam('a')[0][0, 0] / L.cam(c)[0][0, 0]
            r.append(((p - uv[m]) * s * w[m, None]).ravel())   # residuals in cam-a-equivalent px
        r = np.concatenate(r)
        if prior is not None: r = np.r_[r, x[:3] / prior[0], (x[3:] - C0) / prior[1]]
        return r
    x0 = np.r_[np.zeros(3), C0]
    sol = least_squares(res, x0, loss='soft_l1', f_scale=fscale)
    R, C = apply(Rwc0, sol.x)
    J = sol.jac; 
    try: cov = np.linalg.inv(J.T @ J) * max(np.median(np.abs(sol.fun)) * 1.4826, 0.3) ** 2
    except Exception: cov = None
    return R, C, sol, cov
