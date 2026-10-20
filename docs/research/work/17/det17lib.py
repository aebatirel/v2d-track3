"""Stage B sphere-detector helpers: DoG blob candidates (both polarities), patch features, projected-marker labels."""
import json, numpy as np, cv2
from scipy.ndimage import maximum_filter
from scipy.spatial.transform import Rotation as Rot, Slerp
import lib17 as L

def dog_candidates(G, c, s0=1.2, k=1.26, ns=11, thr=0.008, kmax=None):
    """G: grey uint8 full-res. Works at half res for cam a. Returns (x, y, r, resp, pol) in own full-res px, sorted by resp."""
    sc = 2.0 if c == 'a' else 1.0
    g = cv2.resize(G, None, fx=1 / sc, fy=1 / sc, interpolation=cv2.INTER_AREA) if sc != 1 else G
    g = g.astype(np.float32) / 255.0
    sig = s0 * k ** np.arange(ns + 1)
    B = [cv2.GaussianBlur(g, (0, 0), s) for s in sig]
    D = np.stack([B[i] - B[i + 1] for i in range(ns)])
    out = []
    for pol in (1, -1):
        Dp = pol * D; M = maximum_filter(Dp, size=(3, 3, 3), mode='nearest')
        s, y, x = np.nonzero((Dp == M) & (Dp > thr))
        r = np.sqrt(sig[s] * sig[s + 1]) * np.sqrt(2)
        out.append(np.c_[(x + 0.5) * sc - 0.5, (y + 0.5) * sc - 0.5, r * sc, Dp[s, y, x] / (k - 1), np.full(len(s), pol)])
    C = np.vstack(out); C = C[np.argsort(-C[:, 3])]
    return C[:kmax] if kmax else C

PS = 12  # patch side
def features(G, BGR, C):
    """Patch features for candidates C (x, y, r, resp, pol) on the full-res grey image G (and colour BGR or None)."""
    H, W = G.shape; F = []
    hsv = cv2.cvtColor(BGR, cv2.COLOR_BGR2HSV) if BGR is not None else None
    Gf = G.astype(np.float32)
    for x, y, r, resp, pol in C:
        h = 2.0 * r
        x0, y0 = int(round(x - h)), int(round(y - h)); s = max(int(round(2 * h)), 4)
        if x0 < 0 or y0 < 0 or x0 + s > W or y0 + s > H:
            pad = int(s + 2); Gp = cv2.copyMakeBorder(Gf[max(y0, 0):min(y0 + s, H), max(x0, 0):min(x0 + s, W)], 0, 0, 0, 0, cv2.BORDER_REPLICATE)
            P = cv2.resize(Gp, (PS, PS), interpolation=cv2.INTER_AREA) if Gp.size else np.zeros((PS, PS), np.float32)
        else:
            P = cv2.resize(Gf[y0:y0 + s, x0:x0 + s], (PS, PS), interpolation=cv2.INTER_AREA)
        m, sd = P.mean(), P.std() + 1.0
        # radial stats on the native crop
        yy, xx = np.mgrid[0:PS, 0:PS]; rr = np.hypot(xx + 0.5 - PS / 2, yy + 0.5 - PS / 2) / (PS / 4)  # in units of r
        din = P[rr < 0.6].mean(); ring = P[(rr > 1.1) & (rr < 1.6)].mean(); outer = P[rr > 1.6].mean()
        col = [0.0, 0.0, 0.0]
        if hsv is not None:
            xi, yi = int(np.clip(x, 0, W - 1)), int(np.clip(y, 0, H - 1)); q = max(int(0.5 * r), 1)
            d = hsv[max(yi - q, 0):yi + q + 1, max(xi - q, 0):xi + q + 1].reshape(-1, 3).astype(np.float32)
            col = [d[:, 1].mean(), np.median(d[:, 0]), d[:, 2].mean()]
        F.append(np.r_[((P - m) / sd).ravel(), m, sd, din, ring, outer, din - ring, ring - outer, r, resp, pol, col])
    return np.array(F, np.float32)

def gt_interp(gt, j, tau):
    T = len(gt['t']); tau = float(np.clip(tau, 0, T - 1)); i = min(int(tau), T - 2); f = tau - i
    R = Slerp([0, 1], Rot.from_matrix(gt['R'][i:i + 2, j]))([f]).as_matrix()[0]
    return R, (1 - f) * gt['t'][i, j] + f * gt['t'][i + 1, j]

def project_markers(gt, j, tau, R, C, c):
    n = gt['names'][j]; M = np.array([q['c'] for q in L.CAT[n]]); rr = np.array([q['r'] for q in L.CAT[n]])
    Rj, tj = gt_interp(gt, j, tau); X = M @ Rj.T + tj
    uv, z = L.project(X, R, C, c, own=True); return uv, z, L.cam(c)[0][0, 0] * rr / np.maximum(z, 1e-3)

