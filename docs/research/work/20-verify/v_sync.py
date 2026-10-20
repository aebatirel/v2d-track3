"""Verifier (DIG 20 A1): independent a/b/c timing. Per stream and frame interval: GFTT + LK (fwd-bwd), undistorted
with the given K + 14-coef model, RANSAC homography on normalised coords projected to the nearest rotation (SVD), i.e.
a different rotation estimator from the original robust Kabsch. Offsets: (1) |w| magnitude correlation (rig-rotation
free), (2) vector residual with a Kabsch rig rotation, sub-frame by spline. Cam a also per stored-image band (RS).
usage: v_sync.py <split> <ep> ...   -> work/20-verify/sync/<s><ep>.npz + printed summary"""
import sys, os, json, numpy as np, cv2
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as Rot
ROOT = '/Users/aebatirel/Documents/Code/v2d-research'; D3 = f'{ROOT}/data/track_3'; OD = f'{ROOT}/work/20-verify/sync'
CAL = json.load(open(f'{D3}/public/meta/camera_calibration.json'))['cameras']
BANDS = [(0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1)]

def KD(c, scale):
    K = np.array(CAL[f'ego_cam_{c}']['intrinsic_matrix'], float).copy(); K[:2] *= scale
    return K, np.array(CAL[f'ego_cam_{c}']['distortion_coefficients'], float)

