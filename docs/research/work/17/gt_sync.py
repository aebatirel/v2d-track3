"""Which video stream is time-aligned with the mocap GT? For GT-MOVING objects, predict markers with the GT pose at
t+s (s in frames, interpolated) and the stage-2 cameras of frame t; count circle detections within 4 px (cam-a eq).
The best s per camera estimates the GT-vs-camera offset."""
import sys, json, numpy as np, cv2
from scipy.spatial.transform import Rotation as Rot, Slerp
import lib17 as L
ep = int(sys.argv[1]); q = json.load(open(f'out/reg2_{ep}.json')); gt = L.load_gt(ep); T = len(q['cams']); N = len(gt['names'])
FA = L.cam('a')[0][0, 0]
cams = {'a': q['cams'], 'b': q['cams_b'], 'c': q['cams_c']}
sl = [Slerp(np.arange(T), Rot.from_matrix(gt['R'][:, j])) for j in range(N)]
def pose(j, tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(tau), T - 2); f = tau - i
    return sl[j]([tau]).as_matrix()[0], (1 - f) * gt['t'][i, j] + f * gt['t'][i + 1, j]
speed = np.zeros((T, N))
for j in range(N): speed[1:, j] = np.linalg.norm(np.diff(gt['t'][:, j], axis=0), axis=1) * 20
vids = {c: L.Video(ep, c) for c in 'abc'}
def circles(Gi, uv, r, win):
    x0, y0 = int(uv[0] - win - r * 1.5), int(uv[1] - win - r * 1.5); s = int(2 * (win + r * 1.5))
    if x0 < 0 or y0 < 0 or x0 + s > Gi.shape[1] or y0 + s > Gi.shape[0]: return []
    P = cv2.GaussianBlur(Gi[y0:y0 + s, x0:x0 + s], (0, 0), 1.0)
    cs = cv2.HoughCircles(P, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=max(r, 3), param1=50, param2=0.55, minRadius=max(int(0.7 * r), 2), maxRadius=int(1.4 * r) + 1)
    return [] if cs is None else [(a + x0, b + y0) for a, b, rr in cs[0]]
RAW = []; shifts = np.arange(-4, 4.01, 0.25); res = {c: {s: [] for s in shifts} for c in 'abc'}
frames = [t for t in range(3, T - 3) if (speed[t] > 0.10).any()]  # some object moving > 10 cm/s
print(f'ep {ep}: {len(frames)} frames with an object moving > 10 cm/s')
for t in frames:
    for c in 'abc':
        Gi = cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY); R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C'])
        vis = L.visibility(gt, t, R, C, c, own=True); sc = FA / L.cam(c)[0][0, 0]
        for j in range(N):
            if speed[t, j] < 0.10: continue
            M = np.array([m['c'] for m in L.CAT[gt['names'][j]]]); rr = np.array([m['r'] for m in L.CAT[gt['names'][j]]])
            for k in range(len(M)):
                if not vis[j]['vis'][k]: continue
                cs = circles(Gi, vis[j]['uv'][k], vis[j]['rpx'][k], 40 / sc)
                if not cs: continue
                cs = np.array(cs)
                for s in shifts:
                    Rj, tj = pose(j, t + s); p, _ = L.project((M[k] @ Rj.T + tj)[None], R, C, c, own=True)
                    d = np.linalg.norm(cs - p[0], axis=1).min() * sc
                    res[c][s].append(d); RAW.append((t, c, s, d))
for c in 'abc':
    print(f' cam {c}: ' + '  '.join(f's{s:+.2f}:{np.sum(np.array(res[c][s])<4):3d}' for s in shifts))

raw = np.array([(t, 'abc'.index(c), s, d) for t, c, s, d in RAW])
np.save(f'out/gtsync_raw_{ep}.npy', raw)
cap = gt['cap'] - gt['ts']
for c in 'abc':
    for b0 in range(0, T, 30):
        m = (raw[:, 1] == 'abc'.index(c)) & (raw[:, 0] >= b0) & (raw[:, 0] < b0 + 30)
        if not m.any(): continue
        cnt = [(np.sum((raw[m, 2] == s) & (raw[m, 3] < 4)), -np.median(raw[m & (raw[:, 2] == s), 3])) for s in shifts]
        k = max(range(len(shifts)), key=lambda i: cnt[i]); n = int(m.sum() / len(shifts))
        print(f'   cam {c} frames {b0:3d}-{b0+29:3d}: obs {n:3d}, best s {shifts[k]:+.2f} (n<4px {cnt[k][0]}, med {-cnt[k][1]:.1f}); capture_time-timestamp here {np.mean(cap[b0:b0+30])*20:.2f} frames')
