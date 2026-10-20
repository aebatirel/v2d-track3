"""Stage C marker tracker prototype (DIG 17). INFERENCE PART: reads no GT except the optional simulated coarse init (INIT=gt,
see below), which is the only GT touch and is clearly separated (init_pose()).
Cameras: stereo VO of the mono pair (out/vo_public_<ep>.npy, pose of cam b in the b@f0 frame) + video-only cam-a sync
(out/sync_<ep>.json: delta, extrinsic rotation correction). World = VO frame (b@f0).
Per frame t (b/c clock), per object: predict pose (constant velocity), predict visible markers (z-buffer of all tracked
objects' scan surfaces under the predicted poses), HoughCircles in a crop around the predicted markers (det17run settings),
score candidates with the LOEO v2 classifier (c/clf_<ep>.pkl, target ep never in training), associate (nearest within
shrinking gates, exclusive), robust multi-camera reprojection fit (cams a/b/c) with a pose prior; accept / coast.
v2 (stage C): hypothesis-and-verify association (prior + one translation-shift hypothesis per candidate/marker pair, scored
by matched candidates in a medium gate), velocity only from full fixes, no 1-marker pose updates, velocity decay while
coasting, 2-marker acquisition only with >= 4 views and a prior-consistent fit. PRIOR=gt (analysis only, hybrid emulation):
the per-frame prior is GT(t-0.5) mapped into the VO frame with an AR(1) error (PN = sigma_mm,sigma_deg,rho), standing in for a
model-based tracker's output; the marker fit then corrects it. v1 is frozen as c/trk17_v1_frozen.py.
usage: [PRIOR=self|gt] [PN=10,5,0.95] [INIT=gt] [THR=0.05] [SEED=0] [IP=20,5] c/trk17.py ep [t_end] -> c/trk_<ep><TAG>.npz"""
import sys, os, json, time, pickle, numpy as np, cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D
cv2.setNumThreads(2)
ep = int(sys.argv[1]); VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO)
TEND = int(sys.argv[2]) if len(sys.argv) > 2 else T
THR = float(os.environ.get('THR', 0.05)); TAG = os.environ.get('TAG', ''); INIT = os.environ.get('INIT', 'gt')
IP = [float(x) for x in os.environ.get('IP', '20,5').split(',')]       # simulated coarse init error: mm, deg
USE = os.environ.get('CAMS', 'abc'); PRIOR = os.environ.get('PRIOR', 'self'); PN = [float(x) for x in os.environ.get('PN', '10,5,0.95').split(',')]
sy = json.load(open(f'out/sync_{ep}.json')); DELTA = sy['delta']; KA = int(round(DELTA))
Tba = L.ext('a').copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]; Tbc = L.ext('c')
CLF = pickle.load(open(f'c/clf_{ep}.pkl', 'rb'))   # our own sklearn models written by c/train_loeo.py (local, trusted)
FA = L.cam('a')[0][0, 0]; SC = {c: FA / L.cam(c)[0][0, 0] for c in 'abc'}     # a-equivalent px scale
SIG = {'a': 1.5, 'b': 0.75, 'c': 0.75}                                       # own-px measurement sigma
sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo_at(tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(np.floor(tau)), T - 2); f = tau - i
    M = np.eye(4); M[:3, :3] = sl([tau]).as_matrix()[0]; M[:3, 3] = (1 - f) * VO[i, :3, 3] + f * VO[i + 1, :3, 3]; return M
def cam_pose(t, c):
    """camera c pose (R cols = cam axes in world, C) used with the b/c-clock state time t; cam a uses its frame t+KA."""
    if c == 'a': P = vo_at(t + KA - DELTA) @ Tba
    elif c == 'b': P = VO[t]
    else: P = VO[t] @ Tbc
    return P[:3, :3], P[:3, 3]
