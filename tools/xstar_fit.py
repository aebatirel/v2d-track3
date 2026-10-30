"""ORACLE DIAGNOSTIC (public episodes only): frame relations X = scan_T_lib between our library meshes and the organiser
scans, for the leak decomposition (docs/research/work/leak-decomp-20261030/PLAN.md §2, build item B1).

A point p of our mesh's body frame sits at X p in the scan's body frame, so lib-frame pose = scan-frame pose @ X (the
convention of pipeline/oracle_poses.py and pipeline/frame_xform.py).
  geom  X*_geom per object, from the scans only (no mocap): the rigid, unscaled surface fit of LIB/<obj>.glb to the public
        scan. Trimmed ICP (90 %, <= 80 iterations, 6000 samples a side, lib onto scan as the kit's _align_rigid) from 85
        starts: identity, the kit's 24 PCA mappings, 48 seeded random rotations, and 12 spins about the scan axis (cups)
        or the 180 deg flip about the normal (lid); the best by the kit's symmetric mean surface distance on 10000 fresh
        samples a side. Reports the residuals, the RMS-radius ratio (the kit's registration rescales by it before its
        ICP), the distinct minima (symmetry-aware: a cup spin or a lid flip is the same minimum) and how close they come
        to the best (ambiguity), the cup spin profile, and per public episode and slot the kit's own registration X_kit
        (seed 1_000_003 ep + 101 slot) with the error E = X*_geom inv(X_kit) it puts on a perfect lib track.
  trk   X*_trk per (episode, object): the constant body offset fitted to MOCAP for one perception track (lib frames):
        robust least squares (soft-L1, 2 cm) of G T_perc(t) inv(X) p = T_mocap(t) p over host points p (<= 200 frames),
        one free world transform G per episode, a weak prior towards X*_geom for directions the motion leaves unseen.
        Cups use 3 points on the scan axis (spin is neither scored nor observable), so their spin stays X*_geom's; the
        lid's 180 deg flip is chosen per frame. The scorer pins the world on frame 0 (_align_registered_scene), so the
        geometric optimum is not the scorer's: from the LS fit and from X*_geom, Powell then maximises a soft AUC (each
        threshold step a 1 cm ramp) under the kit's own conversion and alignment. X*_trk is the candidate (X*_geom, LS,
        the two refits) with the highest exact AUC among those within 5 cm (symmetry-aware ADD) of X*_geom, so
        T_trk >= T*: the most a constant per-episode body offset can recover (an upper bound; T_trk_ls, the geometric
        fit, is reported beside it). Then scores the track with the kit's chain: lib (X_kit, our mesh, the leaderboard
        convention), * (X*_geom), trk (X*_trk), trk_ls. READS GROUND TRUTH: an oracle diagnostic only, never a default
        anywhere, never an input of eval inference.
Usage: python -I xstar_fit.py geom --lib LIB --t3 T3 --kit KIT --out xstar_geom.json [--episodes 0,2,11]
       python -I xstar_fit.py trk --perc ROOT --geom xstar_geom.json --lib LIB --t3 T3 --kit KIT --out xstar_trk.json
              [--episodes ...]         (ROOT/ep<N>/poses_world_vo.npz: the track to fit, lib frames)
(2026-10-30)
"""
import argparse, hashlib, json, math, os, sys, time
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.optimize import least_squares, minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

EVAL = {1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38}       # as oracle_poses.py
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}                # as score_registered.py
N_FIT, N_EVAL, N_RANDOM, ITERS, TRIM = 6000, 10000, 48, 80, 0.9
AMBIG = 1.10        # a distinct minimum within 10 % of the best residual is reported as an ambiguity [H: threshold]
DISTINCT_CM = 0.5   # minima closer than this (symmetry-aware mean point displacement) are the same minimum
TRK_MAX_CM = 5.0    # an X*_trk candidate further than this from X*_geom (symmetry-aware ADD) is a failure, not a bias [H]
K = None            # the kit's modules (kit())