def nms(D, sc_col=9):
    """greedy NMS on rows (t ci x y r ... score at sc_col): suppress centres within the larger radius of a kept one."""
    keep = []
    for i in np.argsort(-D[:, sc_col]):
        if all(np.hypot(D[i, 2] - D[k, 2], D[i, 3] - D[k, 3]) > max(D[i, 4], D[k, 4]) for k in keep): keep.append(i)
    return D[keep]

def match(dets, u, v, r, cam):
    if len(dets) == 0: return False
    d = np.hypot(dets[:, 2] - u, dets[:, 3] - v); rr = dets[:, 4] / r
    return bool(np.any((d < max(0.5 * r, 3.0 if cam == 0 else 2.0)) & (rr > 0.6) & (rr < 1.6)))

# ---------------- v2 features: vectorised bilinear sampling (patch + radial profile + rim gradient coherence + sectors) -------------
from scipy.ndimage import map_coordinates
_ANG = np.linspace(0, 2 * np.pi, 24, endpoint=False); _CA, _SA = np.cos(_ANG), np.sin(_ANG)
_RADII = np.array([0, .3, .6, .85, 1.0, 1.15, 1.4, 1.7, 2.0])
_g = (np.arange(PS) + 0.5) / PS * 4 - 2; _PY, _PX = np.meshgrid(_g, _g, indexing='ij')
def prep_image(G, BGR=None):
    Gb = cv2.GaussianBlur(G.astype(np.float32), (0, 0), 1.0)
    gx = cv2.Sobel(Gb, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(Gb, cv2.CV_32F, 0, 1, ksize=3) / 8
    hsv = cv2.cvtColor(BGR, cv2.COLOR_BGR2HSV).astype(np.float32) if BGR is not None else None
    return dict(G=Gb, gx=gx, gy=gy, hsv=hsv)
def _samp(img, xs, ys):
    return map_coordinates(img, [ys.ravel(), xs.ravel()], order=1, mode='nearest').reshape(xs.shape)
def features2(P, C):
    """C: (n, >=3) x, y, r. Returns (n, 188) float32."""
    x, y, r = C[:, 0:1], C[:, 1:2], C[:, 2:3]; n = len(C)
    if n == 0: return np.zeros((0, 188), np.float32)
    patch = _samp(P['G'], x + r * _PX.ravel()[None], y + r * _PY.ravel()[None])            # n x 144
    m = patch.mean(1, keepdims=True); s = patch.std(1, keepdims=True) + 1.0
    rx = x[:, :, None] + (r[:, :, None] * _RADII[None, None, :]) * _CA[None, :, None]      # n x 24 x 9
    ry = y[:, :, None] + (r[:, :, None] * _RADII[None, None, :]) * _SA[None, :, None]
    prof = (_samp(P['G'], rx.reshape(n, -1), ry.reshape(n, -1)).reshape(n, 24, 9) - m[:, :, None]) / s[:, :, None]
    feats = [(patch - m) / s, m, s, prof.mean(1), prof.std(1)]
    for k in (3, 4, 5):   # radii .85, 1.0, 1.15
        X_, Y_ = rx[:, :, k], ry[:, :, k]
        gx, gy = _samp(P['gx'], X_, Y_), _samp(P['gy'], X_, Y_)
        gr = gx * _CA[None] + gy * _SA[None]; gt = -gx * _SA[None] + gy * _CA[None]
        agr = np.abs(gr).mean(1, keepdims=True) + 1e-3
        feats += [gr.mean(1, keepdims=True) / s, agr / s, np.abs(gr.mean(1, keepdims=True)) / agr,
                  (np.abs(gr) > 0.5 * np.abs(gr).max(1, keepdims=True)).mean(1, keepdims=True), np.abs(gt).mean(1, keepdims=True) / agr]
    ring = prof[:, :, 5:7].mean(2).reshape(n, 8, 3).mean(2); disc = prof[:, :, :3].mean((1, 2))[:, None]   # 8 sectors at 1.15-1.4 r
    feats += [ring.min(1, keepdims=True), ring.max(1, keepdims=True), ring.min(1, keepdims=True) - disc, ring.max(1, keepdims=True) - disc, r]
    if P['hsv'] is not None:
        dx, dy = rx[:, :, :3].reshape(n, -1), ry[:, :, :3].reshape(n, -1); ox, oy = rx[:, :, 6:8].reshape(n, -1), ry[:, :, 6:8].reshape(n, -1)
        Sd, Vd = _samp(P['hsv'][:, :, 1], dx, dy), _samp(P['hsv'][:, :, 2], dx, dy); So = _samp(P['hsv'][:, :, 1], ox, oy)
        Hd = _samp(P['hsv'][:, :, 0], dx, dy)
        feats += [Sd.mean(1, keepdims=True), So.mean(1, keepdims=True), np.median(Hd, 1, keepdims=True), Vd.mean(1, keepdims=True)]
    else: feats += [np.full((n, 1), -1.0)] * 4
    return np.hstack(feats).astype(np.float32)