names = L.load_gt(ep)['names']                         # object names only (the video's object list is given at eval time)
OBJ = [n for n in names if n in L.CAT and len(L.CAT[n]) >= 3]
MK = {n: np.array([q['c'] for q in L.CAT[n]]) for n in OBJ}; MR = {n: np.array([q['r'] for q in L.CAT[n]]) for n in OBJ}
CALM = os.environ.get('CAL', '')     # '' scan catalogue | 'loeo' calibrated on OTHER public eps (c/calib_<e>.json) | 'self' in-sample (upper bound)
if CALM:
    import glob
    for n in OBJ:
        acc = {}
        for fn in glob.glob('c/calib_*.json'):
            e = int(fn.split('_')[-1].split('.')[0])
            if (CALM == 'loeo' and e == ep) or (CALM == 'self' and e != ep): continue
            for k, q in enumerate(json.load(open(fn)).get(n, [])):
                if q and q['n'] >= 20 and q['res_after'] < 4.0: acc.setdefault(k, []).append((np.array(q['X']), q['n']))
        for k, v in acc.items(): MK[n][k] = sum(x * w for x, w in v) / sum(w for _, w in v)
        print('CAL', CALM, n, 'calibrated markers', sorted(acc), flush=True)
if os.environ.get('LARGE', '0') == '1':      # drop small markers (r < 5 mm)
    for n in OBJ:
        keep = MR[n] >= 0.005
        if keep.sum() >= 3: MK[n], MR[n] = MK[n][keep], MR[n][keep]
SURF = {n: L.surf(n)[::4] for n in OBJ}
vids = {c: L.Video(ep, c) for c in 'abc'}
def hough(G, c, rmin, rmax):
    up = 1 if c == 'a' else 2
    g = cv2.resize(G, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC) if up != 1 else G
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    cs = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=3, param1=40, param2=0.5,
                          minRadius=max(int(rmin * up), 5 if c == 'a' else 6), maxRadius=min(int(np.ceil(rmax * up)) + 1, 40))
    if cs is None: return np.zeros((0, 3))
    cs = cs[0].astype(float); cs[:, :2] = (cs[:, :2] + 0.5) / up - 0.5; cs[:, 2] /= up; return cs
def proj(X, R, C, c):
    uv, z = L.project(X, R, C, c, own=True); return uv, z
def zbuffer(poses, R, C, c, step=2):
    K, d, (W, H) = L.cam(c); w, h = W // step, H // step; zb = np.full((h, w), np.inf, np.float32)
    for n, (Ro, to) in poses.items():
        uv, z = proj(SURF[n] @ Ro.T + to, R, C, c); ok = z > 0.05
        u = (uv[ok, 0] / step).astype(int); v = (uv[ok, 1] / step).astype(int); z = z[ok]; k = (u >= 0) & (u < w) & (v >= 0) & (v < h)
        np.minimum.at(zb, (v[k], u[k]), z[k])
    return cv2.erode(np.where(np.isfinite(zb), zb, 1e3).astype(np.float32), np.ones((3, 3), np.uint8))
def vis_markers(n, Ro, to, R, C, c, zb, step=2, tol=0.004):
    K, d, (W, H) = L.cam(c); X = MK[n] @ Ro.T + to; uv, z = proj(X, R, C, c); rp = K[0, 0] * MR[n] / np.maximum(z, 1e-3)
    vis = np.zeros(len(X), bool); ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    for k in range(len(X)):
        if not (z[k] > 0.05) or not (rp[k] < uv[k, 0] < W - rp[k] and rp[k] < uv[k, 1] < H - rp[k]): continue
        pts = [(uv[k, 0], uv[k, 1])] + [(uv[k, 0] + 0.7 * rp[k] * np.cos(a), uv[k, 1] + 0.7 * rp[k] * np.sin(a)) for a in ang]
        ok = [z[k] - MR[n][k] <= zb[int(v / step), int(u / step)] + tol for u, v in pts if 0 <= u < W and 0 <= v < H]
        vis[k] = np.mean(ok) >= 0.34 if ok else False
    return uv, z, rp, vis