def kit(path):
    global K
    sys.path.insert(0, path)
    from v2dlb import track3_pose as T3
    from v2dlb import object_mesh as OM
    from v2dlb.mesh_budget import budget_mesh
    from v2dlb.mesh_common import _sample_mesh_surface
    K = dict(T3=T3, OM=OM, budget=budget_mesh, sample=_sample_mesh_surface)


def scan_path(t3, n):
    q = f'{t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{t3}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def host_geometry(t3, n, slot):  # the stand-in for the hidden scan geometry, exactly as score_registered.py
    v, f = load_vf(scan_path(t3, n)); c, r = K['OM']._surface_moments(v, f)
    pts = K['sample'](v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, radius=r, points=pts, axis=axis, order=order)


def rigid(R, t):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t; return M


def about(axis, theta, c):  # rotation by theta about the line through c along axis (4x4)
    R = Rot.from_rotvec(np.asarray(axis) * theta).as_matrix(); return rigid(R, c - R @ c)


def sym_group(H, steps=360):  # the scorer's symmetry rotations, as 4x4 about the anchor
    if H['order'] == 2:
        return [np.eye(4), about(H['axis'], np.pi, H['anchor'])]
    if H['order']:
        return [about(H['axis'], th, H['anchor']) for th in np.arange(steps) * 2 * np.pi / steps]
    return [np.eye(4)]


def sym_add_cm(E, H, steps=360):
    """Mean displacement (cm) of the host points by a scan-frame error transform E, minimised over the scorer's
    symmetries (cups: spin, 1 deg; lid: 180 deg) -- the per-frame ADD a constant E adds to a perfect track."""
    p = H['points'] + H['anchor']; q = p @ E[:3, :3].T + E[:3, 3]
    return float(min(np.linalg.norm(q - (p @ S[:3, :3].T + S[:3, 3]), axis=1).mean() for S in sym_group(H, steps)) * 100)


def rot_deg(R):
    return float(np.degrees(Rot.from_matrix(R).magnitude()))


def tilt_deg(R, axis):  # angle the rotation moves the symmetry axis by (the part of R a cup's symmetry does not absorb)
    return float(np.degrees(np.arccos(np.clip(axis @ R @ axis, -1, 1))))


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def names_of(t3, ep):  # slot order of the episode (names only; the pose field is not used here)
    row = pq.read_table(f'{t3}/ep{ep}.parquet', columns=['observation.objects']).column('observation.objects')[0].as_py()
    return [str(o['name']) for o in row]


def mocap(t3, ep, N=None):  # ground truth: scan body-frame poses, (N,4,4) per name (N=None: every frame)
    tab = pq.read_table(f'{t3}/ep{ep}.parquet', columns=['observation.objects']).column('observation.objects').to_pylist()
    names = [str(o['name']) for o in tab[0]]
    N = len(tab) if N is None else N
    if len(tab) < N:
        sys.exit(f'ep{ep}: ground truth has {len(tab)} frames, the track {N}')
    out = {}
    for n in names:
        q = np.array([[o['pose'] for o in row if o['name'] == n][0] for row in tab[:N]], np.float64)  # x y z qw qx qy qz
        M = np.repeat(np.eye(4)[None], N, 0); M[:, :3, :3] = Rot.from_quat(q[:, [4, 5, 6, 3]]).as_matrix(); M[:, :3, 3] = q[:, :3]
        out[n] = M
    return names, out


# ---------------- geom: rigid fit of our mesh to the scan
def icp(L, S, tree, R, t):
    prev = math.inf
    for _ in range(ITERS):
        moved = L @ R.T + t
        d, i = tree.query(moved, k=1)
        keep = np.argpartition(d, int(len(d) * TRIM) - 1)[:int(len(d) * TRIM)]
        dR, dt = K['OM']._kabsch(moved[keep], S[i[keep]])
        R = dR @ R; t = dR @ t + dt
        err = float(d[keep].mean())
        if abs(prev - err) <= 1e-9 * max(prev, 1.0):
            break
        prev = err
    return R, t


