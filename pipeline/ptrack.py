"""Model-free point-track second opinion for perc2 object tracks (point-track session, 2 Nov 2026).

Inference only: reads the rectified-left video, our cached FoundationStereo depth and perc2's outputs (poses.npz:
world_T_cam, cam_T_<obj>; det_f0.npz: the frame-0 masks perc2 chose). Never reads mocap / the parquet `pose` field
(the parquet is not opened here at all; object names come from det_f0.npz, which perc2 took from the slot order).

Per object:
  1. seed 2-D points inside perc2's frame-0 mask (eroded), track them through the video (TRACKER=klt: OpenCV pyramidal
     Lucas-Kanade frame to frame with a forward-backward check);
  2. lift each point with the cached metric stereo depth (3x3 median, edge points rejected) into the camera frame, then
     to world with perc2's world_T_cam;
  3. robust rigid fit (RANSAC + trimmed Kabsch) of the points' object-frame coordinates to their world positions
     -> T_pt(t) (world_T_obj; object frame = perc2's frame-0 pose, so T_pt(0) = FoundationPose's frame-0 pose);
     points that stay outliers are dropped; new points are seeded inside the hull of the current inliers when fewer
     than RESEED_FRAC of the seeded points remain, gated to the inliers' object-frame bounding box;
  4. detector: over a window of W frames, compare the point-track motion with FoundationPose's motion;
       e(t) = mean over the object's tracked points x of || T_pt(t) T_pt(t-W)^-1 P_out(t-W) x - P_fp(t) x ||
     flagged when e(t) > E_FLAG for >= N_FLAG consecutive frames with a valid fit;
       'lag' type: the points moved more than FoundationPose over the window (m_pt > m_fp + LAG_MARGIN): a frozen /
       lost FoundationPose track;  'jump' type: otherwise (FoundationPose moved, points did not);
  5. repair (REPAIR=lag|all|none): from the anchor a = onset - W the output follows the point motion,
       P_out(t) = T_pt(t) T_pt(a)^-1 P_out(a)   (continuous at a by construction),
     until FoundationPose agrees again (e < E_BACK for N_BACK frames), then a RAMP-frame blend back to FoundationPose.
     If the fit is invalid during a repair, the last repaired pose is held in world.
Outputs in OUT: poses_world_vo.npz (repaired world poses per object; for pipeline/score_registered.py),
ptrack.json (spans, counts, settings), ptrack_traj.npz (T_pt, e, inliers per frame).
Env / args: see argparse. CPU only.
"""
import argparse, json, os, time
import numpy as np, cv2
from scipy.spatial.transform import Rotation as Rot, Slerp

p = argparse.ArgumentParser()
p.add_argument('ep', type=int)
p.add_argument('--run', required=True, help='perc2 output dir of this episode (poses.npz, det_f0.npz)')
p.add_argument('--depth', required=True, help='depths_fs0.5.npy of this episode (rectified-left, metres)')
p.add_argument('--t3', default='/content/t3')
p.add_argument('--out', required=True)
p.add_argument('--repair', default='lag', choices=['lag', 'all', 'none'])
p.add_argument('--W', type=int, default=15)
p.add_argument('--e_flag', type=float, default=0.02)
p.add_argument('--n_flag', type=int, default=5)
p.add_argument('--e_back', type=float, default=0.01)
p.add_argument('--n_back', type=int, default=5)
p.add_argument('--lag_margin', type=float, default=0.01)
p.add_argument('--ramp', type=int, default=10)
p.add_argument('--restart', type=int, default=10)
p.add_argument('--min_inl', type=int, default=12)
p.add_argument('--max_pts', type=int, default=300)
p.add_argument('--reseed_frac', type=float, default=0.6)
p.add_argument('--ransac_thr', type=float, default=0.01)
p.add_argument('--tracks', default=None, help='npz of external 2-D tracks from f0 queries: q_<obj> (Q,2 x,y at f0), uv_<obj> (Q,T,2), vis_<obj> (Q,T)')
p.add_argument('--mask', default='render', choices=['render', 'det'])
p.add_argument('--lib', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'meshes', 'library_v3'))
p.add_argument('--max_frames', type=int, default=0, help='debug: stop after this many frames')
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
t_all = time.time()
def log(*x): print(f'[{time.time() - t_all:7.1f}s]', *x, flush=True)

