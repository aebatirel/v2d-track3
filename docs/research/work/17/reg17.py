"""Register the stereo-VO trajectory (frame b0) to the mocap world with ONE 6-DoF transform, from GT-placed marker
spheres of (GT-)static objects pooled over frames and cams a/b/c. Candidates: HoughCircles (ALT) at the predicted
sphere radius in a window around each predicted marker; nearest-candidate association; Cauchy-robust LSQ; windows
shrink 90 -> 10 px (cam-a equivalent). Init: note 11 s25 frame-0 cam_a pose.
usage: reg17.py ep [step] [moving:0/1]"""
import sys, json, numpy as np, cv2, time
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import lib17 as L
ep = int(sys.argv[1]); step = int(sys.argv[2]) if len(sys.argv) > 2 else 3; use_moving = len(sys.argv) > 3 and sys.argv[3] == '1'
FA = L.cam('a')[0][0, 0]
gt = L.load_gt(ep); VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO)
Tba = L.ext('a')  # X_b = Tba X_a
import os
from scipy.spatial.transform import Slerp
SYNC = os.path.exists(f'out/sync_{ep}.json') and os.environ.get('NOSYNC') != '1'
DELTA = 0.0
if SYNC:
    sy = json.load(open(f'out/sync_{ep}.json')); DELTA = sy['delta']; Tba = Tba.copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]
_sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo_at(tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(np.floor(tau)), T - 2); f = tau - i
    M = np.eye(4); M[:3, :3] = _sl([tau]).as_matrix()[0]; M[:3, 3] = (1 - f) * VO[i, :3, 3] + f * VO[i + 1, :3, 3]; return M
def cam_a_pose(Treg, t):
    Twa = Treg @ vo_at(t - DELTA) @ Tba; return Twa[:3, :3], Twa[:3, 3]
def cam_pose_own(Treg, t, c):
    if c == 'a': return cam_a_pose(Treg, t)
    P = Treg @ VO[t]
    if c == 'c': P = P @ L.ext('c')
    return P[:3, :3], P[:3, 3]
R0, C0 = L.s25_cam(ep); Twa0 = np.eye(4); Twa0[:3, :3] = R0; Twa0[:3, 3] = C0
Treg0 = Twa0 @ np.linalg.inv(Tba) @ np.linalg.inv(vo_at(0 - DELTA))
# static mask per frame/object from GT speed (centre speed < 5 mm/s and rotation < 0.5 deg/s over +-2 frames)
N = len(gt['names']); static = np.zeros((T, N), bool)
for j in range(N):
    for t in range(T):
        a, b = max(t - 2, 0), min(t + 2, T - 1)
        dv = np.linalg.norm(gt['t'][b, j] - gt['t'][a, j]) / max(b - a, 1) * 20
        dr = np.degrees(np.linalg.norm(Rot.from_matrix(gt['R'][b, j] @ gt['R'][a, j].T).as_rotvec())) / max(b - a, 1) * 20
        static[t, j] = dv < 0.005 and dr < 0.5
frames = list(range(0, T, step))
print(f'ep {ep}: sync delta {DELTA:.3f}; {T} frames, using every {step}; static frac per object', np.round(static.mean(0), 2), flush=True)
vids = {c: L.Video(ep, c) for c in 'abc'}
G = {(c, t): cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY) for t in frames for c in 'abc'}
def circles(Gi, uv, r, win):
    x0, y0 = int(uv[0] - win - r * 1.5), int(uv[1] - win - r * 1.5); s = int(2 * (win + r * 1.5))
    if x0 < 0 or y0 < 0 or x0 + s > Gi.shape[1] or y0 + s > Gi.shape[0]: return []
    P = cv2.GaussianBlur(Gi[y0:y0 + s, x0:x0 + s], (0, 0), 1.0)
    cs = cv2.HoughCircles(P, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=max(r, 3), param1=50, param2=0.55, minRadius=max(int(0.7 * r), 2), maxRadius=int(1.4 * r) + 1)
    return [] if cs is None else [(a + x0, b + y0, rr) for a, b, rr in cs[0]]