def residuals(Se, Le, X):
    m = Le @ X[:3, :3].T + X[:3, 3]
    d_ls = cKDTree(Se).query(m)[0]; d_sl = cKDTree(m).query(Se)[0]
    tr = lambda d: float(np.sort(d)[:int(len(d) * TRIM)].mean() * 1000)
    return dict(sym_mm=round(float(0.5 * (d_ls.mean() + d_sl.mean()) * 1000), 3), lib_to_scan_mm=round(float(d_ls.mean() * 1000), 3),
                scan_to_lib_mm=round(float(d_sl.mean() * 1000), 3), sym_trim90_mm=round(0.5 * (tr(d_ls) + tr(d_sl)), 3),
                lib_to_scan_p90_mm=round(float(np.percentile(d_ls, 90) * 1000), 3),
                scan_to_lib_p90_mm=round(float(np.percentile(d_sl, 90) * 1000), 3))


def fit_geom(n, lib, t3):
    H = host_geometry(t3, n, 0)
    sv, sf = H['mesh']; lv, lf = load_vf(f'{lib}/{n}.glb')
    lc, lr = K['OM']._surface_moments(lv, lf)
    S, L = K['sample'](sv, sf, N_FIT, 11), K['sample'](lv, lf, N_FIT, 12)
    Se, Le = K['sample'](sv, sf, N_EVAL, 21), K['sample'](lv, lf, N_EVAL, 22)
    tree = cKDTree(S)
    starts = list(K['OM']._initial_rotations(S - S.mean(0), L - L.mean(0), 25))
    starts += list(Rot.random(N_RANDOM, random_state=0).as_matrix())
    if H['order'] == 360:
        starts += [Rot.from_rotvec(H['axis'] * th).as_matrix() for th in np.arange(12) * np.pi / 6]
    elif H['order'] == 2:
        starts += [Rot.from_rotvec(H['axis'] * np.pi).as_matrix()]
    sols = []
    for R0 in starts:
        R, t = icp(L, S, tree, R0, S.mean(0) - R0 @ L.mean(0))
        X = rigid(R, t)
        sols.append((K['OM']._symmetric_mean_distance(Se, Le @ R.T + t), X))
    sols.sort(key=lambda s: s[0])
    best = sols[0][1]
    minima = []                                                    # distinct local minima, best first
    for sc, X in sols:
        if all(sym_add_cm(X @ np.linalg.inv(Y), H, 72) > DISTINCT_CM for _, Y in minima):
            minima.append((sc, X))
    out = dict(scan=os.path.relpath(scan_path(t3, n), t3), lib_md5=md5(f'{lib}/{n}.glb'), scan_md5=md5(scan_path(t3, n)),
               symmetry={0: 'none', 2: 'lid 180 deg', 360: 'cup axis'}[H['order']], scan_axis=np.round(H['axis'], 5).tolist(),
               X_scan_T_lib=np.round(best, 9).tolist(), rot_deg=round(rot_deg(best[:3, :3]), 3),
               shift_cm=round(float(np.linalg.norm(best[:3, 3]) * 100), 3),
               lib_centroid_in_scan_cm=np.round((best[:3, :3] @ lc + best[:3, 3] - H['anchor']) * 100, 3).tolist(),
               rms_radius_ratio_scan_over_lib=round(float(H['radius'] / lr), 4), residual=residuals(Se, Le, best),
               starts=len(starts),
               minima=[dict(sym_mm=round(sc * 1000, 3), ratio_to_best=round(sc / minima[0][0], 3),
                            add_from_best_cm=round(sym_add_cm(X @ np.linalg.inv(best), H), 3),
                            rot_from_best_deg=round(rot_deg(X[:3, :3] @ best[:3, :3].T), 1),
                            hits=int(sum(sym_add_cm(Y @ np.linalg.inv(X), H, 72) <= DISTINCT_CM for _, Y in sols)))
                       for sc, X in minima[:5]])
    rival = [m for m in out['minima'][1:] if m['ratio_to_best'] <= AMBIG]
    out['ambiguous'] = bool(rival)
    rs = []                                                        # sampling stability: refit from the best, new samples
    for k in (31, 41):
        S2, L2 = K['sample'](sv, sf, N_FIT, k), K['sample'](lv, lf, N_FIT, k + 1)
        R, t = icp(L2, S2, cKDTree(S2), best[:3, :3], best[:3, 3]); rs.append(sym_add_cm(rigid(R, t) @ np.linalg.inv(best), H))
    out['reseed_add_cm_max'] = round(max(rs), 4)
    if H['order'] == 360:                                          # residual vs spin about the scan axis, no refit
        prof = [K['OM']._symmetric_mean_distance(Se, Le @ (about(H['axis'], th, H['anchor']) @ best)[:3, :3].T
                                                 + (about(H['axis'], th, H['anchor']) @ best)[:3, 3]) * 1000
                for th in np.radians(np.arange(0, 360, 10))]
        out['spin_profile_mm'] = dict(step_deg=10, min=round(min(prof), 3), max=round(max(prof), 3),
                                      argmin_deg=int(10 * np.argmin(prof)), values=np.round(prof, 3).tolist())
    if H['order'] == 2:
        F = about(H['axis'], np.pi, H['anchor']) @ best
        out['flipped_sym_mm'] = round(K['OM']._symmetric_mean_distance(Se, Le @ F[:3, :3].T + F[:3, 3]) * 1000, 3)
    return out, H


