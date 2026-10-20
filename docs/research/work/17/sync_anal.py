"""Do per-frame cam-a residual means correlate with image velocity (a-vs-b time offset / rolling shutter)?"""
import sys, json, numpy as np
import lib17 as L
ep = int(sys.argv[1]); q = json.load(open(f'out/reg_{ep}.json')); gt = L.load_gt(ep); cams = q['cams']; T = len(cams)
rows = []
for (t, c, j, k, u, v) in q['obs']:
    if c != 'a' or t == 0 or t >= T - 1: continue
    X = L.markers_world(gt, t, j)[k]
    p = {}
    for dt in (-1, 0, 1):
        cm = cams[t + dt]; p[dt], _ = L.project(X[None], np.array(cm['Rwc']), np.array(cm['C']), 'a')
    vel = (p[1] - p[-1])[0] / 2  # px per frame (camera-induced, static point)
    rows.append((t, u - p[0][0, 0], v - p[0][0, 1], vel[0], vel[1], v))
r = np.array(rows)
res = r[:, 1:3].ravel(); vel = r[:, 3:5].ravel()
k = np.dot(vel, res) / np.dot(vel, vel)
print(f'n {len(r)}; |vel| med {np.median(np.hypot(r[:,3],r[:,4])):.2f} px/frame; LS fit res = k*vel: k = {k:+.3f} frames ({k*50:+.1f} ms); '
      f'resid rms before {np.sqrt(np.mean(res**2)):.2f} after {np.sqrt(np.mean((res-k*vel)**2)):.2f}; corr {np.corrcoef(vel,res)[0,1]:+.2f}')
# rolling shutter: k depends on image row?  fit res = (k0 + k1*(v-760)/1520) * vel
A = np.c_[vel, vel * (np.repeat(r[:, 5], 2) - 760) / 1520]
sol, *_ = np.linalg.lstsq(A, res, rcond=None)
print(f'with row term: k0 {sol[0]:+.3f} k1 {sol[1]:+.3f} frames; rms after {np.sqrt(np.mean((res - A @ sol)**2)):.2f}')