def gather(Treg, win):
    obs = []
    for t in frames:
        for c in 'abc':
            Rw, Cw = cam_pose_own(Treg, t, c)
            vis = L.visibility(gt, t, Rw, Cw, c, own=True); sc = FA / L.cam(c)[0][0, 0]; w = max(win / sc, 3)
            for j in range(N):
                if not (static[t, j] or use_moving): continue
                Mw = L.markers_world(gt, t, j)
                for k in range(len(Mw)):
                    if not vis[j]['vis'][k] or vis[j]['rpx'][k] < 2.5: continue
                    cs = circles(G[(c, t)], vis[j]['uv'][k], vis[j]['rpx'][k], w)
                    if not cs: continue
                    d = [np.hypot(a - vis[j]['uv'][k][0], b - vis[j]['uv'][k][1]) for a, b, _ in cs]
                    i = int(np.argmin(d))
                    if d[i] <= w: obs.append((t, c, j, k, Mw[k], cs[i][0], cs[i][1], d[i] * sc))
    return obs
def solve(Treg, obs, fs=3.0):
    tt = np.array([o[0] for o in obs]); cc = np.array([o[1] for o in obs]); X = np.array([o[4] for o in obs]); uv = np.array([[o[5], o[6]] for o in obs])
    sc = {c: FA / L.cam(c)[0][0, 0] for c in 'abc'}
    def res(x):
        D = np.eye(4); D[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); D[:3, 3] = x[3:]
        Tr = D @ Treg; r = np.zeros((len(obs), 2))
        for t in np.unique(tt):
            for c in 'abc':
                m = (tt == t) & (cc == c)
                if m.any(): Rw, Cw = cam_pose_own(Tr, t, c); p, _ = L.project(X[m], Rw, Cw, c, own=True); r[m] = (p - uv[m]) * sc[c]
        return r.ravel()
    sol = least_squares(res, np.zeros(6), loss='cauchy', f_scale=fs, x_scale=1e-3)
    D = np.eye(4); D[:3, :3] = Rot.from_rotvec(sol.x[:3]).as_matrix(); D[:3, 3] = sol.x[3:]
    e = np.linalg.norm(sol.fun.reshape(-1, 2), axis=1)
    J = sol.jac; s = 1.4826 * np.median(e)
    try: cov = np.linalg.inv(J.T @ J) * s ** 2
    except np.linalg.LinAlgError: cov = np.full((6, 6), np.nan)
    return D @ Treg, e, sol.x, cov
Treg = Treg0.copy(); t0 = time.time()
for win in (90, 60, 40, 25, 15, 10, 8):
    obs = gather(Treg, win)
    Treg, e, dx, cov = solve(Treg, obs)
    print(f'win {win}: nobs {len(obs)} (a {sum(o[1]=="a" for o in obs)}, b {sum(o[1]=="b" for o in obs)}, c {sum(o[1]=="c" for o in obs)}); '
          f'res px(a-eq) med {np.median(e):.2f} p90 {np.percentile(e,90):.2f}; inl<4px {np.mean(e<4):.2f}; step rot {np.degrees(np.linalg.norm(dx[:3])):.2f} deg trans {np.linalg.norm(dx[3:])*1000:.1f} mm; {time.time()-t0:.0f}s', flush=True)
sd = np.sqrt(np.diag(cov))
Ra, Ca = cam_a_pose(Treg, 0)
d0 = np.degrees(np.linalg.norm(cv2.Rodrigues(R0.T @ Ra)[0]))
print(f'final: sd rot {np.round(np.degrees(sd[:3]),3)} deg, sd trans {np.round(sd[3:]*1000,2)} mm (formal, robust-scaled)')
print(f'frame-0 cam_a vs s25: rot {d0:.2f} deg, dC mm {np.round((Ca-C0)*1000,1)}; heading {np.degrees(np.arctan2(Ra[1,2],Ra[0,2])):.2f} pitch {-np.degrees(np.arcsin(Ra[2,2])):.2f}')
# per-object / per-cam residual summary on final obs
oo = np.array([(o[1], gt['names'][o[2]], o[3]) for o in obs])
for c in 'abc':
    for n in gt['names']:
        m = (oo[:, 0] == c) & (oo[:, 1] == n)
        if m.any(): print(f'   cam {c} {n:18s} n {m.sum():4d} res med {np.median(e[m]):.2f} p90 {np.percentile(e[m],90):.2f} (a-eq px)')
cams = [dict(t=t, Rwc=cam_a_pose(Treg, t)[0].tolist(), C=cam_a_pose(Treg, t)[1].tolist()) for t in range(T)]
json.dump(dict(ep=ep, Treg=Treg.tolist(), cov=cov.tolist(), cams=cams, obs=[(int(o[0]), o[1], int(o[2]), int(o[3]), float(o[5]), float(o[6])) for o in obs], res=e.tolist()),
          open(f'out/reg_{ep}.json', 'w'))
