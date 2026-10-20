"""Segment labels per frame/object from GT kinematics (stage B, v2).
v, w over +-3 frames. quiet = v < 10 mm/s & w < 3 deg/s. rest = quiet run >= 10 frames (0.5 s) AND object height within
15 mm of its frame-0 or last-frame height (i.e. supported where it started or ended). carried = not rest & v >= 0.05 m/s;
held = not rest & v < 0.05 m/s (in hand slowly, held still in the air, being nudged, grasp/release).
returns seg (T x N: 0 rest, 1 held, 2 carried), v (m/s), w (deg/s)."""
import numpy as np
from scipy.spatial.transform import Rotation as Rot
def segments(gt, H=3, vq=0.010, wq=3.0, run=10, dz=0.015, vc=0.05):
    R, tr = gt['R'], gt['t']; T, N = tr.shape[:2]
    v = np.zeros((T, N)); w = np.zeros((T, N))
    for j in range(N):
        for t in range(T):
            a, b = max(t - H, 0), min(t + H, T - 1); dt = max(b - a, 1) / 20.0
            v[t, j] = np.linalg.norm(tr[b, j] - tr[a, j]) / dt
            w[t, j] = np.degrees(np.linalg.norm(Rot.from_matrix(R[b, j] @ R[a, j].T).as_rotvec())) / dt
    q = (v < vq) & (w < wq); seg = np.ones((T, N), int)
    for j in range(N):
        zok = (np.abs(tr[:, j, 2] - tr[0, j, 2]) < dz) | (np.abs(tr[:, j, 2] - tr[-1, j, 2]) < dz)
        t = 0
        while t < T:
            if q[t, j]:
                e = t
                while e < T and q[e, j]: e += 1
                if e - t >= run: seg[t:e, j] = np.where(zok[t:e], 0, 1)
                t = e
            else: t += 1
    seg[(seg == 1) & (v >= vc)] = 2
    return seg, v, w
