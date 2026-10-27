"""Per-frame rigid refinement of observed points against a consensus surface built from all frames (track jitter).

Why: obs_points.py moves each frame's stereo points into the object frame with OUR track (inv(cam_T_obj[t])). Small
per-frame pose errors (a 1-2 deg tilt moves a point 0.2 m from the centre by 3-7 mm) smear thin parts over several
millimetres although each single frame sees them sharply. Hypothesis [H] (critic, handle_smear.py): on the white
pot the handle's between-frame spread exceeds its within-frame width.

Method (generic: no object name, no part vocabulary, no per-object constant; every size is a sensor or voxel scale):
  1. Per frame: 1.5 mm voxel subsample of its points; PCA normals over KNN neighbours of the SAME frame (one frame sees
     one side of a thin wall, so its normals are sharp), oriented towards that frame's camera centre.
  2. Consensus surfels from all frames under their current corrections: 3 mm voxels keyed by voxel AND by the side
     the surface was seen from (dominant axis and sign of the oriented normal), so the two faces of a 2-3 mm wall stay
     separate surfaces. A voxel needs points from >= MIN_FRAMES frames. Each surfel is then moved along its mean
     normal to the frame-balanced weighted MEDIAN offset of the same-side points within SURFEL_R (every frame
     counts once): a smeared layer collapses onto its median surface instead of staying thick.
  3. Per frame: trimmed, Cauchy-weighted point-to-plane ICP of its subsampled points to the surfels (a correspondence
     must be seen from the same side: normal agreement > cos 60 deg; gate MAX_D), Gauss-Newton about the cloud
     centroid with a weak Gaussian prior on the TOTAL correction (sigma 2 deg / 5 mm; it holds directions the frame
     cannot see, e.g. rotation about a symmetry axis) and hard bounds MAX_ROT_DEG / MAX_TRANS (bound hits are
     reported). Frames with fewer than MIN_PTS matched points keep their current correction.
  4. Gauge: the matched-count-weighted mean correction is removed after every pass, so the consensus cannot drift
     the object frame (the frame stays the one of our library meshes / tracks).
  5. ITERS passes of 2-4 with a shrinking gate (12 -> 8 -> 6 mm); then a last consensus is built for the report.
The corrections are applied to every point and camera centre of each frame. The 4 mm hit/free vote grids are copied
unchanged (they need the depth maps to be re-voted; corrections are mm-level against 4 mm cells): report['grids_stale'].

GT-free: reads only the observation dict it is given (pts, cam, frame; grids are passed through). No scan, mocap,
*_align file or parquet pose is opened here; the loader is autokit/io_gt.py.

Usage (library):
    from autokit.io_gt import load_obs, obs_path
    from autokit.refine import refine_frames, save_refined, patch_spread
    obs = load_obs(obs_path('white_pot', 41))
    ref_obs, rep = refine_frames(obs)                      # rep: per-frame corrections and residuals, summary
    save_refined(ref_obs, rep, OUT.npz)                    # npz with the same keys + OUT.refine.json (+ .corr.npz)
    patch_spread(obs), patch_spread(ref_obs)               # object-agnostic between-/within-frame spread statistic
Optional: ref = a trimesh.Trimesh in the same object frame (e.g. our library mesh) replaces the self-consensus;
fit_mask = bool (N,) excludes points from fitting AND from the consensus (held-out validation).
CLI: python refine.py IN.npz OUT.npz [--iters 3]
"""
import json, math, os, sys, time

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

VOX = 0.0015            # per-frame subsample (m), about the stereo point spacing at 0.5-0.8 m
KNN = 12                # within-frame neighbours for normals
SURFEL_VOX = 0.003      # consensus seed voxel (m)
SURFEL_R = 0.006        # consensus neighbourhood radius (m)
MIN_FRAMES = 3          # frames that must support a consensus surfel
MAX_NB = 384            # neighbours per surfel used (strided subset)
POOL_CAP = 6000         # points per frame pooled into the consensus
FIT_CAP = 3000          # points per frame used by ICP
MIN_PTS = 200           # matched points for a frame to be refined
PLANAR_MIN = 0.3        # ICP uses points whose neighbourhood is at least this planar
COS_SIDE_POOL = math.cos(math.radians(45))   # same-side test inside the consensus
COS_SIDE_ICP = math.cos(math.radians(60))    # same-side test for ICP correspondences
GATES = (0.012, 0.008, 0.006, 0.006)         # ICP correspondence gate per pass (m)
EVAL_GATE = 0.010       # gate of the before/after residual statistic (m)
ICP_ITERS = 10
SIG_R, SIG_ROT, SIG_T = 0.001, math.radians(2.0), 0.005     # residual scale and the prior on the total correction
MAX_ROT_DEG, MAX_TRANS = 3.0, 0.010
CAUCHY = 2.4            # Cauchy weight constant in units of the robust residual scale
MIN_SCALE = 0.0007      # floor of the robust residual scale (m)