def kit_X(lib_path, H, ep, slot):  # the kit's registration as X (oracle_poses.py: X = [R, c - R ca])
    ca, R = K['T3']._register_object_body(K['budget'](lib_path, 4096, 4096), H['mesh'], H['anchor'], 1_000_003 * ep + 101 * slot)
    return rigid(R, H['anchor'] - R @ ca), (ca, R)


def reg_of_X(X, anchor):  # (candidate anchor, body rotation) that makes the kit's _convert_object_body apply inv(X)
    return (np.linalg.inv(X) @ np.r_[anchor, 1.0])[:3], X[:3, :3].copy()


def compare(E, H):  # what a constant scan-frame error E does to a perfect track
    d = dict(rot_deg=round(rot_deg(E[:3, :3]), 3), anchor_shift_cm=round(float(np.linalg.norm(E[:3, :3] @ H['anchor'] + E[:3, 3] - H['anchor']) * 100), 3),
             sym_add_cm=round(sym_add_cm(E, H), 3))
    if H['order']:
        d['axis_tilt_deg'] = round(tilt_deg(E[:3, :3], H['axis']), 3)
    return d


# ---------------- scoring (the kit's chain, as score_registered.py, with any registration)
def to7(M):  # (..., 4, 4) -> x y z qx qy qz qw
    return np.concatenate([M[..., :3, 3], Rot.from_matrix(M[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(M.shape[:-2] + (4,))], -1)


def score_track(names, track, gt, H, REG):
    """Registered ADD-AUC vs mocap of lib-frame poses track[name] (N,4,4); REG[s] = (candidate anchor, rotation)."""
    T3 = K['T3']; N = len(track[names[0]]); B = len(names)
    ach = np.stack([to7(track[n]) for n in names], 1)[:, None].copy(); ref = np.stack([to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    per = {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1], pts[s:s + 1],
                                                     axes[s:s + 1], orders[s:s + 1])), 4) for s, n in enumerate(names)}
    return dict(AUC=round(float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders)), 4), per_obj_AUC=per)


