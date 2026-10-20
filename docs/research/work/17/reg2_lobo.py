"""LOBO validation for the stage A refined per-frame cameras in the mocap world.
Model: b-pose(t) = Treg * D(t) * VO(t); c-pose = b-pose * T_b<-c; a-pose(t) = Treg * D(t-delta) * VO(t-delta) * T_b<-a(corr)
 - VO: stereo VO of the mono pair (vo17.py); delta, extrinsic-rotation correction: sync_fit.py (cam a vs b_t PnP)
 - D(t): slow VO-drift correction, piecewise-linear 6-DoF knots every KN frames, D(0)=I, random-walk prior
 - Treg: one 6-DoF registration (init reg17.py)
Observations: GT-placed marker spheres of GT-static objects (all frames, cams a/b/c), HoughCircles candidates,
nearest association in shrinking windows; Cauchy loss. Validation: leave-one-marker-out (LOMO) residuals.
usage: reg2.py ep [KN=15] [lomo=1]"""
import sys, json, numpy as np, cv2, time
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

# ---- leave-one-block-out (LOBO): hold out all static observations in a 30-frame block, refit, predict them ----
q = json.load(open(f'out/reg2_{ep}.json')); x = np.array(q['x'])
obs = [dict(t=t, c=c, j=j, k=k, X=L.markers_world(gt, t, j)[k], uv=np.array([u, v]), z=z) for (t, c, j, k, u, v, z) in q['obs']]
BL = int(sys.argv[4]) if len(sys.argv) > 4 else 30
rows = []
for b0 in range(0, T, BL):
    m = np.array([b0 <= o['t'] < b0 + BL for o in obs])
    if m.sum() < 5 or (~m).sum() < 20: continue
    xl, _ = fit(x, [o for o, mm in zip(obs, m) if not mm])
    e = []
    for o in [o for o, mm in zip(obs, m) if mm]:
        R, C = cam_pose(xl, o['t'], o['c']); p, _ = L.project(o['X'][None], R, C, o['c'], own=True); sc = FA / L.cam(o['c'])[0][0, 0]
        d = np.linalg.norm(p[0] - o['uv']) * sc; e.append((d, d * o['z'] / FA * 1000)); rows.append((b0, o['t'], o['c'], d, d * o['z'] / FA * 1000))
    e = np.array(e)
    # how far is this block from the nearest retained observation (frames)?
    kept_t = np.array([o['t'] for o, mm in zip(obs, m) if not mm]); gap = np.max([np.min(np.abs(kept_t - t)) for t in range(b0, min(b0 + BL, T))])
    print(f'   LOBO block {b0:3d}-{b0+BL-1:3d}: held-out n {m.sum():3d}, max gap to kept obs {gap:3d} frames; px med {np.median(e[:,0]):.2f} p90 {np.percentile(e[:,0],90):.2f}; mm med {np.median(e[:,1]):.2f} p90 {np.percentile(e[:,1],90):.2f}', flush=True)
r = np.array([(a[3], a[4]) for a in rows])
print(f'LOBO all ep {ep} (block {BL}): n {len(r)} px med {np.median(r[:,0]):.2f} p90 {np.percentile(r[:,0],90):.2f}; mm med {np.median(r[:,1]):.2f} p90 {np.percentile(r[:,1],90):.2f}')
json.dump(rows, open(f'out/lobo_{ep}_{BL}.json', 'w'))