# ---------------------------------------------------------------------------------------------- helpers
def _lin_key(I):
    """Integer (n,3) voxel indices -> one int64 key per row (shifted to be non-negative)."""
    I = I - I.min(0)
    d = I.max(0) + 1
    return (I[:, 0] * d[1] + I[:, 1]) * d[2] + I[:, 2]


def _voxel_first(P, vox):
    """Indices of one point per occupied voxel (the first), in input order."""
    _, first = np.unique(_lin_key(np.floor(P / vox).astype(np.int64)), return_index=True)
    return np.sort(first)


def _normals(P, cam, k=KNN):
    """PCA normals over k nearest neighbours (same frame), oriented towards the camera centre; planarity in [0, 1]."""
    k = min(k, len(P))
    _, nb = cKDTree(P).query(P, k=k)
    Q = P[nb] - P[nb].mean(1, keepdims=True)
    w, V = np.linalg.eigh(np.einsum('nki,nkj->nij', Q, Q) / k)
    n = V[:, :, 0]
    n[np.einsum('ni,ni->n', n, cam - P) < 0] *= -1
    return n, 1 - w[:, 0] / np.maximum(w[:, 1], 1e-12)


def _side_bin(N):
    """6 side classes: dominant axis of the oriented normal and its sign (opposite faces of a wall differ)."""
    a = np.argmax(np.abs(N), 1)
    return 2 * a + (N[np.arange(len(N)), a] < 0)


def _group_first_true(gid_sorted, mask):
    """For rows sorted by group id: index (into the sorted rows) of the first True per group, and those groups."""
    rows = np.nonzero(mask)[0]
    g, first = np.unique(gid_sorted[rows], return_index=True)
    return g, rows[first]


def _apply(R, t, c0, X):
    return (X - c0) @ R.T + c0 + t


# ---------------------------------------------------------------------------------------------- per-frame data
def prepare_frames(obs, fit_mask=None, seed=0):
    """Per frame: 1.5 mm subsample Q with normals N and planarity; ICP subset and pool subset (fit_mask honoured)."""
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64); F = np.asarray(obs['frame'])
    order = np.argsort(F, kind='stable')
    fids, start, cnt = np.unique(F[order], return_index=True, return_counts=True)
    rng = np.random.default_rng(seed)
    frames = []
    for fid, s0, n in zip(fids, start, cnt):
        g = order[s0:s0 + n]
        sub = g[_voxel_first(P[g], VOX)]
        d = dict(fid=int(fid), idx=g, n_raw=int(n))
        if len(sub) < KNN + 1:
            d.update(Q=np.zeros((0, 3)), N=np.zeros((0, 3)), fit=np.zeros(0, int), pool=np.zeros(0, int))
            frames.append(d); continue
        Q = P[sub]; N, planar = _normals(Q, C[sub])
        usable = np.ones(len(sub), bool) if fit_mask is None else np.asarray(fit_mask)[sub]
        fit = np.nonzero(usable & (planar > PLANAR_MIN))[0]
        if len(fit) > FIT_CAP:
            fit = np.sort(rng.choice(fit, FIT_CAP, replace=False))
        pool = np.nonzero(usable)[0]
        if len(pool) > POOL_CAP:
            pool = np.sort(rng.choice(pool, POOL_CAP, replace=False))
        d.update(Q=Q, N=N, planar=planar, fit=fit, pool=pool, cam=C[sub[0]])
        frames.append(d)
    return frames