# ---------- rectification (same as pipeline/perc2.py) ----------
C = json.load(open(f'{a.t3}/calib.json')); cam = C['cameras']
sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
SZ, RSZ = (1280, 800), (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R, T, alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
KR = P1[:3, :3].copy(); fx, cx, cy = KR[0, 0], KR[0, 2], KR[1, 2]

P = np.load(f'{a.run}/poses.npz'); W_C = P['world_T_cam']
det = np.load(f'{a.run}/det_f0.npz')
names = [str(n) for n in det['names']]
N = len(W_C)
if a.max_frames: N = min(N, a.max_frames)
cap = cv2.VideoCapture(f'{a.t3}/v/ep{a.ep}_c.mp4'); rc = []
while len(rc) < N:
    ok, f = cap.read()
    if not ok: break
    rc.append(cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR))
N = min(N, len(rc))
DEP = np.load(a.depth, mmap_mode='r')
assert DEP.shape[1:] == (RSZ[1], RSZ[0]), DEP.shape
log('ep', a.ep, 'objects', names, 'frames', N)

# frame-0 masks perc2 chose (half resolution, packed)
ms = tuple(det['mask_shape']); allm = np.unpackbits(det['masks'], axis=-1)[..., :ms[2]].astype(bool)
chosen = det['chosen']
GUARD = json.load(open(f'{a.run}/track_guard.json')) if os.path.exists(f'{a.run}/track_guard.json') else {}
P_fp = {n: np.stack([W_C[t] @ P[f'cam_T_{n}'][t] for t in range(N)]) for n in names}

