"""[reg2x: copy of reg2.py with env EXCL=obj1,obj2 (removed from static anchors) and output out/reg2<SUF>_<ep>.json] Stage A refined per-frame cameras in the mocap world.
Model: b-pose(t) = Treg * D(t) * VO(t); c-pose = b-pose * T_b<-c; a-pose(t) = Treg * D(t-delta) * VO(t-delta) * T_b<-a(corr)
 - VO: stereo VO of the mono pair (vo17.py); delta, extrinsic-rotation correction: sync_fit.py (cam a vs b_t PnP)
 - D(t): slow VO-drift correction, piecewise-linear 6-DoF knots every KN frames, D(0)=I, random-walk prior
 - Treg: one 6-DoF registration (init reg17.py)
Observations: GT-placed marker spheres of GT-static objects (all frames, cams a/b/c), HoughCircles candidates,
nearest association in shrinking windows; Cauchy loss. Validation: leave-one-marker-out (LOMO) residuals.
usage: reg2.py ep [KN=15] [lomo=1]"""
import sys, os, json, numpy as np, cv2, time
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation as Rot, Slerp
import lib17 as L
ep = int(sys.argv[1]); KN = int(sys.argv[2]) if len(sys.argv) > 2 else 15; do_lomo = (sys.argv[3] == '1') if len(sys.argv) > 3 else True
SIG_R, SIG_T = np.radians(0.05), 0.002      # drift random-walk per knot step
FA = L.cam('a')[0][0, 0]
gt = L.load_gt(ep); VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO); N = len(gt['names'])
R1 = json.load(open(f'out/reg_{ep}.json')); Treg0 = np.array(R1['Treg'])
sy = json.load(open(f'out/sync_{ep}.json')); DELTA = sy['delta']
Tba = L.ext('a').copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]   # rotation correction only
Tbc = L.ext('c')
sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo_at(tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(np.floor(tau)), T - 2); f = tau - i
    M = np.eye(4); M[:3, :3] = sl([tau]).as_matrix()[0]; M[:3, 3] = (1 - f) * VO[i, :3, 3] + f * VO[i + 1, :3, 3]; return M
knots = np.arange(0, T - 1 + KN, KN); knots[-1] = min(knots[-1], T - 1); knots = np.unique(np.r_[knots, T - 1]); NK = len(knots)
def drift(K6, tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(np.searchsorted(knots, tau, side='right') - 1, NK - 2); f = (tau - knots[i]) / (knots[i + 1] - knots[i])
    v = (1 - f) * K6[i] + f * K6[i + 1]; M = np.eye(4); M[:3, :3] = Rot.from_rotvec(v[:3]).as_matrix(); M[:3, 3] = v[3:]; return M, i, f
def unpack(x):
    Dr = np.eye(4); Dr[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); Dr[:3, 3] = x[3:6]
    K6 = np.zeros((NK, 6)); K6[1:] = x[6:].reshape(NK - 1, 6); return Dr @ Treg0, K6
def cam_pose(x, t, c):
    Treg, K6 = unpack(x)
    if c == 'a': tau = t - DELTA; D, _, _ = drift(K6, tau); P = Treg @ D @ vo_at(tau) @ Tba
    else:
        D, _, _ = drift(K6, t); P = Treg @ D @ VO[t]
        if c == 'c': P = P @ Tbc
    return P[:3, :3], P[:3, 3]
static = np.zeros((T, N), bool)
for j in range(N):
    for t in range(T):
        a, b = max(t - 2, 0), min(t + 2, T - 1)
        dv = np.linalg.norm(gt['t'][b, j] - gt['t'][a, j]) / max(b - a, 1) * 20
        dr = np.degrees(np.linalg.norm(Rot.from_matrix(gt['R'][b, j] @ gt['R'][a, j].T).as_rotvec())) / max(b - a, 1) * 20
        static[t, j] = dv < 0.005 and dr < 0.5
for _n in [s for s in os.environ.get("EXCL", "").split(",") if s]: static[:, gt["names"].index(_n)] = False  # stage-B resume: exclude anchors
vids = {c: L.Video(ep, c) for c in 'abc'}
G = {(c, t): cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY) for t in range(T) for c in 'abc'}
def circles(Gi, uv, r, win):
    x0, y0 = int(uv[0] - win - r * 1.5), int(uv[1] - win - r * 1.5); s = int(2 * (win + r * 1.5))
    if x0 < 0 or y0 < 0 or x0 + s > Gi.shape[1] or y0 + s > Gi.shape[0]: return []
    P = cv2.GaussianBlur(Gi[y0:y0 + s, x0:x0 + s], (0, 0), 1.0)
    cs = cv2.HoughCircles(P, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=max(r, 3), param1=50, param2=0.55, minRadius=max(int(0.7 * r), 2), maxRadius=int(1.4 * r) + 1)
    return [] if cs is None else [(a + x0, b + y0, rr) for a, b, rr in cs[0]]
def gather(x, win, objs_mask):
    obs = []
    for t in range(T):
        for c in 'abc':
            R, C = cam_pose(x, t, c); vis = L.visibility(gt, t, R, C, c, own=True); sc = FA / L.cam(c)[0][0, 0]; w = max(win / sc, 2.5)
            for j in range(N):
                if not objs_mask[t, j]: continue
                Mw = L.markers_world(gt, t, j)
                for k in range(len(Mw)):
                    if not vis[j]['vis'][k] or vis[j]['rpx'][k] < 2.5: continue
                    cs = circles(G[(c, t)], vis[j]['uv'][k], vis[j]['rpx'][k], w)
                    if not cs: continue
                    d = [np.hypot(a - vis[j]['uv'][k][0], b - vis[j]['uv'][k][1]) for a, b, _ in cs]; i = int(np.argmin(d))
                    if d[i] <= w: obs.append(dict(t=t, c=c, j=j, k=k, X=Mw[k], uv=np.array(cs[i][:2]), z=float(vis[j]['z'][k])))
    return obs