def detect(G, BGR, c, uv, rp, vis, win):
    """candidates (x, y, r, score) near the predicted visible markers; one crop per object and camera."""
    if not vis.any(): return np.zeros((0, 4))
    H_, W_ = G.shape; m = 2.5 * rp[vis].max() + win + 6
    x0, y0 = int(max(uv[vis, 0].min() - m, 0)), int(max(uv[vis, 1].min() - m, 0))
    x1, y1 = int(min(uv[vis, 0].max() + m, W_)), int(min(uv[vis, 1].max() + m, H_))
    if x1 - x0 < 12 or y1 - y0 < 12: return np.zeros((0, 4))
    cs = hough(G[y0:y1, x0:x1], c, 0.6 * rp[vis].min(), 1.6 * rp[vis].max())
    if len(cs) == 0: return np.zeros((0, 4))
    near = np.zeros(len(cs), bool)
    for k in np.flatnonzero(vis):
        near |= (np.hypot(cs[:, 0] + x0 - uv[k, 0], cs[:, 1] + y0 - uv[k, 1]) <= win) & (cs[:, 2] / rp[k] > 0.6) & (cs[:, 2] / rp[k] < 1.6)
    cs = cs[near]
    if len(cs) == 0: return np.zeros((0, 4))
    P = D.prep_image(G[y0:y1, x0:x1], BGR[y0:y1, x0:x1] if c == 'a' else None)
    F = D.features2(P, cs.astype(np.float64)).astype(np.float16).astype(np.float32)
    s = CLF['a' if c == 'a' else 'bc'].predict_proba(F)[:, 1]
    out = np.c_[cs[:, 0] + x0, cs[:, 1] + y0, cs[:, 2], s]; return out[out[:, 3] >= THR]
def pose_mat(x): return Rot.from_rotvec(x[:3]).as_matrix(), x[3:6]
def advance(R, t, v, w, dt):
    return Rot.from_rotvec(w * dt).as_matrix() @ R, t + v * dt
def solve(n, R0, t0, obs, cams, v, w, sig_t, sig_r):
    """obs: list of (c, k, u, v_). Pose prior (R0, t0) with sigmas (m, rad). Cauchy loss in sigma units."""
    x0 = np.r_[Rot.from_matrix(R0).as_rotvec(), t0]
    def res(x):
        R, t = pose_mat(x); out = []
        for (c, k, u, vv) in obs:
            Rc, tc = (advance(R, t, v, w, KA - DELTA)) if c == 'a' else (R, t)    # cam-a exposure offset (b/c clock)
            uv, _ = proj((MK[n][k] @ Rc.T + tc)[None], *cams[c], c); out += [(uv[0, 0] - u) / SIG[c], (uv[0, 1] - vv) / SIG[c]]
        out += list(Rot.from_matrix(R0.T @ R).as_rotvec() / sig_r) + list((t - t0) / sig_t)
        return np.array(out)
    r = least_squares(res, x0, loss='cauchy', f_scale=2.0, method='trf', max_nfev=60)
    R, t = pose_mat(r.x); return R, t, r.fun[:2 * len(obs)].reshape(-1, 2)
# ---------------- initial pose: the ONLY GT access in this script (simulated coarse model-based init) ----------------
def init_pose(n):
    gt = L.load_gt(ep); j = gt['names'].index(n); Treg = np.array(json.load(open(f'out/reg2_{ep}.json'))['Treg'])
    Rm, tm = D.gt_interp(gt, j, 0.0); Ti = np.linalg.inv(Treg); R = Ti[:3, :3] @ Rm; t = Ti[:3, :3] @ tm + Ti[:3, 3]
    rng = np.random.default_rng(int(os.environ.get('SEED', 0)) * 100 + OBJ.index(n))
    a = rng.normal(size=3); a *= np.radians(IP[1]) / np.linalg.norm(a); e = rng.normal(size=3); e *= IP[0] / 1000 / np.linalg.norm(e)
    return Rot.from_rotvec(a).as_matrix() @ R, t + e