# visible-surface masks rendered from the tracking templates (perc2's MESH_DIR) at a pose: a point splat z-buffer over
# all objects at half resolution, kept where it agrees with our depth (2 cm; hands and other occluders drop out).
# MASK=det uses perc2's frame-0 detection masks instead (ep0 showed the lid's mask on the pot handle).
import trimesh
SURF = {n: np.asarray(trimesh.sample.sample_surface(trimesh.load(f'{a.lib}/{n}.glb', force='mesh'), 60000, seed=0)[0]) for n in names}
def render_masks(t, poses_w):
    H2, W2 = RSZ[1] // 2, RSZ[0] // 2; zb = np.full(H2 * W2, np.inf); lab = np.full(H2 * W2, -1)
    cam_T_w = np.linalg.inv(W_C[t])
    for i, n in enumerate(names):
        M = cam_T_w @ poses_w[n]; X = SURF[n] @ M[:3, :3].T + M[:3, 3]; X = X[X[:, 2] > 0.1]
        u = np.round((X[:, 0] * fx / X[:, 2] + cx) / 2).astype(int); v = np.round((X[:, 1] * fx / X[:, 2] + cy) / 2).astype(int)
        ok = (u >= 0) & (u < W2) & (v >= 0) & (v < H2); idx = v[ok] * W2 + u[ok]; z = X[ok, 2]
        order = np.argsort(-z); idx, z = idx[order], z[order]            # nearest last -> wins the assignment
        better = z < zb[idx]; zb[idx[better]] = z[better]; lab[idx[better]] = i
    zb, lab = zb.reshape(H2, W2), lab.reshape(H2, W2)
    dep = np.asarray(DEP[t][::2, ::2])
    out = {}
    for i, n in enumerate(names):
        m = (lab == i).astype(np.uint8); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        zf = cv2.morphologyEx(np.where(lab == i, zb, 0).astype(np.float32), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        m &= (dep > 0) & (np.abs(dep - zf) < 0.02)
        out[n] = cv2.resize(m.astype(np.uint8), RSZ, interpolation=cv2.INTER_NEAREST).astype(bool)
    return out
if a.mask == 'render':
    MASK0 = render_masks(0, {n: P_fp[n][0] for n in names})
else:
    MASK0 = {n: cv2.resize((allm[chosen[i]] if chosen[i] >= 0 else np.zeros(ms[1:], bool)).astype(np.uint8), RSZ,
                           interpolation=cv2.INTER_NEAREST).astype(bool) for i, n in enumerate(names)}
log('f0 mask pixels', {n: int(m.sum()) for n, m in MASK0.items()})

def lift(t, uv):
    """3x3-median depth at the points; NaN where invalid or at a depth edge (3x3 spread > 2 cm)."""
    d = DEP[t]; u = np.round(uv[:, 0]).astype(int); v = np.round(uv[:, 1]).astype(int)
    ok = (u >= 1) & (u < RSZ[0] - 1) & (v >= 1) & (v < RSZ[1] - 1)
    X = np.full((len(uv), 3), np.nan)
    if not ok.any(): return X
    uu, vv = u[ok], v[ok]
    patch = np.stack([d[vv + dy, uu + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)], 1).astype(float)
    patch[patch <= 0] = np.nan
    with np.errstate(all='ignore'):
        z = np.nanmedian(patch, 1); spread = np.nanmax(patch, 1) - np.nanmin(patch, 1)
        nval = np.isfinite(patch).sum(1)
    good = np.isfinite(z) & (spread < 0.02) & (nval >= 6)
    zc = np.where(good, z, np.nan)
    Xc = np.stack([(uv[ok, 0] - cx) * zc / fx, (uv[ok, 1] - cy) * zc / fx, zc], 1)
    Xw = Xc @ W_C[t][:3, :3].T + W_C[t][:3, 3]
    X[ok] = Xw
    return X

def kabsch(A, B, w=None):
    """R, t minimising sum w || R A + t - B ||^2."""
    w = np.ones(len(A)) if w is None else w
    ca, cb = (w[:, None] * A).sum(0) / w.sum(), (w[:, None] * B).sum(0) / w.sum()
    H = ((A - ca) * w[:, None]).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H); d = np.sign(np.linalg.det(Vt.T @ U.T))
    Rm = Vt.T @ np.diag([1, 1, d]) @ U.T
    M = np.eye(4); M[:3, :3] = Rm; M[:3, 3] = cb - Rm @ ca
    return M

RNG = np.random.default_rng(0)
def robust_fit(A, B, prior):
    """RANSAC (3-point Kabsch, the prior pose as one extra hypothesis) + trimmed refit. Returns M, inlier mask."""
    n = len(A)
    if n < a.min_inl: return None, np.zeros(n, bool)
    hyps = [prior]
    for _ in range(150):
        idx = RNG.choice(n, 3, replace=False)
        if np.linalg.matrix_rank(A[idx] - A[idx].mean(0), tol=1e-3) < 2: continue
        hyps.append(kabsch(A[idx], B[idx]))
    best, bi = None, None
    for M in hyps:
        r = np.linalg.norm(A @ M[:3, :3].T + M[:3, 3] - B, axis=1); inl = r < a.ransac_thr
        if best is None or inl.sum() > bi.sum(): best, bi = M, inl
    if bi.sum() < max(a.min_inl, 0.2 * n): return None, bi
    for _ in range(3):
        M = kabsch(A[bi], B[bi]); r = np.linalg.norm(A @ M[:3, :3].T + M[:3, 3] - B, axis=1)
        bi = r < min(a.ransac_thr, max(0.004, 2.5 * np.median(r[bi])))
        if bi.sum() < a.min_inl: return None, bi
    return kabsch(A[bi], B[bi]), bi

