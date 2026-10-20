"""Verifier: global-shutter control for the band method: cam b per-band rotations vs cam c full-frame."""
import sys, numpy as np, v_sync
from v_sync import *
split = sys.argv[1]
for ep in map(int, sys.argv[2:]):
    # run stream() for b with bands by temporarily treating it like 'a' band-wise
    cap_c = 'b'
    orig = v_sync.stream
    def stream_b(split, ep):
        import cv2
        cap = cv2.VideoCapture(f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_b/episode_{ep:06d}.mp4'); K, D = KD('b', 1.0); G = []
        while True:
            ok, f = cap.read()
            if not ok: break
            G.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
        return G, K, D
    G, K, D = stream_b(split, ep); H = G[0].shape[0]
    W = np.full((len(G) - 1, 4, 3), np.nan); YB = np.full((len(G) - 1, 4), np.nan)
    lk = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    for k in range(len(G) - 1):
        p = cv2.goodFeaturesToTrack(G[k], 1500, 0.005, 8, blockSize=7)
        q, st, _ = cv2.calcOpticalFlowPyrLK(G[k], G[k + 1], p, None, **lk); b, st2, _ = cv2.calcOpticalFlowPyrLK(G[k + 1], G[k], q, None, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm((b - p)[:, 0], axis=1) < 0.5); p, q = p[ok], q[ok]
        n0 = cv2.undistortPoints(p, K, D)[:, 0]; n1 = cv2.undistortPoints(q, K, D)[:, 0]; y = p[:, 0, 1] / H
        for bi in range(4):
            sel = np.ones(len(y), bool) if bi == 0 else (y >= BANDS[bi - 1][0]) & (y < BANDS[bi - 1][1])
            if sel.sum() < 20: continue
            Hm, inl = cv2.findHomography(n0[sel], n1[sel], cv2.RANSAC, 1.5 / K[0, 0], maxIters=3000, confidence=0.999)
            if Hm is None: continue
            U, S, Vt = np.linalg.svd(Hm); R = U @ Vt
            if np.linalg.det(R) < 0: R = -R
            W[k, bi] = Rot.from_matrix(R).as_rotvec(); YB[k, bi] = y[sel][inl[:, 0] == 1].mean()
    key = ('p' if split == 'public' else 'e') + str(ep); Wc = np.load(f'{OD}/{key}.npz')['Wc']
    s0, c0, Rbc = vec_offset(W[:, 0], Wc)
    band = [vec_offset(W[:, i], Wc, R=Rbc)[0] * 50 for i in (1, 2, 3)]; yb = [np.nanmean(YB[:, i]) for i in (1, 2, 3)]
    print(f'{key}: b(full)-c {s0*50:+.2f} ms | b bands vs c: ' + ' '.join(f'{x:+.1f}@{y:.2f}' for x, y in zip(band, yb)) + f' | slope {np.polyfit(yb, band, 1)[0]:+.1f} ms/h', flush=True)