def stream(split, ep, c):
    cap = cv2.VideoCapture(f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4')
    sc = 0.5 if c == 'a' else 1.0; K, D = KD(c, sc); G = []
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if sc != 1: g = cv2.resize(g, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        G.append(g)
    H = G[0].shape[0]; nb = 1 + (len(BANDS) if c == 'a' else 0)
    W = np.full((len(G) - 1, nb, 3), np.nan); YB = np.full((len(G) - 1, nb), np.nan)
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    for k in range(len(G) - 1):
        p = cv2.goodFeaturesToTrack(G[k], 1500, 0.005, 8, blockSize=7)
        if p is None: continue
        q, st, _ = cv2.calcOpticalFlowPyrLK(G[k], G[k + 1], p, None, **lk)
        b, st2, _ = cv2.calcOpticalFlowPyrLK(G[k + 1], G[k], q, None, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm((b - p)[:, 0], axis=1) < 0.5)
        p, q = p[ok], q[ok]
        if len(p) < 30: continue
        n0 = cv2.undistortPoints(p, K, D)[:, 0]; n1 = cv2.undistortPoints(q, K, D)[:, 0]
        y = p[:, 0, 1] / H
        for bi in range(nb):
            sel = np.ones(len(y), bool) if bi == 0 else (y >= BANDS[bi - 1][0]) & (y < BANDS[bi - 1][1])
            if sel.sum() < 20: continue
            Hm, inl = cv2.findHomography(n0[sel], n1[sel], cv2.RANSAC, 1.0 / K[0, 0] * 1.5, maxIters=3000, confidence=0.999)
            if Hm is None: continue
            U, S, Vt = np.linalg.svd(Hm); R = U @ Vt
            if np.linalg.det(R) < 0: R = -R
            # Hm maps x0 -> x1 for points at infinity: x1 ~ R x0, so R is the frame rotation (camera coords)
            W[k, bi] = Rot.from_matrix(R).as_rotvec(); YB[k, bi] = y[sel][inl[:, 0] == 1].mean()
    return W, YB

def fill(w):
    w = w.copy(); bad = ~np.isfinite(w).all(-1)
    if bad.any(): 
        idx = np.arange(len(w))
        for j in range(3): w[bad, j] = np.interp(idx[bad], idx[~bad], w[~bad, j])
    return w

def mag_offset(wx, wy, rng=3.0):
    """s maximising corr(|wx[k]|, |wy|(k+s)); positive s: X frame k ~ Y frame k+s."""
    mx, my = np.linalg.norm(fill(wx), axis=1), np.linalg.norm(fill(wy), axis=1)
    cs = CubicSpline(np.arange(len(my)), my); k = np.arange(len(mx)); best = (-2, 0)
    for s in np.arange(-rng, rng + 1e-9, 0.01):
        kk = k[(k + s >= 0) & (k + s <= len(my) - 1)]
        c = np.corrcoef(mx[kk], cs(kk + s))[0, 1]
        if c > best[0]: best = (c, s)
    return best[1], best[0]

def kabsch(A, B):  # R with A ~ R B
    U, S, Vt = np.linalg.svd(A.T @ B); d = np.sign(np.linalg.det(U @ Vt)); return U @ np.diag([1, 1, d]) @ Vt

def vec_offset(wx, wy, rng=3.0, R=None, ks=None):
    wx, wy = fill(wx), fill(wy); cs = CubicSpline(np.arange(len(wy)), wy, axis=0); k = np.arange(len(wx)) if ks is None else ks
    best = (np.inf, 0, None)
    for s in np.arange(-rng, rng + 1e-9, 0.01):
        kk = k[(k + s >= 0) & (k + s <= len(wy) - 1)]
        Y = cs(kk + s); RR = kabsch(wx[kk], Y) if R is None else R
        cost = ((wx[kk] - Y @ RR.T) ** 2).sum() / (wx[kk] ** 2).sum()
        if cost < best[0]: best = (cost, s, RR)
    return best[1], best[0], best[2]

if __name__ == '__main__':
    os.makedirs(OD, exist_ok=True); split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        key = ('p' if split == 'public' else 'e') + str(ep); f = f'{OD}/{key}.npz'
        if not os.path.exists(f):
            Wa, Ya = stream(split, ep, 'a'); Wb, _ = stream(split, ep, 'b'); Wc, _ = stream(split, ep, 'c')
            np.savez(f, Wa=Wa, Ya=Ya, Wb=Wb[:, 0], Wc=Wc[:, 0])
        z = np.load(f); Wa, Ya, Wb, Wc = z['Wa'], z['Ya'], z['Wb'], z['Wc']
        n = len(Wb); q = np.array_split(np.arange(n), 4)
        sbc_m, _ = mag_offset(Wb, Wc); sbc, cbc, _ = vec_offset(Wb, Wc)
        sab_m, cab_m = mag_offset(Wa[:, 0], Wb); sab, cab, Rab = vec_offset(Wa[:, 0], Wb)
        c0 = vec_offset(Wa[:, 0], Wb, rng=0.0)[1]
        qs = [vec_offset(Wa[:, 0], Wb, R=Rab, ks=qq)[0] for qq in q]
        band = [vec_offset(Wa[:, i], Wb, R=Rab)[0] for i in (1, 2, 3)]; yb = [np.nanmean(Ya[:, i]) for i in (1, 2, 3)]
        slope = np.polyfit(yb, np.array(band) * 50, 1)
        r = dict(key=key, n=n, bc_ms=sbc * 50, bc_mag_ms=sbc_m * 50, ab_ms=sab * 50, ab_mag_ms=sab_m * 50, ab_cost=cab, ab_cost_s0=c0,
                 ab_quarters_ms=[x * 50 for x in qs], band_ms=[x * 50 for x in band], band_y=yb, rs_slope_ms=slope[0], rs_icpt_ms=slope[1],
                 rig_ab_deg=None)
        json.dump(r, open(f'{OD}/{key}.json', 'w'), default=float)
        print(f"{key:4s} n{n:4d} | b-c {sbc*50:+6.2f} ms (mag {sbc_m*50:+6.1f}) | a-b {sab*50:+6.1f} ms (mag {sab_m*50:+6.1f}) cost {cab:.4f} vs s0 {c0:.4f} | quarters "
              + ' '.join(f'{x*50:+6.1f}' for x in qs) + ' | bands ' + ' '.join(f'{x*50:+6.1f}@{y:.2f}' for x, y in zip(band, yb)) + f' | RS slope {slope[0]:+.1f} ms/h icpt {slope[1]:+.1f}', flush=True)