LK = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
def seed(t, mask, k):
    """Up to k good-feature points in the mask (eroded 5 px)."""
    m = cv2.erode(mask.astype(np.uint8) * 255, np.ones((11, 11), np.uint8))
    if m.sum() == 0: return np.zeros((0, 2), np.float32)
    pts = cv2.goodFeaturesToTrack(rc[t], maxCorners=k, qualityLevel=0.001, minDistance=4, mask=m, blockSize=7)
    pts = np.zeros((0, 2), np.float32) if pts is None else pts[:, 0].astype(np.float32)
    if len(pts) < k:                                               # weak texture (light wood, white pot): add a grid
        v, u = np.nonzero(m[::8, ::8]); g = np.stack([u * 8, v * 8], 1).astype(np.float32)
        if len(pts) and len(g):
            g = g[np.min(np.linalg.norm(g[:, None] - pts[None], axis=2), 1) > 4]
        if len(g) > k - len(pts): g = g[RNG.choice(len(g), k - len(pts), replace=False)]
        pts = np.vstack([pts, g]).astype(np.float32)
    return pts

def angle_deg(R_):
    return float(np.degrees(np.arccos(np.clip((np.trace(R_) - 1) / 2, -1, 1))))

def track_object_ext(n):
    """External tracks (e.g. BootsTAPIR, f0 queries): per-frame robust fit of the visible points; no re-seeding."""
    TR = np.load(a.tracks); q, UV, VIS = TR[f'q_{n}'], TR[f'uv_{n}'], TR[f'vis_{n}']
    Tpt = np.full((N, 4, 4), np.nan); Tpt[0] = P_fp[n][0]
    X0 = lift(0, q); ok0 = np.isfinite(X0).all(1)
    inv0 = np.linalg.inv(Tpt[0]); Xo = np.full_like(X0, np.nan); Xo[ok0] = X0[ok0] @ inv0[:3, :3].T + inv0[:3, 3]
    ninl = np.zeros(N, int); ninl[0] = int(ok0.sum()); last = Tpt[0]
    for t in range(1, N):
        X = lift(t, UV[:, t]); fin = np.isfinite(X).all(1) & ok0 & VIS[:, t]
        if fin.sum() < a.min_inl: continue
        M, inl = robust_fit(Xo[fin], X[fin], last)
        if M is not None:
            Tpt[t] = M; last = M; ninl[t] = int(inl.sum())
    return Tpt, ninl, np.zeros(N, int), {}