_GT = None
def gt_prior_seq(n, T_):
    """hybrid emulation (analysis only): GT(t-0.5) in the VO frame (Treg) with an AR(1) pose error (world axes)."""
    global _GT
    if _GT is None: _GT = (L.load_gt(ep), np.linalg.inv(np.array(json.load(open(f'out/reg2_{ep}.json'))['Treg'])))
    gt, Ti = _GT; j = gt['names'].index(n); rng = np.random.default_rng(int(os.environ.get('SEED', 0)) * 1000 + 7 + OBJ.index(n))
    st_, sr_, rho = PN[0] / 1000, np.radians(PN[1]), PN[2]; e = np.r_[rng.normal(size=3) * st_, rng.normal(size=3) * sr_]; out = []
    for t in range(T_):
        if t: e = rho * e + np.sqrt(1 - rho ** 2) * np.r_[rng.normal(size=3) * st_, rng.normal(size=3) * sr_]
        Rm, tm = D.gt_interp(gt, j, t - 0.5); R = Ti[:3, :3] @ Rm; tt = Ti[:3, :3] @ tm + Ti[:3, 3]
        out.append((Rot.from_rotvec(e[3:]).as_matrix() @ R, tt + e[:3]))
    return out
def shift_hyp(c, cams, X, u, v):
    """translation that moves world point X onto pixel (u, v) of camera c at X's depth."""
    R, C = cams[c]; K, d, _ = L.cam(c); Xc = (X - C) @ R
    q = cv2.undistortPoints(np.array([[[u, v]]], np.float64), K, d).reshape(2); Xn = np.r_[q, 1.0] * Xc[2]
    return R @ (Xn - Xc)
# ---------------- tracking loop ----------------
st = {n: dict(R=None, t=None, v=np.zeros(3), w=np.zeros(3), coast=0, dt_last=0.0, dr_last=0.0) for n in OBJ}
GTP = {}
for n in OBJ:
    if PRIOR == 'gt': GTP[n] = gt_prior_seq(n, T); st[n]['R'], st[n]['t'] = GTP[n][0]
    else: st[n]['R'], st[n]['t'] = init_pose(n); st[n]['coast'] = 6     # start in acquisition mode (wide gates)
OBSLOG = []
RES = {n: dict(R=np.zeros((T, 3, 3)), t=np.zeros((T, 3)), nm=np.zeros(T, int), nobs=np.zeros(T, int), status=np.zeros(T, int),
               med=np.full(T, np.nan), ids=np.zeros((T, 3, 8), bool), Rp=np.zeros((T, 3, 3)), tp=np.zeros((T, 3)), ndet=np.zeros((T, 3), int), npred=np.zeros((T, 3), int)) for n in OBJ}
