"""Verifier: feature-level rolling-shutter + offset fit for cam a, with no band rotations. Each cam-a feature track
(a[k] row y0 -> a[k+1] row y1) is predicted from the cam-b orientation track (cumulative b rotations, slerp) at
b-index times t0 = k + d + tau*y0, t1 = k + 1 + d + tau*y1, mapped by the rig rotation; robust angular residual.
Profile over tau (frames per stored-image height), delta minimised for each tau.  usage: v_rsfeat.py <split> <ep> ..."""
import sys, numpy as np, cv2
from scipy.optimize import minimize_scalar
from scipy.spatial.transform import Rotation as Rot, Slerp
from v_sync import *
def tracks(split, ep, ks):
    cap = cv2.VideoCapture(f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4')
    K, D = KD('a', 0.5); G = []
    while True:
        ok, f = cap.read()
        if not ok: break
        G.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    H = G[0].shape[0]; lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    out = []
    for k in ks:
        p = cv2.goodFeaturesToTrack(G[k], 400, 0.005, 12, blockSize=7)
        q, st, _ = cv2.calcOpticalFlowPyrLK(G[k], G[k + 1], p, None, **lk); b, st2, _ = cv2.calcOpticalFlowPyrLK(G[k + 1], G[k], q, None, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm((b - p)[:, 0], axis=1) < 0.5); p, q = p[ok], q[ok]
        def bear(x):
            n = cv2.undistortPoints(x, K, D)[:, 0]; v = np.c_[n, np.ones(len(n))]; return v / np.linalg.norm(v, axis=1, keepdims=True)
        out.append(np.c_[np.full(len(p), k), p[:, 0, 1] / H, q[:, 0, 1] / H, bear(p), bear(q)])
    return np.vstack(out), K[0, 0]
if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        key = ('p' if split == 'public' else 'e') + str(ep); z = np.load(f'{OD}/{key}.npz')
        Wa, Wb = fill(z['Wa'][:, 0]), fill(z['Wb']); N = len(Wb)
        _, _, Rab = vec_offset(Wa, Wb); Rab = Rot.from_matrix(Rab)
        O = [Rot.identity()]
        for k in range(N): O.append(Rot.from_rotvec(Wb[k]) * O[-1])
        sl = Slerp(np.arange(N + 1), Rot.concatenate(O))
        mag = np.linalg.norm(Wb, axis=1); ks = [k for k in range(4, N - 4) if mag[k] > np.median(mag)]
        T, f = tracks(split, ep, ks); c = float(__import__("os").environ.get("CPX", "3")) / f
        k, y0, y1, F0, F1 = T[:, 0], T[:, 1], T[:, 2], T[:, 3:6], T[:, 6:9]
        Cum = CubicSpline(np.arange(N + 1), np.r_[np.zeros((1, 3)), np.cumsum(Wb, 0)], axis=0)
        CUB = __import__('os').environ.get('INTERP', 'slerp') == 'cubic'
        def cost(d, tau):
            t0 = np.clip(k + d + tau * y0, 0, N); t1 = np.clip(k + 1 + d + tau * y1, 0, N)
            if CUB: P = Rot.from_rotvec(Rab.apply(Cum(t1) - Cum(t0))).apply(F0)
            else: Rel = Rab * sl(t1) * sl(t0).inv() * Rab.inv(); P = Rel.apply(F0)
            ang = np.arccos(np.clip((P * F1).sum(1), -1, 1)); return np.mean(np.minimum(ang, c) ** 2) / c ** 2
        prof = []
        for tau in np.arange(0.0, 0.951, 0.05):
            r = minimize_scalar(lambda d: cost(d, tau), bounds=(-2.6, -0.4), method='bounded', options=dict(xatol=1e-3))
            prof.append((tau, r.x, r.fun))
        prof = np.array(prof); i = int(np.argmin(prof[:, 2])); j = slice(max(i - 2, 0), i + 3)
        a = np.polyfit(prof[j, 0], prof[j, 2], 2); tau_b = -a[1] / (2 * a[0]) if a[0] > 0 else prof[i, 0]
        d_b = minimize_scalar(lambda d: cost(d, tau_b), bounds=(-2.6, -0.4), method='bounded').x
        n = int(round(-d_b - 0.2))
        print(f'{key:4s} feats {len(T)} | best tau {tau_b*50:5.1f} ms/height, top-row delta {d_b*50:+6.1f} ms -> t(a[k+{n}],y)-t(b[k]) = {(d_b+n)*50:+5.1f} + {tau_b*50:4.1f} y | '
              + 'profile ' + ' '.join(f'{t*50:.0f}:{v:.4f}' for t, _, v in prof[::2]), flush=True)