# ---------------------------------------------------------------------------------------------- consensus
def build_consensus(frames, corr, c0, surfel_vox=SURFEL_VOX, surfel_r=SURFEL_R, min_frames=MIN_FRAMES):
    """Consensus surfels (S, NS, support frames) from the pooled, corrected points of all frames (see docstring 2)."""
    Ps, Ns, Fs = [], [], []
    for i, fr in enumerate(frames):
        if len(fr['pool']) == 0:
            continue
        R, t = corr[i]
        Ps.append(_apply(R, t, c0, fr['Q'][fr['pool']])); Ns.append(fr['N'][fr['pool']] @ R.T)
        Fs.append(np.full(len(fr['pool']), i, np.int64))
    P = np.concatenate(Ps); N = np.concatenate(Ns); F = np.concatenate(Fs)
    nF = len(frames)
    # seeds: (voxel, side) cells supported by >= min_frames frames
    key = _lin_key(np.floor(P / surfel_vox).astype(np.int64)) * 6 + _side_bin(N)
    uk, inv = np.unique(key, return_inverse=True)
    kf = np.unique(inv * nF + F)
    nfr = np.bincount(kf // nF, minlength=len(uk))
    cnt = np.bincount(inv, minlength=len(uk)).astype(float)
    S0 = np.stack([np.bincount(inv, P[:, j], len(uk)) for j in range(3)], 1) / cnt[:, None]
    N0 = np.stack([np.bincount(inv, N[:, j], len(uk)) for j in range(3)], 1)
    keep = (nfr >= min_frames) & (np.linalg.norm(N0, axis=1) > 1e-9)
    S0 = S0[keep]; N0 = N0[keep] / np.linalg.norm(N0[keep], axis=1, keepdims=True)
    # robust projection: frame-balanced weighted median offset of same-side neighbours along the mean normal
    tree = cKDTree(P)
    S_out, N_out, sup_out = [], [], []
    for c in range(0, len(S0), 4000):
        Sc, Nc = S0[c:c + 4000], N0[c:c + 4000]
        lists = tree.query_ball_point(Sc, surfel_r)
        lens = np.array([len(l) for l in lists])
        step = np.maximum(1, lens // MAX_NB)
        sid = np.concatenate([np.full(len(l[::s]), q) for q, (l, s) in enumerate(zip(lists, step))])
        idx = np.concatenate([np.asarray(l[::s], np.int64) for l, s in zip(lists, step)])
        side = np.einsum('ni,ni->n', N[idx], Nc[sid]) > COS_SIDE_POOL
        sid, idx = sid[side], idx[side]
        off = np.einsum('ni,ni->n', P[idx] - Sc[sid], Nc[sid])
        ok = np.abs(off) <= surfel_r
        sid, idx, off = sid[ok], idx[ok], off[ok]
        # every frame counts once per surfel
        sf = sid * nF + F[idx]
        usf, sfi, sfc = np.unique(sf, return_inverse=True, return_counts=True)
        w = 1.0 / sfc[sfi]
        nfs = np.bincount(usf // nF, minlength=len(Sc))
        # weighted mean normal
        Nm = np.stack([np.bincount(sid, w * N[idx, j], len(Sc)) for j in range(3)], 1)
        # weighted median offset per surfel
        o = np.lexsort((off, sid)); sid_s, off_s, w_s = sid[o], off[o], w[o]
        W = np.bincount(sid_s, w_s, len(Sc))
        cw = np.cumsum(w_s); gstart = np.r_[0, np.cumsum(np.bincount(sid_s, minlength=len(Sc)))[:-1]]
        base = np.where(gstart > 0, cw[np.maximum(gstart - 1, 0)], 0.0)
        cw_in = cw - base[sid_s]
        g, at = _group_first_true(sid_s, cw_in >= 0.5 * W[sid_s])
        med = np.zeros(len(Sc)); med[g] = off_s[at]
        good = (nfs >= min_frames) & (np.linalg.norm(Nm, axis=1) > 1e-9)
        Nn = Nm[good] / np.linalg.norm(Nm[good], axis=1, keepdims=True)
        S_out.append(Sc[good] + med[good, None] * Nc[good]); N_out.append(Nn); sup_out.append(nfs[good])
    return np.concatenate(S_out), np.concatenate(N_out), np.concatenate(sup_out)


def surfels_from_mesh(mesh, n=300000, vox=SURFEL_VOX, seed=0):
    """Reference surfels from one of OUR meshes in the object frame: surface samples with outward face normals."""
    import trimesh
    S, fi = trimesh.sample.sample_surface(mesh, n, seed=seed)
    NS = mesh.face_normals[fi]
    k = _voxel_first(S, vox * 0.5)
    return S[k], NS[k], np.full(len(k), 999)


# ---------------------------------------------------------------------------------------------- matching + ICP
def match(X, Nx, tree, S, NS, gate):
    """Nearest same-side surfel within the gate: (mask, surfel index, signed point-to-plane residual)."""
    d, j = tree.query(X, k=4, distance_upper_bound=gate)
    valid = np.isfinite(d)
    jj = np.minimum(j, len(S) - 1)
    ok = valid & (np.einsum('nkc,nc->nk', NS[jj], Nx) > COS_SIDE_ICP)
    has = ok.any(1); first = ok.argmax(1)
    js = jj[np.arange(len(X)), first]
    r = np.einsum('ni,ni->n', X - S[js], NS[js])
    return has, js, r


def _robust_w(r):
    s = max(1.4826 * float(np.median(np.abs(r))), MIN_SCALE)
    return 1.0 / (1.0 + (r / (CAUCHY * s)) ** 2), s


def icp_frame(Q, N, R, t, c0, tree, S, NS, gate, iters=ICP_ITERS):
    """Point-to-plane Gauss-Newton with the prior on the total correction and hard bounds. Returns (R, t, info)."""
    D = np.r_[[SIG_R ** 2 / SIG_ROT ** 2] * 3, [SIG_R ** 2 / SIG_T ** 2] * 3]
    info = dict(n_fit=int(len(Q)))
    for it in range(iters):
        X = _apply(R, t, c0, Q); Nx = N @ R.T
        has, js, r = match(X, Nx, tree, S, NS, gate)
        if it == 0:
            info['n_match0'] = int(has.sum())
            info['res0_mm'] = float(np.median(np.abs(r[has])) * 1e3) if has.any() else float('nan')
        if has.sum() < MIN_PTS:
            info['skipped'] = 'few_matches'; break
        Xm, n, rm = X[has], NS[js[has]], r[has]
        w, s = _robust_w(rm)
        J = np.c_[np.cross(Xm - c0, n), n]
        H = (J * w[:, None]).T @ J; g = (J * w[:, None]).T @ rm
        xi = np.r_[Rotation.from_matrix(R).as_rotvec(), t]
        A = H + np.diag(D) + 1e-6 * np.diag(np.diag(H))
        delta = -np.linalg.solve(A, g + D * xi)
        dR = Rotation.from_rotvec(delta[:3]).as_matrix()
        R = dR @ R; t = dR @ t + delta[3:]
        # hard bounds on the total correction
        rv = Rotation.from_matrix(R).as_rotvec(); ang = np.linalg.norm(rv)
        if ang > math.radians(MAX_ROT_DEG):
            R = Rotation.from_rotvec(rv * math.radians(MAX_ROT_DEG) / ang).as_matrix(); info['bound_rot'] = True
        if np.linalg.norm(t) > MAX_TRANS:
            t = t * MAX_TRANS / np.linalg.norm(t); info['bound_trans'] = True
        if np.linalg.norm(delta[:3]) * 0.1 + np.linalg.norm(delta[3:]) < 2e-6:
            break
    if 'skipped' not in info:
        ev = np.linalg.eigvalsh(H)
        info.update(n_match=int(has.sum()), scale_mm=s * 1e3, cond=float(ev[-1] / max(ev[0], 1e-30)), iters=it + 1)
    return R, t, info


def _gauge(corr, wts):
    """Remove the weighted mean correction (exactly: compose with the inverse of the mean transform about c0)."""
    wts = np.asarray(wts, float)
    if wts.sum() <= 0:
        return corr, np.zeros(6)
    rv = np.array([Rotation.from_matrix(R).as_rotvec() for R, _ in corr]); tt = np.array([t for _, t in corr])
    m_rv = (wts[:, None] * rv).sum(0) / wts.sum(); m_t = (wts[:, None] * tt).sum(0) / wts.sum()
    Rm_T = Rotation.from_rotvec(m_rv).as_matrix().T
    return [(Rm_T @ R, Rm_T @ (t - m_t)) for R, t in corr], np.r_[m_rv, m_t]


def frame_residuals(frames, corr, c0, tree, S, NS, gate=EVAL_GATE):
    """Median |point-to-plane residual| (mm) and match fraction per frame against fixed surfels."""
    med, frac = [], []
    for i, fr in enumerate(frames):
        if len(fr['fit']) == 0:
            med.append(np.nan); frac.append(0.0); continue
        R, t = corr[i]
        Q, N = fr['Q'][fr['fit']], fr['N'][fr['fit']]
        has, _, r = match(_apply(R, t, c0, Q), N @ R.T, tree, S, NS, gate)
        med.append(float(np.median(np.abs(r[has])) * 1e3) if has.sum() >= MIN_PTS else np.nan)
        frac.append(float(has.mean()))
    return np.array(med), np.array(frac)


# ---------------------------------------------------------------------------------------------- main entry
def refine_frames(obs, ref=None, iters=3, gauge=True, fit_mask=None, seed=0, verbose=False, **kw):
    """Per-frame rigid correction of each frame's points to a consensus of all frames (or to ref surfels).
    Returns (obs_refined with the same keys, report). kw may override the module constants by lower-case name:
    surfel_vox, surfel_r, min_frames, gates (tuple)."""
    t0 = time.time()
    surfel_vox = kw.get('surfel_vox', SURFEL_VOX); surfel_r = kw.get('surfel_r', SURFEL_R)
    min_frames = kw.get('min_frames', MIN_FRAMES); gates = tuple(kw.get('gates', GATES))
    P = np.asarray(obs['pts'], np.float64)
    c0 = np.median(P, 0)
    frames = prepare_frames(obs, fit_mask=fit_mask, seed=seed)
    nF = len(frames)
    corr = [(np.eye(3), np.zeros(3)) for _ in range(nF)]
    if ref is not None:
        S, NS, sup = surfels_from_mesh(ref) if hasattr(ref, 'faces') else ref
    rep = dict(n_frames=nF, n_pts=int(len(P)), passes=[], c0=c0.tolist(), ref=None if ref is None else 'given')
    infos = [dict() for _ in range(nF)]
    res_before = None
    for it in range(iters):
        if ref is None:
            S, NS, sup = build_consensus(frames, corr, c0, surfel_vox, surfel_r, min_frames)
        tree = cKDTree(S)
        if it == 0:
            res_before, frac_before = frame_residuals(frames, corr, c0, tree, S, NS)
        gate = gates[min(it, len(gates) - 1)]
        wts = np.zeros(nF)
        for i, fr in enumerate(frames):
            if len(fr['fit']) < MIN_PTS:
                infos[i] = dict(skipped='few_points', n_fit=int(len(fr['fit']))); continue
            R, t, inf = icp_frame(fr['Q'][fr['fit']], fr['N'][fr['fit']], corr[i][0], corr[i][1], c0, tree, S, NS, gate)
            infos[i] = inf
            if 'skipped' not in inf:
                corr[i] = (R, t); wts[i] = inf['n_match']
        mean_corr = np.zeros(6)
        if gauge:
            corr, mean_corr = _gauge(corr, wts)
        rep['passes'].append(dict(gate_mm=gate * 1e3, surfels=int(len(S)), fitted=int((wts > 0).sum()),
                                  gauge_removed_deg=float(np.degrees(np.linalg.norm(mean_corr[:3]))),
                                  gauge_removed_mm=float(np.linalg.norm(mean_corr[3:]) * 1e3),
                                  sec=round(time.time() - t0, 1)))
        if verbose:
            print(json.dumps(rep['passes'][-1]), flush=True)
    # final consensus of the refined frames, for the after-statistic only
    if ref is None:
        S, NS, sup = build_consensus(frames, corr, c0, surfel_vox, surfel_r, min_frames)
    tree = cKDTree(S)
    res_after, frac_after = frame_residuals(frames, corr, c0, tree, S, NS)
    # apply to every point and camera centre
    out = {k: v for k, v in obs.items()}
    pts = np.asarray(obs['pts'], np.float64).copy(); cam = np.asarray(obs['cam'], np.float64).copy()
    for i, fr in enumerate(frames):
        R, t = corr[i]; g = fr['idx']
        pts[g] = _apply(R, t, c0, pts[g]); cam[g] = _apply(R, t, c0, cam[g])
    out['pts'] = pts.astype(np.asarray(obs['pts']).dtype); out['cam'] = cam.astype(np.asarray(obs['cam']).dtype)
    # report
    rot = np.array([np.degrees(np.linalg.norm(Rotation.from_matrix(R).as_rotvec())) for R, _ in corr])
    tr = np.array([np.linalg.norm(t) * 1e3 for _, t in corr])
    fitted = np.array(['skipped' not in inf and 'n_match' in inf for inf in infos])
    per = []
    for i, fr in enumerate(frames):
        R, t = corr[i]
        per.append(dict(frame=fr['fid'], n_raw=fr['n_raw'], fitted=bool(fitted[i]),
                        rotvec_deg=np.round(np.degrees(Rotation.from_matrix(R).as_rotvec()), 4).tolist(),
                        t_mm=np.round(t * 1e3, 3).tolist(), res_before_mm=_r(res_before[i]),
                        res_after_mm=_r(res_after[i]), **{k: _r(v) for k, v in infos[i].items()}))
    # temporal structure of the corrections: lag-1 autocorrelation of each component over consecutive fitted frames
    X = np.array([np.r_[np.degrees(Rotation.from_matrix(R).as_rotvec()), t * 1e3] for R, t in corr])[fitted]
    ac = [float(np.corrcoef(X[:-1, j], X[1:, j])[0, 1]) if len(X) > 3 and X[:, j].std() > 0 else float('nan')
          for j in range(6)]
    f = fitted
    rep.update(
        frames_fitted=int(f.sum()), frames_skipped=int((~f).sum()),
        res_before_med_mm=_r(np.nanmedian(res_before)), res_after_med_mm=_r(np.nanmedian(res_after)),
        match_frac_before=_r(np.mean(frac_before)), match_frac_after=_r(np.mean(frac_after)),
        rot_deg_p50=_r(np.median(rot[f])) if f.any() else None, rot_deg_p90=_r(np.percentile(rot[f], 90)) if f.any() else None,
        trans_mm_p50=_r(np.median(tr[f])) if f.any() else None, trans_mm_p90=_r(np.percentile(tr[f], 90)) if f.any() else None,
        bound_hits=int(sum(bool(inf.get('bound_rot') or inf.get('bound_trans')) for inf in infos)),
        lag1_autocorr_rot_t=[_r(a) for a in ac], surfels_final=int(len(S)), grids_stale=True,
        sec=round(time.time() - t0, 1), per_frame=per,
        params=dict(VOX=VOX, KNN=KNN, SURFEL_VOX=surfel_vox, SURFEL_R=surfel_r, MIN_FRAMES=min_frames, GATES=gates,
                    FIT_CAP=FIT_CAP, POOL_CAP=POOL_CAP, MIN_PTS=MIN_PTS, SIG_ROT_DEG=math.degrees(SIG_ROT),
                    SIG_T=SIG_T, MAX_ROT_DEG=MAX_ROT_DEG, MAX_TRANS=MAX_TRANS, iters=iters, gauge=gauge,
                    fit_mask=fit_mask is not None))
    rep['corr'] = dict(frame=np.array([fr['fid'] for fr in frames]),
                       R=np.array([R for R, _ in corr]), t=np.array([t for _, t in corr]), c0=c0)
    return out, rep


def _r(v, nd=4):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), nd)
    return v


def save_refined(obs_ref, rep, out_path):
    """npz with the input's keys; the report as OUT.refine.json and the corrections as OUT.corr.npz
    (p_refined = R (p - c0) + c0 + t per frame; the corrected track is cam_T_obj[t] @ inv([R | c0 + t - R c0]))."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    np.savez_compressed(out_path, **obs_ref)
    base = out_path[:-4] if out_path.endswith('.npz') else out_path
    c = rep['corr']
    np.savez_compressed(base + '.corr.npz', frame=c['frame'], R=c['R'], t=c['t'], c0=c['c0'])
    json.dump({k: v for k, v in rep.items() if k != 'corr'}, open(base + '.refine.json', 'w'), indent=1)


# ---------------------------------------------------------------------------------------------- diagnostic
def patch_spread(obs, n_patches=3000, radius=0.005, min_pts=8, min_frames=8, region=None, seed=0, frames=None):
    """Object-agnostic jitter statistic (the critic's handle measure generalised to random surface patches).
    Seeds: random subsampled points (optionally only where region(X) is True). Per patch: same-side points of all
    frames within RADIUS, offsets along the patch's mean normal; per frame (>= MIN_PTS points) the median offset and
    the p5-p95 width; between = p5-p95 of the per-frame medians (>= MIN_FRAMES frames), within = median per-frame
    width. Returns medians over patches (mm) and the share of patches with between > within. No GT."""
    frames = frames if frames is not None else prepare_frames(obs, seed=seed)
    P = np.concatenate([fr['Q'] for fr in frames if len(fr['Q'])])
    N = np.concatenate([fr['N'] for fr in frames if len(fr['Q'])])
    F = np.concatenate([np.full(len(fr['Q']), i) for i, fr in enumerate(frames) if len(fr['Q'])])
    rng = np.random.default_rng(seed)
    cand = np.arange(len(P)) if region is None else np.nonzero(region(P))[0]
    if len(cand) == 0:
        return dict(n_patches=0)
    seeds = rng.choice(cand, min(n_patches, len(cand)), replace=False)
    tree = cKDTree(P); nF = len(frames)
    lists = tree.query_ball_point(P[seeds], radius)
    sid = np.concatenate([np.full(len(l), q) for q, l in enumerate(lists)])
    idx = np.concatenate([np.asarray(l, np.int64) for l in lists])
    ns = N[seeds]
    same = np.einsum('ni,ni->n', N[idx], ns[sid]) > COS_SIDE_POOL
    sid, idx = sid[same], idx[same]
    Nm = np.stack([np.bincount(sid, N[idx, j], len(seeds)) for j in range(3)], 1)
    Nm /= np.maximum(np.linalg.norm(Nm, axis=1, keepdims=True), 1e-12)
    off = np.einsum('ni,ni->n', P[idx] - P[seeds][sid], Nm[sid])
    key = sid * nF + F[idx]
    o = np.lexsort((off, key)); key_s, off_s = key[o], off[o]
    uk, st, ct = np.unique(key_s, return_index=True, return_counts=True)
    okg = ct >= min_pts
    uk, st, ct = uk[okg], st[okg], ct[okg]
    pick = lambda q: off_s[st + np.floor(q * (ct - 1)).astype(int)]  # noqa: E731
    med, width = pick(0.5), pick(0.95) - pick(0.05)
    psid = uk // nF
    between, within, nfr = [], [], []
    o2 = np.lexsort((med, psid)); psid_s, med_s, width_s = psid[o2], med[o2], width[o2]
    up, st2, ct2 = np.unique(psid_s, return_index=True, return_counts=True)
    for s0, c in zip(st2, ct2):
        if c < min_frames:
            continue
        m = med_s[s0:s0 + c]
        between.append(m[int(np.floor(0.95 * (c - 1)))] - m[int(np.floor(0.05 * (c - 1)))])
        within.append(np.median(width_s[s0:s0 + c])); nfr.append(c)
    if not between:
        return dict(n_patches=0)
    b, w = np.array(between) * 1e3, np.array(within) * 1e3
    return dict(n_patches=int(len(b)), between_mm=_r(np.median(b), 3), within_mm=_r(np.median(w), 3),
                ratio=_r(np.median(b / np.maximum(w, 1e-6)), 3), frac_between_gt_within=_r(np.mean(b > w), 3),
                frames_per_patch=_r(np.median(nfr), 1))


def _sphere_lsq(Q, c=None, r=None, iters=8):
    """Algebraic sphere fit (if no start) then Gauss-Newton on the geometric distance; returns (c, r)."""
    if c is None:
        A = np.c_[2 * Q, np.ones(len(Q))]; sol = np.linalg.lstsq(A, (Q ** 2).sum(1), rcond=None)[0]
        c = sol[:3]; r2 = sol[3] + c @ c
        if r2 <= 0:
            return None, None
        r = math.sqrt(r2)
    for _ in range(iters):
        D = Q - c; dn = np.maximum(np.linalg.norm(D, axis=1), 1e-9)
        J = np.c_[-D / dn[:, None], -np.ones(len(Q))]
        st = np.linalg.lstsq(J, -(dn - r), rcond=None)[0]
        c = c + st[:3]; r = r + st[3]
        if np.linalg.norm(st) < 1e-7:
            break
    return c, float(r)


def ball_scan(obs, r_range=(0.002, 0.016), seed_vox=0.004, nb_r=0.016, band=0.0012, min_inl=60, min_frames=10,
              max_res=0.0007, min_convex=0.8, min_cover=0.12, min_iso=0.3, min_protrude=0.8, pool_cap=2500, seed=0,
              frames=None):
    """Free-radius sphere detector (no radius prior; the window is a generic 2-16 mm), used to MEASURE the marker
    ball radius from public observations. Per 4 mm seed: same-frame-normal points within NB_R -> algebraic + geometric
    sphere fit, inliers |d - r| <= BAND, refit. Accepted when (all generic): r in R_RANGE (not at its ends), >= MIN_INL
    inliers from >= MIN_FRAMES frames, median |d - r| <= MAX_RES, convex towards the cameras (mean normal . radial
    >= MIN_CONVEX), cap coverage 1 - |mean radial unit vector| >= MIN_COVER, isotropic normal spread (tangent-plane
    eigenvalue ratio >= MIN_ISO, so a fillet or a rim (one curved direction) is rejected), protruding from the
    surrounding surface (p90 height above the plane of the r+2..r+8 mm shell >= MIN_PROTRUDE r, or an empty shell:
    a sphere-shaped patch OF a smooth surface is rejected). Non-maximum suppression on
    centres within r. Returns a list of dict(c, r_mm, inliers, frames, res_mm, cover, iso, convex). No GT."""
    frames = frames if frames is not None else prepare_frames(obs, seed=seed)
    rng = np.random.default_rng(seed)
    Ps, Ns, Fs = [], [], []
    for i, fr in enumerate(frames):
        if len(fr['Q']) == 0:
            continue
        k = np.arange(len(fr['Q'])) if len(fr['Q']) <= pool_cap else rng.choice(len(fr['Q']), pool_cap, replace=False)
        Ps.append(fr['Q'][k]); Ns.append(fr['N'][k]); Fs.append(np.full(len(k), i))
    P = np.concatenate(Ps); N = np.concatenate(Ns); F = np.concatenate(Fs)
    tree = cKDTree(P)
    seeds = P[_voxel_first(P, seed_vox)]
    found = []
    for s in seeds:
        nb = np.asarray(tree.query_ball_point(s, nb_r), np.int64)
        if len(nb) < min_inl:
            continue
        if len(nb) > 3000:
            nb = rng.choice(nb, 3000, replace=False)
        c, r = _sphere_lsq(P[nb])
        if c is None or not (r_range[0] < r < r_range[1]) or np.linalg.norm(c - s) > r + band:
            continue
        for _ in range(2):          # inliers of the current sphere -> refit
            d = np.linalg.norm(P[nb] - c, axis=1); inl = nb[np.abs(d - r) <= band]
            if len(inl) < min_inl:
                break
            c, r = _sphere_lsq(P[inl], c, r)
            if c is None or not (r_range[0] < r < r_range[1]):
                break
        if c is None or len(inl) < min_inl or not (r_range[0] < r < r_range[1]):
            continue
        # the whole ball, not only the seed's neighbourhood
        inl = np.asarray(tree.query_ball_point(c, r + band), np.int64)
        d = np.linalg.norm(P[inl] - c, axis=1); inl = inl[np.abs(d - r) <= band]
        if len(inl) < min_inl:
            continue
        U = (P[inl] - c) / np.linalg.norm(P[inl] - c, axis=1, keepdims=True)
        convex = float(np.mean(np.einsum('ni,ni->n', N[inl], U)))
        m = U.mean(0); cover = 1 - float(np.linalg.norm(m))
        e1, e2 = np.linalg.svd(np.eye(3) - np.outer(m, m) / max(m @ m, 1e-12))[0][:, :2].T
        T2 = np.c_[U @ e1, U @ e2]; ev = np.linalg.eigvalsh(np.cov(T2.T))
        iso = float(ev[0] / max(ev[1], 1e-12))
        res = float(np.median(np.abs(np.linalg.norm(P[inl] - c, axis=1) - r)))
        nfr = int(len(np.unique(F[inl])))
        # protrusion: a ball stands out of the surface around it (shell r+2..r+8 mm); a patch of a smooth surface
        # that happens to fit a sphere lies IN that surface. Height of the inliers above the shell's plane (oriented
        # to the shell normals), p90 in units of r; an empty shell (ball on a stem) counts as protruding.
        sh = np.asarray(tree.query_ball_point(c, r + 0.008), np.int64)
        sh = sh[np.linalg.norm(P[sh] - c, axis=1) >= r + 0.002]
        if len(sh) < 0.2 * len(inl):
            protrude = 9.0
        else:
            p0 = P[sh].mean(0); nn = np.linalg.svd(P[sh] - p0, full_matrices=False)[2][2]
            if nn @ N[sh].mean(0) < 0:
                nn = -nn
            protrude = float(np.percentile((P[inl] - p0) @ nn, 90) / r)
        if (nfr >= min_frames and res <= max_res and convex >= min_convex and cover >= min_cover and iso >= min_iso
                and protrude >= min_protrude):
            found.append(dict(c=c.tolist(), r_mm=r * 1e3, inliers=int(len(inl)), frames=nfr, res_mm=res * 1e3,
                              cover=cover, iso=iso, convex=convex, protrude=protrude, shell=int(len(sh))))
    # non-maximum suppression: keep the best-supported sphere among centres closer than the larger radius
    found.sort(key=lambda b: -b['inliers'])
    keep = []
    for b in found:
        if all(np.linalg.norm(np.array(b['c']) - np.array(k['c'])) > max(b['r_mm'], k['r_mm']) * 1e-3 for k in keep):
            keep.append(b)
    return [{k: (_r(v) if not isinstance(v, list) else [round(x, 5) for x in v]) for k, v in b.items()} for b in keep]


if __name__ == '__main__':
    import argparse
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from autokit.io_gt import load_obs
    ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--iters', type=int, default=3)
    a = ap.parse_args()
    o = load_obs(a.inp)
    r_obs, rep = refine_frames(o, iters=a.iters, verbose=True)
    save_refined(r_obs, rep, a.out)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('per_frame', 'corr')}))
