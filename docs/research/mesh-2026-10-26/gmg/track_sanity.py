"""Track sanity and identity tests (module M3 of SPEC section 7; build step B4).

  check(bundle, obj) -> {good: bool[T], flags, below_table_frac, block_resid_mm, identity_split, identity_cross}
  route_a_shell(obs, frames=None, cap=SHELL_CAP, seed=0) -> (samples (n,3) of the route-A sheet, info)
  register(A, B, n=REG_N) -> (T 4x4 moving A onto B, chamfer_mm): rigid best-of-24 PCA-start ICP, no scale, no
                             identity start
  chamfer_mm(A, B) -> symmetric chamfer (mean of the two mean nearest distances) in mm
  split_test(bundle, obj, partner) -> dict        SPEC section 7: halves of o must match each other better than either
                                                  matches the partner's shell
  cross_test(shells, key) -> dict                 SPEC section 7: o's shell must lie nearer to o's shells of its other
                                                  good public episodes than to any other object's shell

GT-free: our owned points, our tracks and the per-frame table planes of the bundle. The thresholds are PREREG A.6
"track sanity" and "identity tests" (informed: written after tracks were found bad through scan ADD).

Bad frame (SPEC section 7): more than 5 % of the object's owned points (all frames, object frame; placed by the frame's
track) lie more than max(3 sigma, 3 mm) below the frame's table plane, or the frame's block-vs-rest residual
exceeds 3 times the episode median (blocks: the A.2 K = 3 contiguous blocks of the object's frames; residual of frame
f = median distance of f's owned points to the 2 mm centroids of the owned points of the other blocks). TRACK_FAIL:
fewer than 30 % of the object's frames, or fewer than 20 frames, are good.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy.spatial import cKDTree

from gmg import guard, contact as CT

SHELL_CAP = 400000      # route-A sheet input cap for the identity shells (random owned points, seed 0; numerical)
SHELL_SAMPLES = 4000    # area-weighted samples of a sheet used by the chamfer (seed 0; numerical)
REG_N = 1500            # points per side in the ICP (random, seed 0; numerical)
ICP_ITERS = 30
RESID_N = 2000          # owned points of a frame used for its block-vs-rest residual (random, seed 0; numerical)
BELOW_N = 50000         # owned points used by the below-table test (random, seed 0; numerical)


def _consts():
    g = guard.constant
    return dict(
        below_share=g('sanity_below_share', 0.05, 'informed:PREREG A.6 track sanity (> 5 % of owned points)'),
        below_k=g('sanity_below_sigma_k', 3.0, 'informed:PREREG A.6 track sanity (below max(3 sigma, 3 mm))'),
        below_min=g('sanity_below_min_m', 0.003, 'informed:PREREG A.6 track sanity (below max(3 sigma, 3 mm))'),
        resid_k=g('sanity_block_resid_k', 3.0, 'informed:PREREG A.6 track sanity (block residual > 3 x median)'),
        blocks=g('sanity_blocks_K', 3, 'generic:PREREG A.6 K = 3 contiguous blocks (A.2)'),
        fail_frac=g('sanity_fail_frac', 0.30, 'informed:PREREG A.6 track sanity (TRACK_FAIL < 30 % good)'),
        fail_min=g('sanity_fail_min_frames', 20, 'informed:PREREG A.6 track sanity (TRACK_FAIL < 20 good frames)'),
        pca_starts=g('identity_pca_starts', 24, 'informed:PREREG A.6 identity tests (best-of-24 PCA-start ICP)'),
    )


def _table_cam(bundle, f):
    tf = bundle.meta.get('table_frames') or {}
    r = tf.get(str(f))
    if r is None:
        return None
    return np.asarray(r[0], np.float64), float(r[1])


def frames_with_points(obs):
    own = np.asarray(obs['own'])
    return sorted(np.unique(np.asarray(obs['frame'])[own == 0]).tolist())


def check(bundle, obj):
    c = _consts()
    obs = bundle.obs(obj)
    T = int(bundle.meta['T'])
    sig = bundle.sigma(obj)
    P = np.asarray(obs['pts'], np.float64)
    fr = np.asarray(obs['frame'])
    own = np.asarray(obs['own'])
    frs = frames_with_points(obs)
    # the object's owned points (all frames, object frame; BELOW_N at random, seed 0) placed by each frame's track
    idx = np.nonzero(own == 0)[0]
    if len(idx) > BELOW_N:
        idx = np.random.default_rng(0).choice(idx, BELOW_N, replace=False)
    X = P[idx]
    thr = max(c['below_k'] * sig, c['below_min'])
    below = {}
    for f in frs:
        pl = _table_cam(bundle, f)
        if pl is None or not len(X):
            continue
        Tc = bundle.poses[f'cam_T_{obj}'][f].astype(np.float64)
        Xc = X @ Tc[:3, :3].T + Tc[:3, 3]
        h = Xc @ pl[0] + pl[1]
        below[f] = float((h < -thr).mean())
    # block-vs-rest residual
    K = c['blocks']
    resid = {}
    if len(frs) >= K:
        blocks = np.array_split(np.asarray(frs), K)
        rng = np.random.default_rng(0)
        for b in range(K):
            rest = np.isin(fr, np.concatenate([blocks[q] for q in range(K) if q != b])) & (own == 0)
            if not rest.any():
                continue
            tree = cKDTree(CT.centroids(P[rest]))
            for f in blocks[b]:
                idx = np.nonzero((fr == f) & (own == 0))[0]
                if len(idx) > RESID_N:
                    idx = rng.choice(idx, RESID_N, replace=False)
                if len(idx):
                    resid[int(f)] = float(np.median(tree.query(P[idx], k=1)[0]))
    med = float(np.median(list(resid.values()))) if resid else float('nan')
    bad_below = [f for f, v in below.items() if v > c['below_share']]
    bad_resid = [f for f, v in resid.items() if np.isfinite(med) and v > c['resid_k'] * med]
    bad = set(bad_below) | set(bad_resid)
    good = [False] * T
    for f in frs:
        if f not in bad:
            good[f] = True
    n_good = int(sum(good))
    flags = []
    if n_good < c['fail_frac'] * max(len(frs), 1) or n_good < c['fail_min']:
        flags.append('TRACK_FAIL')
    rv = np.array(list(resid.values())) if resid else np.zeros(0)
    return dict(good=good, flags=flags, n_frames=len(frs), n_good=n_good,
                below_table_frac=round(len(bad_below) / max(len(frs), 1), 4),
                below_share_median=round(float(np.median(list(below.values()))), 5) if below else None,
                below_share_max=round(float(max(below.values())), 5) if below else None,
                bad_below=bad_below, bad_resid=bad_resid,
                block_resid_mm=dict(median=round(med * 1e3, 3) if np.isfinite(med) else None,
                                    p90=round(float(np.percentile(rv, 90)) * 1e3, 3) if len(rv) else None,
                                    max=round(float(rv.max()) * 1e3, 3) if len(rv) else None),
                below_thr_mm=round(thr * 1e3, 3))


# ------------------------------------------------------------------------------------------------ shells, registration
def route_a_shell(obs, frames=None, cap=SHELL_CAP, seed=0):
    """Samples of the route-A sheet (autokit.shell.shell_sheet; the shell's mid-surface, see DEVIATIONS) of the owned
    points of FRAMES (all if None), at most CAP of them at random (seed 0)."""
    from autokit import shell as SH
    import trimesh
    fr = np.asarray(obs['frame'])
    sel = np.asarray(obs['own']) == 0
    if frames is not None:
        sel &= np.isin(fr, list(frames))
    idx = np.nonzero(sel)[0]
    rng = np.random.default_rng(seed)
    if len(idx) > cap:
        idx = np.sort(rng.choice(idx, cap, replace=False))
    sub = {k: np.asarray(obs[k])[idx] for k in ('pts', 'cam', 'frame')}
    sh = SH.shell_sheet(sub)
    sheet = sh['sheet']
    info = dict(points=int(len(idx)), faces=int(len(sheet.faces)), frames=None if frames is None else len(frames))
    if len(sheet.faces) == 0:
        return np.zeros((0, 3)), info
    S, _ = trimesh.sample.sample_surface(sheet, SHELL_SAMPLES, seed=seed)
    info['area_cm2'] = round(float(sheet.area) * 1e4, 2)
    return np.asarray(S, np.float64), info


def _rotations24():
    out = []
    for perm in itertools.permutations(range(3)):
        for sg in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i in range(3):
                R[i, perm[i]] = sg[i]
            if np.linalg.det(R) > 0:
                out.append(R)
    return out


ROT24 = _rotations24()


def _pca(X):
    mu = X.mean(0)
    _, V = np.linalg.eigh(np.cov((X - mu).T))
    V = V[:, ::-1]
    if np.linalg.det(V) < 0:
        V[:, 2] *= -1
    return mu, V


def _kabsch(A, B):
    ma, mb = A.mean(0), B.mean(0)
    H = (A - ma).T @ (B - mb)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    return R, mb - R @ ma


def chamfer_mm(A, B):
    if not len(A) or not len(B):
        return float('inf')
    da = cKDTree(B).query(A, k=1)[0]
    db = cKDTree(A).query(B, k=1)[0]
    return float(0.5 * (da.mean() + db.mean()) * 1e3)


def register(A, B, n=REG_N, seed=0):
    """Rigid registration of A onto B: 24 starts (B's PCA frame times the 24 proper axis permutations / sign flips of
    A's PCA frame; centroids aligned), point-to-point ICP (ICP_ITERS iterations), the start with the lowest final
    symmetric chamfer wins. No scale, no identity start. Returns (T 4x4, chamfer_mm)."""
    rng = np.random.default_rng(seed)
    a = A[rng.choice(len(A), min(n, len(A)), replace=False)]
    b = B[rng.choice(len(B), min(n, len(B)), replace=False)]
    tb = cKDTree(b)
    ma, Va = _pca(a)
    mb, Vb = _pca(b)
    best = (np.inf, None)
    for Rp in ROT24:
        R = Vb @ Rp @ Va.T
        t = mb - R @ ma
        for _ in range(ICP_ITERS):
            x = a @ R.T + t
            _, j = tb.query(x, k=1)
            R2, t2 = _kabsch(x, b[j])
            R, t = R2 @ R, R2 @ t + t2
        x = a @ R.T + t
        ch = chamfer_mm(x, b)
        if ch < best[0]:
            best = (ch, (R, t))
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = best[1]
    return T, best[0]


def reg_chamfer(A, B):
    return register(A, B)[1]


def split_test(bundle, obj, partner, shells=None):
    """SPEC section 7 split test on the object's good frames (first half, second half by time) and the partner's
    shell (all its good frames). Pass: chamfer(h1, h2) < min(chamfer(h1, p), chamfer(h2, p))."""
    good = bundle.good_frames(obj)
    if len(good) < 2:
        return dict(testable=False, reason='fewer than 2 good frames')
    h = len(good) // 2
    s1, i1 = route_a_shell(bundle.obs(obj), good[:h])
    s2, i2 = route_a_shell(bundle.obs(obj), good[h:])
    sp = shells.get(partner) if shells else None
    if sp is None:
        sp, _ = route_a_shell(bundle.obs(partner), bundle.good_frames(partner))
    if not len(s1) or not len(s2) or not len(sp):
        return dict(testable=False, reason='empty shell', h1=i1, h2=i2)
    c12 = reg_chamfer(s1, s2)
    c1p = reg_chamfer(s1, sp)
    c2p = reg_chamfer(s2, sp)
    return dict(testable=True, pass_=bool(c12 < min(c1p, c2p)), chamfer_h1_h2_mm=round(c12, 3),
                chamfer_h1_p_mm=round(c1p, 3), chamfer_h2_p_mm=round(c2p, 3), h1=i1, h2=i2,
                frames_h1=h, frames_h2=len(good) - h)


def cross_pairs(shells, good_keys):
    """Every (key, other) registration the cross test of every shell needs (A = key's shell onto B = other's)."""
    out = []
    for key in sorted(shells):
        if not len(shells[key]):
            continue
        for k in good_keys:
            if k != key and k in shells and len(shells[k]):
                out.append((key, k))
    return out


def cross_test(shells, key, good_keys, chamfers=None):
    """SPEC section 7 cross-object test. shells: {(ep, obj): samples}; key = (ep, obj); good_keys: the keys whose
    object passed track sanity (no TRACK_FAIL). Pass: the nearest other shell (registered chamfer) is o's own.
    chamfers: optional {(key, other): registered chamfer mm} computed beforehand (same function, reg_chamfer)."""
    ep, obj = key
    if key not in shells or not len(shells[key]):
        return dict(testable=False, reason='no shell')
    own = [k for k in good_keys if k[1] == obj and k[0] != ep and k in shells and len(shells[k])]
    other = [k for k in good_keys if k[1] != obj and k in shells and len(shells[k])]
    if not own:
        return dict(testable=False, reason='no other good public episode of this object')
    d = {f'ep{k[0]}:{k[1]}': round(chamfers[(key, k)] if chamfers is not None else reg_chamfer(shells[key], shells[k]), 3)
         for k in own + other}
    d_own = min(d[f'ep{k[0]}:{k[1]}'] for k in own)
    d_oth = min(d[f'ep{k[0]}:{k[1]}'] for k in other) if other else float('inf')
    near = min(d, key=d.get)
    return dict(testable=True, pass_=bool(d_own < d_oth), nearest=near, d_own_mm=d_own, d_other_mm=d_oth,
                chamfers_mm=d)