def track_object(n):
    """KLT point tracks of one object -> T_pt (world_T_obj per frame, NaN where invalid), inliers, object-frame points."""
    Tpt = np.full((N, 4, 4), np.nan); Tpt[0] = P_fp[n][0]
    uv = seed(0, MASK0[n], a.max_pts)
    Xw = lift(0, uv); keep = np.isfinite(Xw).all(1); uv, Xw = uv[keep], Xw[keep]
    inv0 = np.linalg.inv(Tpt[0]); Xo = Xw @ inv0[:3, :3].T + inv0[:3, 3]
    bad = np.zeros(len(uv), int); n_seed = max(len(uv), 1)
    ninl = np.zeros(N, int); ninl[0] = len(uv); reseeds = 0
    last = Tpt[0]; seg = np.zeros(N, int); lost = 0; restarts = 0
    for t in range(1, N):
        seg[t] = seg[t - 1]
        if lost >= a.restart:
            # lost for RESTART frames: restart from FoundationPose's pose (seeds only where its render agrees with
            # our depth, so a wrong FoundationPose pose seeds nothing); a new segment (no motion compared across it)
            m0 = render_masks(t, {o: P_fp[o][t] for o in names})[n]
            uv0 = seed(t, m0, a.max_pts); X0 = lift(t, uv0); k0 = np.isfinite(X0).all(1)
            if k0.sum() >= a.min_inl:
                inv_ = np.linalg.inv(P_fp[n][t]); uv = uv0[k0]; Xo = X0[k0] @ inv_[:3, :3].T + inv_[:3, 3]
                bad = np.zeros(len(uv), int); n_seed = len(uv); Tpt[t] = P_fp[n][t]; last = Tpt[t]; ninl[t] = len(uv)
                seg[t] += 1; lost = 0; restarts += 1
                continue
        if len(uv):
            p1, st, _ = cv2.calcOpticalFlowPyrLK(rc[t - 1], rc[t], uv.reshape(-1, 1, 2), None, **LK)
            p0, st2, _ = cv2.calcOpticalFlowPyrLK(rc[t], rc[t - 1], p1, None, **LK)
            fb = np.linalg.norm(p0[:, 0] - uv, axis=1)
            ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (fb < 1.0)
            uv, Xo, bad = p1[ok, 0], Xo[ok], bad[ok]
        X = lift(t, uv); fin = np.isfinite(X).all(1)
        if os.environ.get('PT_DEBUG'): log(n, t, 'alive', len(uv), 'finite', int(fin.sum()))
        M, inl = robust_fit(Xo[fin], X[fin], last) if fin.sum() >= a.min_inl else (None, np.zeros(fin.sum(), bool))
        full_inl = np.zeros(len(uv), bool); full_inl[np.nonzero(fin)[0][inl]] = True
        if M is not None:
            Tpt[t] = M; last = M; ninl[t] = int(full_inl.sum()); lost = 0
            bad = np.where(full_inl, 0, bad + 1)
        else:
            bad = bad + 1; lost += 1
        keepm = bad < 3; uv, Xo, bad = uv[keepm], Xo[keepm], bad[keepm]
        if M is not None and len(uv) < a.reseed_frac * n_seed and ninl[t] >= a.min_inl:
            # re-seed in the template's visible, depth-consistent surface at the point-track pose (others at
            # FoundationPose's), gated to the inliers' object-frame box (+1 cm)
            pw = {o: P_fp[o][t] for o in names}; pw[n] = M
            new = seed(t, render_masks(t, pw)[n], a.max_pts)
            if len(uv) and len(new):
                dmin = np.min(np.linalg.norm(new[:, None] - uv[None], axis=2), 1); new = new[dmin > 4]
            Xn = lift(t, new); okn = np.isfinite(Xn).all(1); new, Xn = new[okn], Xn[okn]
            invt = np.linalg.inv(M); Xon = Xn @ invt[:3, :3].T + invt[:3, 3]
            lo, hi = Xo.min(0) - 0.01, Xo.max(0) + 0.01
            g = ((Xon >= lo) & (Xon <= hi)).all(1)
            if g.sum():
                uv = np.vstack([uv, new[g]]).astype(np.float32); Xo = np.vstack([Xo, Xon[g]]); bad = np.r_[bad, np.zeros(g.sum(), int)]
                n_seed = max(n_seed, len(uv)); reseeds += 1
    return Tpt, ninl, seg, dict(reseeds=reseeds, restarts=restarts)

def blend(A_, B_, w):
    """(1-w) A + w B on SE(3): lerp translation, slerp rotation."""
    s = Slerp([0, 1], Rot.from_matrix(np.stack([A_[:3, :3], B_[:3, :3]])))
    M = np.eye(4); M[:3, :3] = s([w]).as_matrix()[0]; M[:3, 3] = (1 - w) * A_[:3, 3] + w * B_[:3, 3]
    return M

def pt_err(A_, B_, X):
    return float(np.linalg.norm((X @ A_[:3, :3].T + A_[:3, 3]) - (X @ B_[:3, :3].T + B_[:3, 3]), axis=1).mean())