def fit(x0, obs, fs=2.5):
    groups = {}
    for i, o in enumerate(obs): groups.setdefault((o['t'], o['c']), []).append(i)
    sc = {c: FA / L.cam(c)[0][0, 0] for c in 'abc'}
    X = np.array([o['X'] for o in obs]); UV = np.array([o['uv'] for o in obs])
    def res(x):
        r = np.zeros((len(obs), 2))
        for (t, c), ii in groups.items():
            R, C = cam_pose(x, t, c); p, _ = L.project(X[ii], R, C, c, own=True); r[ii] = (p - UV[ii]) * sc[c]
        K6 = x[6:].reshape(NK - 1, 6); dK = np.diff(np.vstack([np.zeros(6), K6]), axis=0)
        pr = np.c_[dK[:, :3] / SIG_R, dK[:, 3:] / SIG_T].ravel()
        return np.r_[r.ravel(), pr]
    # sparsity
    nres = 2 * len(obs) + 6 * (NK - 1); S = lil_matrix((nres, len(x0)), dtype=int)
    for i, o in enumerate(obs):
        tau = o['t'] - DELTA if o['c'] == 'a' else o['t']; _, ki, _ = drift(np.zeros((NK, 6)), tau)
        cols = list(range(6))
        for kk in (ki, ki + 1):
            if kk >= 1: cols += list(range(6 + 6 * (kk - 1), 12 + 6 * (kk - 1)))
        for r_ in (2 * i, 2 * i + 1): S[r_, cols] = 1
    for kk in range(NK - 1):
        for q in range(6):
            r_ = 2 * len(obs) + 6 * kk + q; S[r_, 6 + 6 * kk + q] = 1
            if kk >= 1: S[r_, 6 + 6 * (kk - 1) + q] = 1
    sol = least_squares(res, x0, loss='cauchy', f_scale=fs, jac_sparsity=S, x_scale=1e-3, max_nfev=60)
    e = np.linalg.norm(sol.fun[:2 * len(obs)].reshape(-1, 2), axis=1)
    return sol.x, e
t0 = time.time(); x = np.zeros(6 + 6 * (NK - 1))
for win in (12, 8, 6):
    obs = gather(x, win, static); x, e = fit(x, obs)
    print(f'ep {ep} win {win}: nobs {len(obs)} (a {sum(o["c"]=="a" for o in obs)} b {sum(o["c"]=="b" for o in obs)} c {sum(o["c"]=="c" for o in obs)}) res(a-eq px) med {np.median(e):.2f} p90 {np.percentile(e,90):.2f}; {time.time()-t0:.0f}s', flush=True)
Treg, K6 = unpack(x)
print('drift knots (deg, mm) max |rot| %.3f max |trans| %.1f' % (np.degrees(np.abs(K6[:, :3]).max()), np.abs(K6[:, 3:]).max() * 1000))
oo = obs; ee = e
for c in 'abc':
    for j in range(N):
        m = np.array([o['c'] == c and o['j'] == j for o in oo])
        if m.any(): print(f'   cam {c} {gt["names"][j]:18s} n {m.sum():4d} res med {np.median(ee[m]):.2f} p90 {np.percentile(ee[m],90):.2f} (a-eq px)')
cams = {c: [dict(Rwc=cam_pose(x, t, c)[0].tolist(), C=cam_pose(x, t, c)[1].tolist()) for t in range(T)] for c in 'abc'}
out = dict(ep=ep, KN=KN, delta=DELTA, x=x.tolist(), Treg=Treg.tolist(), cams=cams['a'], cams_b=cams['b'], cams_c=cams['c'],
           obs=[(o['t'], o['c'], o['j'], o['k'], float(o['uv'][0]), float(o['uv'][1]), o['z']) for o in obs], res=e.tolist())
# LOMO validation
if do_lomo:
    ids = sorted(set((o['j'], o['k']) for o in obs)); lomo = []
    for (j, k) in ids:
        m = np.array([(o['j'], o['k']) == (j, k) for o in obs])
        if m.sum() < 8: continue
        xl, _ = fit(x, [o for o, mm in zip(obs, m) if not mm])
        for o in [o for o, mm in zip(obs, m) if mm]:
            R, C = cam_pose(xl, o['t'], o['c']); p, _ = L.project(o['X'][None], R, C, o['c'], own=True)
            d = (p[0] - o['uv']); sc = FA / L.cam(o['c'])[0][0, 0]
            lomo.append((j, k, o['c'], o['t'], d[0] * sc, d[1] * sc, o['z']))
        lj = np.array([np.hypot(a[4], a[5]) for a in lomo if (a[0], a[1]) == (j, k)])
        print(f'   LOMO {gt["names"][j][:12]} m{k}: n {m.sum()} held-out res (a-eq px) med {np.median(lj):.2f} p90 {np.percentile(lj,90):.2f}', flush=True)
    la = np.array([(np.hypot(a[4], a[5]), a[6]) for a in lomo])
    mm = la[:, 0] * la[:, 1] / FA * 1000  # metric lateral error at the marker depth (mm)
    print(f'LOMO all: n {len(la)}; px(a-eq) med {np.median(la[:,0]):.2f} p75 {np.percentile(la[:,0],75):.2f} p90 {np.percentile(la[:,0],90):.2f}; lateral mm med {np.median(mm):.2f} p90 {np.percentile(mm,90):.2f}')
    out['lomo'] = lomo
json.dump(out, open(f'out/reg2{os.environ.get("SUF", "x")}_{ep}.json', 'w'))
print('total', time.time() - t0)