tim = []; t0w = time.time()
for t in range(min(T, TEND)):
    ts = time.time()
    cams = {c: cam_pose(t, c) for c in 'abc'}
    img = {}
    for c in USE:
        fr = t + KA if c == 'a' else t
        BGR = vids[c].get(min(fr, T - 1)) if fr < T else None
        img[c] = (cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY), BGR) if BGR is not None else None
    pred = {}
    for n in OBJ:
        s = st[n]; pred[n] = GTP[n][t] if PRIOR == 'gt' else (advance(s['R'], s['t'], s['v'], s['w'], 1.0) if s['coast'] < 6 else (s['R'], s['t']))
    zbs = {c: zbuffer(pred, *cams[c], c) for c in USE if img.get(c) is not None}
    for n in OBJ:
        s = st[n]; Rp, tp = pred[n]
        # gate (a-eq px) and prior sigma grow with speed and coasting
        spd_t, spd_r = s['dt_last'], s['dr_last']
        win = min(8 + 0.6 * FA * spd_t / 0.5 + 0.3 * FA * spd_r / 2.0 + 12 * s['coast'], 90)
        sig_t = 0.004 + 0.5 * spd_t + 0.01 * s['coast']; sig_r = np.radians(1.5) + 0.5 * spd_r + np.radians(4) * s['coast']
        if PRIOR == 'gt':
            sig_t, sig_r = PN[0] / 1000 * 1.5, np.radians(PN[1]) * 1.5; win = min(3 * FA * (PN[0] / 1000 + 0.08 * np.radians(PN[1])) / 0.5, 120)
        cand = {}
        for ci, c in enumerate('abc'):
            if c not in zbs: continue
            Rc, tc = advance(Rp, tp, s['v'], s['w'], KA - DELTA) if c == 'a' else (Rp, tp)
            uv, z, rp, vis = vis_markers(n, Rc, tc, *cams[c], c, zbs[c]); RES[n]['npred'][t, ci] = vis.sum()
            ww = win / SC[c]; det = detect(img[c][0], img[c][1], c, uv, rp, vis, ww); RES[n]['ndet'][t, ci] = len(det)
            cand[c] = (uv, rp, vis, det, ww)
        # hypothesis-and-verify: prior + translation shifts that put marker k on candidate i; score = matched candidate scores
        def hscore(Rh, th, gate_a):
            tot, nk = 0.0, set()
            for c, (uv0, rp, vis, det, ww) in cand.items():
                if len(det) == 0: continue
                Rc, tc = advance(Rh, th, s['v'], s['w'], KA - DELTA) if c == 'a' else (Rh, th)
                uv, _ = proj(MK[n] @ Rc.T + tc, *cams[c], c); used = set()
                for k in np.flatnonzero(vis):
                    d = np.hypot(det[:, 0] - uv[k, 0], det[:, 1] - uv[k, 1]); ok = np.flatnonzero(d <= gate_a / SC[c])
                    ok = [i for i in ok if i not in used]
                    if ok: i = max(ok, key=lambda i: det[i, 3]); used.add(i); tot += 0.5 + det[i, 3]; nk.add(k)
            return tot + 0.5 * len(nk)
        best = (hscore(Rp, tp, max(6.0, 0.25 * win)), tp)
        for c, (uv0, rp, vis, det, ww) in cand.items():
            Rc, tc = advance(Rp, tp, s['v'], s['w'], KA - DELTA) if c == 'a' else (Rp, tp)
            for k in np.flatnonzero(vis):
                for i in range(len(det)):
                    if np.hypot(det[i, 0] - uv0[k, 0], det[i, 1] - uv0[k, 1]) > ww: continue
                    th = tp + shift_hyp(c, cams, MK[n][k] @ Rc.T + tc, det[i, 0], det[i, 1])
                    if np.linalg.norm(th - tp) > 3 * sig_t + 0.08 * 3 * sig_r: continue
                    sc_ = hscore(Rp, th, max(6.0, 0.25 * win)) - 0.5 * np.sum(((th - tp) / sig_t) ** 2) / 9
                    if sc_ > best[0]: best = (sc_, th)
        # association + solve, shrinking gates (starting from the best hypothesis)
        R, tt = Rp, best[1]; obs = []
        for g in (0.5, 0.3, 0.2):
            obs = []
            for c, (uv0, rp, vis, det, ww) in cand.items():
                if len(det) == 0: continue
                Rc, tc = advance(R, tt, s['v'], s['w'], KA - DELTA) if c == 'a' else (R, tt)
                uv, _ = proj(MK[n] @ Rc.T + tc, *cams[c], c); gate = max(ww * g, 3.0 / SC[c] if c == 'a' else 2.0)
                pairs = []
                for k in np.flatnonzero(vis):
                    d = np.hypot(det[:, 0] - uv[k, 0], det[:, 1] - uv[k, 1]); rr = det[:, 2] / rp[k]
                    for i in np.flatnonzero((d <= gate) & (rr > 0.6) & (rr < 1.6)): pairs.append((d[i] - 2 * gate * det[i, 3] * 0.25, k, i))
                used_k, used_i = set(), set()
                for _, k, i in sorted(pairs):
                    if k in used_k or i in used_i: continue
                    used_k.add(k); used_i.add(i); obs.append((c, k, det[i, 0], det[i, 1]))
            if len(obs) == 0: break
            nd = len({k for (_, k, _, _) in obs})
            R, tt, rr_ = solve(n, Rp, tp, obs, cams, s['v'], s['w'], sig_t if nd >= 3 else sig_t * 0.5, sig_r if nd >= 3 else sig_r * 0.5)
        # final inlier set
        nm = 0; med = np.nan
        if obs:
            e = np.hypot(rr_[:, 0], rr_[:, 1]); inl = e < 4.0; obs = [o for o, q in zip(obs, inl) if q]
            if obs:
                R, tt, rr_ = solve(n, Rp, tp, obs, cams, s['v'], s['w'], sig_t if len({o[1] for o in obs}) >= 3 else sig_t * 0.5, sig_r)
                e = np.hypot(rr_[:, 0], rr_[:, 1]); med = float(np.median(e) * np.mean([SIG[o[0]] * SC[o[0]] for o in obs]))
                nm = len({o[1] for o in obs})
                for (c, k, _, _) in obs: RES[n]['ids'][t, 'abc'.index(c), k] = True
        # accept rules: >=3 distinct markers -> full fix; 2 -> fix with prior; 1 -> translation nudge only if not coasting long
        status = 0
        if nm >= 1:   # prior consistency (Mahalanobis of the fitted pose vs the prior)
            mah = np.sqrt(np.sum(((tt - tp) / sig_t) ** 2) + np.sum((Rot.from_matrix(Rp.T @ R).as_rotvec() / sig_r) ** 2))
        if nm >= 3: status = 3
        elif nm == 2 and (s['coast'] < 6 or len(obs) >= 4) and mah < 4.5: status = 2   # acquisition: 2 markers need >= 4 views
        elif nm == 1: status = 1                                                           # recorded, no pose update
        if status <= 1:
            R, tt = pred[n]; s['coast'] += 1; s['v'] *= 0.8; s['w'] *= 0.8
        else:
            if status == 3 and s['coast'] == 0 and PRIOR != 'gt':
                dtv = (tt - s['t']); dw = Rot.from_matrix(R @ s['R'].T).as_rotvec(); a_ = 0.6
                s['v'] = (1 - a_) * s['v'] + a_ * np.clip(dtv, -0.05, 0.05); s['w'] = (1 - a_) * s['w'] + a_ * np.clip(dw, -0.15, 0.15)
            elif s['coast'] >= 6: s['v'], s['w'] = np.zeros(3), np.zeros(3)          # re-acquired: restart the motion model
            s['coast'] = 0
        s['dt_last'] = float(np.linalg.norm(s['v'])); s['dr_last'] = float(np.linalg.norm(s['w']))
        if s['coast'] >= 6: s['v'] *= 0.0; s['w'] *= 0.0
        for (c, k, u_, v_) in obs: OBSLOG.append((t, OBJ.index(n), 'abc'.index(c), k, u_, v_, status))
        s['R'], s['t'] = R, tt
        q = RES[n]; q['Rp'][t], q['tp'][t] = pred[n]; q['R'][t], q['t'][t], q['nm'][t], q['nobs'][t], q['status'][t], q['med'][t] = R, tt, nm, len(obs), status, med
    tim.append(time.time() - ts)
    if t % 20 == 0: print(f'ep {ep} t {t} ' + ' '.join(f'{n[:8]} st{RES[n]["status"][t]} nm{RES[n]["nm"][t]} c{st[n]["coast"]}' for n in OBJ) + f' {np.mean(tim):.2f}s/fr {time.time()-t0w:.0f}s', flush=True)
np.savez_compressed(f'c/trk_{ep}{TAG}.npz', objs=np.array(OBJ), obslog=np.array(OBSLOG, np.float64).reshape(-1, 7), PRIOR=PRIOR, PN=PN, T=min(T, TEND), tim=np.array(tim), THR=THR, INIT=INIT, IP=IP, DELTA=DELTA, KA=KA,
                    **{f'{k}_{i}': v for i, n in enumerate(OBJ) for k, v in RES[n].items()})
print('done', f'{np.mean(tim):.2f}s/frame', f'{time.time()-t0w:.0f}s')