out, info, traj = {}, {}, {}
for n in names:
    t0 = time.time()
    Tpt, ninl, seg, tinfo = track_object_ext(n) if a.tracks else track_object(n)
    valid = np.isfinite(Tpt[:, 0, 0]) & (ninl >= a.min_inl)
    Xs = SURF[n][::300]                                            # 200 template surface points (ADD-like errors)
    Pf = P_fp[n]; Pout = Pf.copy()
    e = np.full(N, np.nan); typ = [''] * N
    spans = []; state = 'fp'; run = 0; anchor = None; back = 0; held = 0
    t = a.W
    while t < N:
        s = t - a.W
        if state == 'fp':
            if valid[t] and valid[s] and seg[t] == seg[s]:
                D = Tpt[t] @ np.linalg.inv(Tpt[s]); Qt = D @ Pout[s]
                e[t] = pt_err(Qt, Pf[t], Xs)
                m_pt = pt_err(D @ Pf[s], Pf[s], Xs); m_fp = pt_err(Pf[t], Pf[s], Xs)
                typ[t] = 'lag' if m_pt > m_fp + a.lag_margin else 'jump'
                run = run + 1 if e[t] > a.e_flag else 0
            else:
                run = 0
            if run >= a.n_flag:
                onset = t - a.n_flag + 1; kind = 'lag' if sum(typ[k] == 'lag' for k in range(onset, t + 1)) > a.n_flag / 2 else 'jump'
                do = a.repair == 'all' or (a.repair == 'lag' and kind == 'lag')
                spans.append(dict(onset=int(onset), anchor=int(max(onset - a.W, 0)), kind=kind, repaired=bool(do), end=None))
                if do:
                    anchor = max(onset - a.W, 0); state = 'rep'; back = 0
                    for k in range(anchor + 1, t + 1):
                        Pout[k] = (Tpt[k] @ np.linalg.inv(Tpt[anchor]) @ Pout[anchor]) if valid[k] and valid[anchor] and seg[k] == seg[anchor] else Pout[k - 1]
                run = 0
            t += 1
        else:                                                      # repairing: follow the points from the anchor
            if valid[t] and valid[anchor] and seg[t] == seg[anchor]:
                Pout[t] = Tpt[t] @ np.linalg.inv(Tpt[anchor]) @ Pout[anchor]
            else:
                Pout[t] = Pout[t - 1]; held += 1
                if valid[t] and seg[t] == seg[anchor]:              # re-anchor on the held pose
                    anchor = t
            e[t] = pt_err(Pout[t], Pf[t], Xs)
            back = back + 1 if e[t] < a.e_back else 0
            if seg[t] != seg[anchor]:     # the points restarted from FoundationPose's depth-consistent pose: hand back
                back = a.n_back
            if back >= a.n_back:                                   # FoundationPose agrees again: ramp back
                spans[-1]['end'] = int(t)
                for k in range(1, a.ramp + 1):
                    if t + k >= N: break
                    Qk = Tpt[t + k] @ np.linalg.inv(Tpt[anchor]) @ Pout[anchor] if valid[t + k] and valid[anchor] and seg[t + k] == seg[anchor] else Pout[t + k - 1]
                    Pout[t + k] = blend(Qk, Pf[t + k], k / (a.ramp + 1))
                state = 'fp'; run = 0; t += a.ramp + 1; continue
            t += 1
    out[n] = Pout
    rep = int(sum(((Pout[k] - Pf[k]) ** 2).sum() > 1e-12 for k in range(N)))
    info[n] = dict(seeded=int(ninl[0]), median_inliers=int(np.median(ninl)), frames_valid=int(valid.sum()), **tinfo,
                   spans=spans, frames_changed=rep, held=held, guard=GUARD.get(n), sec=round(time.time() - t0, 1),
                   e_max_cm=round(float(np.nanmax(e)) * 100, 2) if np.isfinite(e).any() else None)
    traj[f'Tpt_{n}'] = Tpt; traj[f'e_{n}'] = e; traj[f'ninl_{n}'] = ninl; traj[f'seg_{n}'] = seg
    log(n, info[n])
np.savez(f'{a.out}/poses_world_vo.npz', **out)
np.savez_compressed(f'{a.out}/ptrack_traj.npz', **traj)
json.dump(dict(episode=a.ep, objects=names, frames=N, settings=vars(a), objects_info=info), open(f'{a.out}/ptrack.json', 'w'), indent=1)
log('DONE')