# ---------------- trk: constant body offset fitted to mocap
def fit_trk(names, Tp, gt, Xg, H, f_scale=0.02, w_prior=1.0, max_frames=200):
    N = len(Tp[names[0]]); idx = np.arange(0, N, max(1, -(-N // max_frames)))
    P, W, Y0 = [], [], []
    for s, n in enumerate(names):
        h = H[s]
        if h['order'] == 360:
            r = float(np.sqrt((h['points'] ** 2).sum(1).mean()))
            P.append(h['anchor'] + np.outer([-1.0, 0.0, 1.0], h['axis']) * r)
        else:
            P.append(h['anchor'] + h['points'][::10])
        W.append(np.sqrt(100.0 / len(P[-1]))); Y0.append(np.linalg.inv(Xg[n]))
    A = [np.einsum('tij,jk->tik', Tp[n][idx], Y0[s]) for s, n in enumerate(names)]   # world_T_scanbody, X = X*_geom
    flips = [sym_group(h) if h['order'] == 2 else [np.eye(4)] for h in H]
    choice = [np.zeros(len(idx), int) for _ in names]

    def target(s):
        Sg = np.stack([F for F in flips[s]])[choice[s]]                                   # (t,4,4)
        q = np.einsum('tij,kj->tki', Sg[:, :3, :3], P[s]) + Sg[:, None, :3, 3]
        M = gt[names[s]][idx]
        return np.einsum('tij,tkj->tki', M[:, :3, :3], q) + M[:, None, :3, 3]

    def moved(s, x6):
        R = Rot.from_rotvec(x6[:3]).as_matrix(); q = P[s] @ R.T + x6[3:]
        return np.einsum('tij,kj->tki', A[s][:, :3, :3], q) + A[s][:, None, :3, 3]

    # G0: Kabsch of all moved points (X = X*_geom) onto mocap; G = G(x) G0, rotation about the targets' centroid m
    tg = [target(s) for s in range(len(names))]
    src = np.concatenate([moved(s, np.zeros(6)).reshape(-1, 3) for s in range(len(names))])
    dst = np.concatenate([t.reshape(-1, 3) for t in tg]); m = dst.mean(0)
    R0, t0 = K['OM']._kabsch(src, dst); G0 = rigid(R0, t0)

    def G_of(x):
        R = Rot.from_rotvec(x[:3]).as_matrix(); return rigid(R, m - R @ m + x[3:6]) @ G0

    def res(x, free):
        G = G_of(x); out = []
        for s in range(len(names)):
            xs = x[6 + 6 * s:12 + 6 * s] if free else np.zeros(6)
            pw = moved(s, xs) @ G[:3, :3].T + G[:3, 3]
            out.append((W[s] * (pw - tg[s])).ravel())
            if free:
                out.append(np.sqrt(w_prior) * np.r_[xs[:3] * H[s]['radius'], xs[3:]])
        return np.concatenate(out)

    def solve(free, x0):
        return least_squares(res, x0, args=(free,), loss='soft_l1', f_scale=f_scale, x_scale=0.01, max_nfev=400).x

    x = np.zeros(6 + 6 * len(names))
    for rnd in range(3 if any(h['order'] == 2 for h in H) else 1):
        x = solve(True, x)
        for s, h in enumerate(H):                                                         # re-pick the lid's flip
            if h['order'] == 2:
                G = G_of(x); pw = moved(s, x[6 + 6 * s:12 + 6 * s]) @ G[:3, :3].T + G[:3, 3]
                errs = []
                for k in range(2):
                    choice[s][:] = k; errs.append(np.linalg.norm(pw - target(s), axis=-1).mean(-1))
                choice[s][:] = np.argmin(np.stack(errs), 0); tg[s] = target(s)
    xg = solve(False, np.zeros(6 + 6 * len(names)))                                       # G only, X = X*_geom

    def err_cm(x, free):
        G = G_of(x); d = {}
        for s, n in enumerate(names):
            xs = x[6 + 6 * s:12 + 6 * s] if free else np.zeros(6)
            e = np.linalg.norm(moved(s, xs) @ G[:3, :3].T + G[:3, 3] - tg[s], axis=-1).mean(-1) * 100
            d[n] = dict(median=round(float(np.median(e)), 3), mean=round(float(e.mean()), 3), p90=round(float(np.percentile(e, 90)), 3))
        return d

    Xt = {}
    for s, n in enumerate(names):
        xs = x[6 + 6 * s:12 + 6 * s]
        Xt[n] = np.linalg.inv(Y0[s] @ rigid(Rot.from_rotvec(xs[:3]).as_matrix(), xs[3:]))
    span = {n: round(float(max(rot_deg(Tp[n][i, :3, :3] @ Tp[n][idx[0], :3, :3].T) for i in idx)), 1) for n in names}
    return Xt, dict(frames_used=int(len(idx)), stride=int(idx[1] - idx[0]) if len(idx) > 1 else 1, f_scale_m=f_scale,
                    point_err_cm_geom=err_cm(xg, False), point_err_cm_trk=err_cm(x, True), track_rot_span_deg=span,
                    G_mocap_T_perc=np.round(G_of(x), 6).tolist(),
                    lid_flipped_frames={names[s]: int(choice[s].sum()) for s, h in enumerate(H) if h['order'] == 2})


THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8   # the kit's ADD thresholds, trapezoid weights


def soft_auc(e):  # the kit's per-body ADD-AUC with each threshold step replaced by a 1 cm ramp (smooth surrogate)
    return float(np.mean(np.clip((THR[None] - e[:, None]) / 0.01 + 0.5, 0, 1) @ TW))


def fit_trk_scorer(names, Tp, gt, H, starts, maxfev=3000):
    """Constant X per object that maximises the soft AUC under the kit's own conversion and frame-0 scene alignment
    (the alignment pins the world on frame 0, so the geometric LS optimum is not the scorer's), from each start
    ({name: X}). Cups: 3 points on the axis; lid: min over its flip; others: 100 host points."""
    T3 = K['T3']; B = len(names); N = len(Tp[names[0]])
    ach0 = np.stack([to7(Tp[n]) for n in names], 1)[:, None]; ref = np.stack([to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    kp, tgt = [], []
    for s, h in enumerate(H):
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), h['anchor'])
        r = float(np.sqrt((h['points'] ** 2).sum(1).mean()))
        kp.append(np.outer([-1.0, 0.0, 1.0], h['axis']) * r if h['order'] == 360 else h['points'][::10])
        Rr = T3._rotation_matrix(ref[:, 0, s, 3:])
        tgt.append([np.einsum('tij,kj->tki', Rr, kp[s] @ S[:3, :3].T) + ref[:, 0, s, None, :3]
                    for S in (sym_group(h) if h['order'] == 2 else [np.eye(4)])])
    axes = [h['axis'] for h in H]

    def X_of(X0, u):
        return np.linalg.inv(np.linalg.inv(X0) @ rigid(Rot.from_rotvec(u[:3] * 0.05).as_matrix(), u[3:] * 0.01))

    def f(u, X0s):
        ach = ach0.copy()
        for s, n in enumerate(names):
            ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *reg_of_X(X_of(X0s[n], u[6 * s:6 * s + 6]), H[s]['anchor']))
        ach = T3._align_registered_scene(ach, ref, axes); tot = 0.0
        for s in range(B):
            pa = np.einsum('tij,kj->tki', T3._rotation_matrix(ach[:, 0, s, 3:]), kp[s]) + ach[:, 0, s, None, :3]
            tot += soft_auc(np.min([np.linalg.norm(pa - q, axis=-1).mean(-1) for q in tgt[s]], 0))
        return -tot / B

    out = []
    for X0s in starts:
        r = minimize(f, np.zeros(6 * B), args=(X0s,), method='Powell', options=dict(maxfev=maxfev, xtol=1e-3, ftol=1e-7))
        out.append(({n: X_of(X0s[n], r.x[6 * s:6 * s + 6]) for s, n in enumerate(names)},
                    dict(soft_auc_start=round(-f(np.zeros(6 * B), X0s), 4), soft_auc_end=round(-r.fun, 4), nfev=int(r.nfev))))
    return out


def trk_episode(ep, a, Xg_all):
    kit(a.kit); t0 = time.time()
    f = f'{a.perc}/ep{ep}/poses_world_vo.npz'
    V = np.load(f); names, gt = mocap(a.t3, ep, len(V[V.files[0]]))
    if sorted(names) != sorted(V.files):
        sys.exit(f'ep{ep}: track names {V.files} != episode slots {names}')
    Tp = {n: V[n].astype(np.float64) for n in names}
    H = [host_geometry(a.t3, n, s) for s, n in enumerate(names)]
    Xg = {n: np.asarray(Xg_all['objects'][n]['X_scan_T_lib']) for n in names}
    Xls, fit = fit_trk(names, Tp, gt, Xg, H)
    opt = fit_trk_scorer(names, Tp, gt, H, [Xls, Xg])
    cand = {'geom': Xg, 'ls': Xls, 'opt_from_ls': opt[0][0], 'opt_from_geom': opt[1][0]}
    REG = {k: [reg_of_X(X[n], H[s]['anchor']) for s, n in enumerate(names)] for k, X in cand.items()}
    REG['lib'] = [kit_X(f'{a.lib}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)]
    sc = {k: score_track(names, Tp, gt, H, R) for k, R in REG.items()}
    far = {k: max(sym_add_cm(X[n] @ np.linalg.inv(Xg[n]), H[s]) for s, n in enumerate(names)) for k, X in cand.items()}
    ok = [k for k in ('geom', 'ls', 'opt_from_ls', 'opt_from_geom') if far[k] <= TRK_MAX_CM]   # geom first: ties keep it
    pick = max(ok, key=lambda k: sc[k]['AUC'])
    Xt = cand[pick]
    fit.update(scorer_fit={'from_ls': opt[0][1], 'from_geom': opt[1][1]}, candidates_AUC={k: sc[k]['AUC'] for k in cand},
               candidates_max_offset_cm={k: round(v, 3) for k, v in far.items()}, rejected_over_cap=[k for k in cand if k not in ok],
               picked=pick)
    r = dict(track=os.path.abspath(f), track_md5=md5(f), frames=len(Tp[names[0]]), fit=fit,
             scores={'lib': sc['lib'], 'star': sc['geom'], 'trk': sc[pick], 'trk_ls': sc['ls']},
             objects={n: dict(slot=s, X_scan_T_lib=np.round(Xt[n], 9).tolist(), trk_vs_geom=compare(Xt[n] @ np.linalg.inv(Xg[n]), H[s]),
                              ls_vs_geom=compare(Xls[n] @ np.linalg.inv(Xg[n]), H[s])) for s, n in enumerate(names)})
    print(f'ep{ep}: lib {sc["lib"]["AUC"]:.4f}  * {sc["geom"]["AUC"]:.4f}  trk {sc[pick]["AUC"]:.4f} ({pick}; ls {sc["ls"]["AUC"]:.4f})  '
          + ', '.join(f'{n} {r["objects"][n]["trk_vs_geom"]["sym_add_cm"]:.2f} cm' for n in names) + f'  ({time.time() - t0:.0f} s)', flush=True)
    return ep, r


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['geom', 'trk'])
    p.add_argument('--lib', required=True); p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
    p.add_argument('--out', required=True); p.add_argument('--episodes', default=','.join(map(str, PUBLIC)))
    p.add_argument('--perc', help='trk: ROOT with ep<N>/poses_world_vo.npz (lib frames)')
    p.add_argument('--geom', help='trk: xstar_geom.json')
    p.add_argument('--jobs', type=int, default=4, help='trk: episodes in parallel')
    a = p.parse_args()
    eps = [int(e) for e in a.episodes.split(',') if e]
    bad = [e for e in eps if e in EVAL]
    if bad or os.environ.get('SPLIT', 'public') != 'public':
        sys.exit(f'eval episodes {bad} / SPLIT={os.environ.get("SPLIT")}: this oracle diagnostic is for public episodes only')
    kit(a.kit); t0 = time.time()
    if a.mode == 'geom':
        objs = sorted(n for n in os.listdir(f'{a.t3}/mesh') if os.path.exists(f'{a.lib}/{n}.glb'))
        res = dict(kind='geom', note='X*_geom: rigid fit of our library mesh to the public scan (scans only, no mocap). '
                   'X = scan_T_lib: lib-frame pose = scan-frame pose @ X. Public-episode diagnostic; not a default anywhere.',
                   lib=os.path.abspath(a.lib), method=dict(icp='trimmed point-to-point, lib onto scan', trim=TRIM, iters=ITERS,
                   fit_samples=N_FIT, eval_samples=N_EVAL, random_starts=N_RANDOM, ambiguity_ratio=AMBIG, distinct_cm=DISTINCT_CM),
                   objects={}, kit_registration={})
        H0 = {}
        for n in objs:
            res['objects'][n], H0[n] = fit_geom(n, a.lib, a.t3)
            o = res['objects'][n]
            print(f'{n:18s} rot {o["rot_deg"]:7.2f} shift {o["shift_cm"]:5.2f} cm  sym {o["residual"]["sym_mm"]:6.2f} mm  '
                  f'ratio {o["rms_radius_ratio_scan_over_lib"]:.3f}  minima {[(m["ratio_to_best"], m["rot_from_best_deg"]) for m in o["minima"][:3]]}'
                  f'{"  AMBIGUOUS" if o["ambiguous"] else ""}  ({time.time() - t0:.0f} s)', flush=True)
        for ep in eps:
            names = names_of(a.t3, ep); res['kit_registration'][str(ep)] = {}
            for s, n in enumerate(names):
                H = host_geometry(a.t3, n, s); Xk, _ = kit_X(f'{a.lib}/{n}.glb', H, ep, s)
                Xg = np.asarray(res['objects'][n]['X_scan_T_lib'])
                res['kit_registration'][str(ep)][n] = dict(slot=s, X_kit=np.round(Xk, 9).tolist(), rot_deg=round(rot_deg(Xk[:3, :3]), 3),
                                                           E_xstar_inv_kit=compare(Xg @ np.linalg.inv(Xk), H))
            print(f'ep{ep}: ' + ', '.join(f'{n} E {v["E_xstar_inv_kit"]["sym_add_cm"]:.2f} cm' for n, v in res['kit_registration'][str(ep)].items()), flush=True)
    else:
        Xg_all = json.load(open(a.geom)); assert Xg_all['kind'] == 'geom'
        res = dict(kind='trk', note='X*_trk: constant body offset per (episode, object) FITTED TO MOCAP for the given track. '
                   'ORACLE DIAGNOSTIC ONLY: never a default, never for eval inference. X = scan_T_lib.',
                   perc=os.path.abspath(a.perc), geom=os.path.abspath(a.geom), geom_md5=md5(a.geom), lib=os.path.abspath(a.lib), episodes={})
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(a.jobs) as ex:
            for ep, r in ex.map(trk_episode, eps, [a] * len(eps), [Xg_all] * len(eps)):
                res['episodes'][str(ep)] = r
    res['seconds'] = round(time.time() - t0, 1)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(f'wrote {a.out}')


if __name__ == '__main__':
    main()
