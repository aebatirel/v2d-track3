"""Marker balls without a radius prior (module M6 of SPEC section 7; SPEC section 10; PREREG A.6; build step B7).

  detect_episode(bundle, sigma=None, objects=None) -> {r_consensus_mm, balls: {obj: [Ball]}, per_object: {...},
                                                       unimodal: {...}, settings, settings_sha256}
      sigma: None (each object's bundle sigma), a float (m, all objects) or {obj: m}.
  detect_object(obs, sigma, T, window, seed=0) -> (accepted [Ball], diagnostics)   one pass on one object
  attach(mesh, balls, obs=None) -> mesh       manifold union of the mesh and every ball (+ a post where the stem rule
                                              of parts.fit_ball finds observed points); report in mesh.metadata
  ball_dict(ball) / balls_from_json(rows)     JSON round trip

Detector (SPEC section 10; the settings are the FROZEN table below, PREREG A.6 "ball detector" and "ball radius
window"; frozen at B7 before any dev run):
  1. points: the object's OWNED points (own = 0), finite; at most 1.5 M (random, seed 0, as ball_probe); one random
     point per 1.5 mm voxel (ball_probe kept the first point per voxel, which favours early frames when the points
     are stored frame by frame; a random representative does not); view directions towards the camera centre.
  2. host-free sphere voting (obs-first ball_probe.py): 15,000 random seed points; per seed the neighbourhoods of
     radius 6, 9, 13, 17 mm in turn (>= 25 points); a free sphere fit (parts.sphere_fit_free; computed here batched,
     same steps; tests check equality); the first neighbourhood whose fit passes is the seed's vote: radius in the
     window and below the neighbourhood radius, inlier share >= 0.6, median residual <= max(1.5 sigma, 0.12 r),
     parts.ball_support of the inliers: convex >= 0.8, cap spread >= 0.12, isotropy >= 0.35, >= 3 frames.
  3. votes are clustered in seed order (a vote joins the first cluster whose centre is within 0.6 max(r, r_cl));
     clusters with >= 3 votes are candidates.
  4. robust fit per candidate: parts.sphere_fit_ransac (radius window, inlier band 3 sigma = the noise band, on the
     voxel points within r_cl + 3 sigma of the cluster centre: the voted sphere and its band; settings v2, B7 dev run 1
     showed that a 2 r_cl neighbourhood lets the fit grow into the host surface around a ball on a short post), then
     parts.sphere_fit_free on its inliers (kept if its radius stays in the window; otherwise the RANSAC sphere, flag
     ransac_only).
  5. acceptance (SPEC section 10 / PREREG A.6): radius in the window; median residual <= 1.5 sigma; >= 3 frames;
     observed cap >= 90 deg (full opening angle of the cap whose spread equals the inliers' spread, spread =
     (1 - cos a) / 2 for half-angle a, so cap = 2 a); convex towards the cameras (>= 0.8 of the points within the
     band face their camera, parts.fit_ball's RANSAC rule); seen in both halves of the episode (frames < T/2 and
     >= T/2). Frames and halves are counted on the raw owned points within the band that face their camera.
  6. overlap suppression (obs-first ball_nms.py): two balls may not overlap (centre distance < r_a + r_b); the one
     with more votes stays (ties: lower residual).
  7. one radius consensus per episode: the median of the accepted radii pooled over all its objects. A second pass
     per object at the consensus radius +-10 % (intersected with the A.6 window, settings v2): votes and the robust fit are bounded to that window (a free fit that
     leaves it is refitted with the radius clamped to the window and the centre free); its accepted balls are added
     where they do not overlap a ball already kept.
  8. diagnostics per candidate and ball (reported only, NEVER used for acceptance; B7 notes, DEVIATIONS): the
     normal deviation and the outside ratio of corner_stats(). B7 synthetic finding: the frozen acceptance tests also
     accept sharp box corners and edges as balls (fit residual 0.8-1.4 sigma <= 1.5 sigma, cap 120-210 deg, convex
     0.87-0.93); these two statistics separate them on the synthetic scene, but adding a test would change the
     pre-registered detector, which this build step may not do (scan-catalogue numbers on markers are known).
  Posts (stems) depend on the host surface, so they are decided in attach() against the candidate mesh, by the stem
  rule of parts.fit_ball (>= 15 observed points in the cylinder from the ball to the nearest host surface point
  within 0.6 r of its axis, and at least twice as many as in either control cylinder one ball diameter to the side).
No radius prior: nothing snaps to a size; the window only bounds the search. GT-free: reads only its arguments.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from gmg import guard

# Frozen at B7 (2026-10-30/31) before the first dev run; the values are PREREG A.6 / SPEC section 10 or the obs-first
# ball_probe / ball_nms settings SPEC section 10 names. Changing any value needs a PREREG F amendment.
FROZEN = dict(
    radius_window_m=[0.0015, 0.0125],     # A.6 ball radius window (generic: passive markers about 3-25 mm diameter)
    seeds=15000,                          # A.6 ball detector (seed count informed: changed once after a first run)
    min_frames=3,                         # A.6
    resid_max_sigma=1.5,                  # A.6
    cap_min_deg=90.0,                     # A.6
    both_halves=True,                     # A.6
    second_pass_rel=0.10,                 # A.6 second pass at consensus +-10 %
    convex_min=0.8,                       # SPEC 10 convex towards the cameras (ball_probe / parts.fit_ball value)
    vote_vox_m=0.0015,                    # SPEC 10 1.5 mm voxels
    max_points=1500000,                   # ball_probe cap
    vote_nbhd_m=[0.006, 0.009, 0.013, 0.017],   # ball_probe
    vote_min_pts=25,                      # ball_probe
    vote_inlier_min=0.6,                  # ball_probe
    vote_res_sigma=1.5,                   # ball_probe RES_K (x the episode's own floor; here x sigma)
    vote_res_rel=0.12,                    # ball_probe
    vote_convex_min=0.8,                  # ball_probe
    vote_spread_min=0.12,                 # ball_probe
    vote_iso_min=0.35,                    # ball_probe
    vote_min_frames=3,                    # ball_probe
    cluster_rel=0.6,                      # ball_probe
    cluster_min_votes=3,                  # ball_probe SUPMIN
    fit_band_sigma=3.0,                   # noise band (A.6 / SPEC 8): RANSAC inlier band, frames/halves/convex band
    fit_nbhd='r_cluster + fit band',      # v2: robust fit on the points within r_cl + 3 sigma of the cluster centre
                                          # (v1: 2 r_cl, which let the fit absorb the host surface: B7 dev run 1)
    settings_version=2,
    ransac_hypotheses=400,                # parts.sphere_fit_ransac default
    ransac_top=5,                         # parts.sphere_fit_ransac default
    consensus='median of accepted radii pooled over the episode objects',
    nms='centre distance < r_a + r_b: the ball with more votes stays',
    stem_min=15,                          # parts.fit_ball stem_min default
    stem_r_rel=0.6,                       # parts.fit_ball: stem points within 0.6 r of the axis
    sphere_segments=24,                   # attach: PL.mf_sphere(seg=24) as parts.fit_ball
    unimodal_band=0.15,                   # PREREG B.4 (reported only, dev signal)
)
SETTINGS_SHA256 = hashlib.sha256(json.dumps(FROZEN, sort_keys=True).encode()).hexdigest()
VOX_FIT = 0.0015                          # parts.VOX (sphere_fit_free inlier floor)


def consts():
    o = {k: 'generic:obs-first ball_probe / ball_nms setting named by SPEC section 10' for k in FROZEN}
    for k in ('radius_window_m',):
        o[k] = 'generic:PREREG A.6 ball radius window (passive markers about 3-25 mm diameter)'
    for k in ('min_frames', 'resid_max_sigma', 'cap_min_deg', 'both_halves', 'second_pass_rel'):
        o[k] = 'generic:PREREG A.6 ball detector'
    o['seeds'] = 'informed:ball detector seed count (PREREG A.6: changed once after a first run)'
    for k in ('fit_band_sigma',):
        o[k] = 'generic:PREREG A.6 noise band 3 sigma'
    o['fit_nbhd'] = 'informed:B7 dev run 1 (ep2: robust fits grew from vote radii 5-7 mm to 10-12.5 mm through host points)'
    o['settings_version'] = 'generic:settings file version'
    for k in ('ransac_hypotheses', 'ransac_top', 'stem_min', 'stem_r_rel', 'sphere_segments'):
        o[k] = 'generic:autokit parts default'
    o['unimodal_band'] = 'generic:PREREG B.4 unimodal radius band (reported only)'
    for k, v in FROZEN.items():
        guard.constant(f'marker_{k}', v, o[k])
    guard.constant('marker_settings_sha256', SETTINGS_SHA256, 'generic:hash of the frozen marker settings (B7)')
    guard.constant('marker_diag_pca_radius_m', 0.003, 'generic:diagnostic only (corner_stats normals, 2 x 1.5 mm voxel)')
    guard.constant('marker_diag_max_inliers', 300, 'generic:diagnostic only (corner_stats subsample)')
    return dict(FROZEN)


@dataclass
class Ball:
    c: list                      # centre (object frame, m)
    r: float                     # radius (m)
    frames: int                  # frames with supporting raw points
    resid: float                 # median |d - r| of the fit inliers (m)
    cap_deg: float               # full opening angle of the observed cap
    stem: object = None          # decided in attach() against the host mesh
    votes: int = 0               # seed votes of its cluster
    convex: float = 0.0
    iso: float = 0.0
    halves: list = field(default_factory=list)   # supporting frames in the first / second half
    n_fit: int = 0               # inlier voxel points of the fit
    fit: str = 'free'            # 'free' or 'ransac_only'
    pass_: int = 1               # detector pass (1 free window, 2 consensus window)
    normal_dev_deg: object = None    # diagnostic only (corner_stats), never used for acceptance
    outside_ratio: object = None     # diagnostic only (corner_stats), never used for acceptance


def ball_dict(b):
    d = asdict(b)
    d['c'] = [float(x) for x in d['c']]
    for k in ('r', 'resid', 'cap_deg', 'convex', 'iso'):
        d[k] = float(d[k])
    d['r_mm'] = round(d['r'] * 1e3, 3)
    return d


def balls_from_json(rows):
    keys = Ball.__dataclass_fields__.keys()
    return [Ball(**{k: v for k, v in r.items() if k in keys}) for r in rows]


def _parts():
    from autokit import parts as PT
    return PT


# ------------------------------------------------------------------------------------------------ batched fits
def _solve(A, b):
    """Batched least squares via the pseudo-inverse of the normal matrix (S, k, k) @ (S, k)."""
    return np.einsum('sij,sj->si', np.linalg.pinv(A), b)


def batch_free_fit(Q, M, window=None):
    """parts.sphere_fit_free on S padded neighbourhoods at once. Q (S, n, 3), M (S, n) bool (valid points).
    window: None (free radius) or (lo, hi): a fit whose radius leaves the window is refitted with the radius clamped
    and the centre free (second pass). Returns c (S,3), r (S,), res (S,), keep (S,n), ok (S,)."""
    S, n, _ = Q.shape
    Mf = M.astype(np.float64)
    A = np.concatenate([2 * Q, np.ones((S, n, 1))], -1) * Mf[..., None]
    b = (Q ** 2).sum(-1) * Mf
    sol = _solve(np.einsum('sni,snj->sij', A, A), np.einsum('sni,sn->si', A, b))
    c = sol[:, :3].copy(); r2 = sol[:, 3] + (c ** 2).sum(1)
    ok = np.isfinite(r2) & (r2 > 0)
    r = np.sqrt(np.where(ok, r2, 1.0))
    keep = M.copy()

    def gn(c, r, keep, ok, fix_r=False):
        W = keep.astype(np.float64)
        for _ in range(10):
            D = Q - c[:, None]
            dn = np.maximum(np.linalg.norm(D, axis=2), 1e-9)
            res = dn - r[:, None]
            if fix_r:
                J = -D / dn[..., None]
            else:
                J = np.concatenate([-D / dn[..., None], -np.ones((S, n, 1))], -1)
            JW = J * W[..., None]
            step = _solve(np.einsum('sni,snj->sij', JW, J), np.einsum('sni,sn->si', JW, -res))
            c = c + step[:, :3]
            if not fix_r:
                r = r + step[:, 3]
            bad = ~(np.all(np.isfinite(c), 1) & np.isfinite(r)) | (r <= 0)
            ok = ok & ~bad
            c = np.where(np.isfinite(c), c, 0.0); r = np.where(np.isfinite(r) & (r > 0), r, 1.0)
            if not ok.any() or float(np.nanmax(np.abs(step[ok]))) < 1e-10:   # converged (speed only; same fixed point)
                break
        return c, r, ok

    for rnd in range(2):
        c, r, ok = gn(c, r, keep, ok)
        res = np.abs(np.linalg.norm(Q - c[:, None], axis=2) - r[:, None])
        if rnd == 0:
            med = np.nanmedian(np.where(M, res, np.nan), axis=1)
            keep = M & (res < np.maximum(3 * med, VOX_FIT)[:, None])
            ok &= keep.sum(1) >= 10
    if window is not None:
        lo, hi = window
        out = ok & ((r < lo) | (r > hi))
        if out.any():
            rc = np.clip(r, lo, hi)
            c2, _, ok2 = gn(c, rc, keep, ok, fix_r=True)
            c = np.where(out[:, None], c2, c); r = np.where(out, rc, r); ok = np.where(out, ok2, ok)
            res = np.abs(np.linalg.norm(Q - c[:, None], axis=2) - r[:, None])
    resk = np.nanmedian(np.where(keep, res, np.nan), axis=1)
    return c, r, resk, keep, ok


def batch_support(Q, V, F, keep, c, r):
    """parts.ball_support for S neighbourhoods at once (statistics over the KEEP points)."""
    W = keep.astype(np.float64)
    k = np.maximum(W.sum(1), 1.0)
    D = Q - c[:, None]
    u = D / np.maximum(np.linalg.norm(D, axis=2, keepdims=True), 1e-12)
    m = (u * W[..., None]).sum(1) / k[:, None]
    mn = np.linalg.norm(m, axis=1)
    spread = 1 - mn
    convex = ((np.einsum('sni,sni->sn', u, V) > 0) * W).sum(1) / k
    a = m / np.maximum(mn, 1e-9)[:, None]
    T = u - np.einsum('sni,si->sn', u, a)[..., None] * a[:, None]
    Tm = (T * W[..., None]).sum(1) / k[:, None]
    X = (T - Tm[:, None]) * W[..., None]
    cov = np.einsum('sni,snj->sij', X, X) / np.maximum(k - 1, 1.0)[:, None, None]
    ev = np.linalg.eigvalsh(cov)[:, 1:]
    iso = ev[:, 0] / np.maximum(ev[:, 1], 1e-12)
    Fk = np.where(keep, F, -1)
    Fs = np.sort(Fk, axis=1)
    newf = np.ones_like(Fs, bool); newf[:, 1:] = Fs[:, 1:] != Fs[:, :-1]
    frames = (newf & (Fs >= 0)).sum(1)
    return dict(spread=spread, convex=convex, iso=iso, frames=frames)


# ------------------------------------------------------------------------------------------------ one pass
def _owned_points(obs, K, rng):
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    F = np.asarray(obs['frame']).astype(np.int64)
    own = np.asarray(obs.get('own', np.zeros(len(P), np.uint8)))
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1) & (own == 0)
    P, C, F = P[ok], C[ok], F[ok]
    if len(P) > K['max_points']:
        s = np.sort(rng.choice(len(P), K['max_points'], replace=False)); P, C, F = P[s], C[s], F[s]
    perm = rng.permutation(len(P))
    key = np.floor(P[perm] / K['vote_vox_m']).astype(np.int64)
    _, ui = np.unique(key, axis=0, return_index=True)
    iv = np.sort(perm[ui])
    Pv, Cv, Fv = P[iv], C[iv], F[iv]
    V = Cv - Pv; V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-12)
    return P, C, F, Pv, V, Fv


def _votes(Pv, V, Fv, tree, seeds, sigma, window, K, chunk=1000):
    """ball_probe voting, batched. Returns the accepted votes in seed order: list of (c, r, res, spread, frames)."""
    lo, hi = window
    bounded = None if (lo, hi) == tuple(K['radius_window_m']) else (lo, hi)
    res_lim = K['vote_res_sigma'] * sigma
    done = np.zeros(len(seeds), bool)
    vote = [None] * len(seeds)
    for R in K['vote_nbhd_m']:
        todo = np.nonzero(~done)[0]
        if len(todo) == 0:
            break
        nbs = tree.query_ball_point(Pv[seeds[todo]], R)
        lens = np.array([len(x) for x in nbs])
        sel = np.nonzero(lens >= K['vote_min_pts'])[0]
        sel = sel[np.argsort(lens[sel], kind='stable')]         # chunks of similar size: less padding (speed only)
        for s0 in range(0, len(sel), chunk):
            part = sel[s0:s0 + chunk]
            nmax = int(lens[part].max())
            idx = np.zeros((len(part), nmax), np.int64); M = np.zeros((len(part), nmax), bool)
            for i, j in enumerate(part):
                idx[i, :lens[j]] = nbs[j]; M[i, :lens[j]] = True
            Q = Pv[idx]
            c, r, res, keep, ok = batch_free_fit(Q, M, bounded)
            sup = batch_support(Q, V[idx], Fv[idx], keep, c, r)
            frac = keep.sum(1) / np.maximum(M.sum(1), 1)
            acc = (ok & (r >= lo) & (r <= hi) & (r < R) & (frac >= K['vote_inlier_min'])
                   & (res <= np.maximum(res_lim, K['vote_res_rel'] * r))
                   & (sup['convex'] >= K['vote_convex_min']) & (sup['spread'] >= K['vote_spread_min'])
                   & (sup['iso'] >= K['vote_iso_min']) & (sup['frames'] >= K['vote_min_frames']))
            for i in np.nonzero(acc)[0]:
                t = todo[part[i]]
                vote[t] = (c[i].copy(), float(r[i]), float(res[i]), float(sup['spread'][i]), int(sup['frames'][i]))
                done[t] = True
    return [v for v in vote if v is not None]


def _clusters(votes, K):
    """ball_probe clustering (sequential, seed order)."""
    clusters = []
    for c, r, res, sp, fr in votes:
        for cl in clusters:
            if np.linalg.norm(cl['c'] - c) < K['cluster_rel'] * max(r, cl['r']):
                cl['m'].append((c, r, sp, fr)); cl['c'] = np.mean([m[0] for m in cl['m']], 0)
                cl['r'] = float(np.median([m[1] for m in cl['m']])); break
        else:
            clusters.append(dict(c=c, r=r, m=[(c, r, sp, fr)]))
    return clusters


def _robust(cl, Pv, V, Fv, tree, raw_tree, P, C, F, sigma, window, T, K, seed):
    """Robust fit and acceptance of one candidate cluster -> (Ball or None, info)."""
    PT = _parts()
    lo, hi = window
    tol = K['fit_band_sigma'] * sigma
    nb = np.asarray(tree.query_ball_point(cl['c'], cl['r'] + tol), np.int64)   # the voted sphere and its band
    info = dict(c_vote=[round(float(x), 5) for x in cl['c']], r_vote_mm=round(cl['r'] * 1e3, 3), votes=len(cl['m']),
                n_nbhd=int(len(nb)))
    if len(nb) < 10:
        info['rejected'] = 'few_points'; return None, info
    Q, Vq, Fq = Pv[nb], V[nb], Fv[nb]
    fit = PT.sphere_fit_ransac(Q, Vq, lo, hi, tol, n_hyp=K['ransac_hypotheses'], top=K['ransac_top'],
                               rng=np.random.default_rng(seed))
    if fit is None:
        info['rejected'] = 'no_fit'; return None, info
    c, r, res, inl = fit
    how = 'ransac_only'
    free = PT.sphere_fit_free(Q[inl]) if inl.sum() >= 10 else None
    if free is not None and lo <= free[1] <= hi:
        c, r, res = free[0], free[1], free[2]
        sel = np.nonzero(inl)[0][free[3]]
        how = 'free'
    else:
        sel = np.nonzero(inl)[0]
    sup = PT.ball_support(Q[sel], Vq[sel], Fq[sel], c, r)
    near = np.abs(np.linalg.norm(Q - c, axis=1) - r) < tol
    convex = float(np.mean(np.einsum('ij,ij->i', Q[near] - c, Vq[near]) > 0)) if near.any() else 0.0
    spread = float(sup['spread'])
    cap = math.degrees(2 * math.acos(float(np.clip(1 - 2 * spread, -1.0, 1.0))))
    rawi = np.asarray(raw_tree.query_ball_point(c, r + tol), np.int64)
    if len(rawi):
        X = P[rawi]; dd = np.linalg.norm(X - c, axis=1)
        m = (np.abs(dd - r) < tol) & (np.einsum('ij,ij->i', X - c, C[rawi] - X) > 0)
        fr = np.unique(F[rawi][m])
    else:
        fr = np.zeros(0, np.int64)
    half = T / 2.0
    halves = [int(np.sum(fr < half)), int(np.sum(fr >= half))]
    ndev, outr = corner_stats(Pv, V, tree, c, r, tol, np.random.default_rng(seed))
    ball = Ball(c=[float(x) for x in c], r=float(r), frames=int(len(fr)), resid=float(res), cap_deg=round(cap, 3),
                votes=len(cl['m']), convex=round(convex, 4), iso=float(sup['iso']), halves=halves, n_fit=int(len(sel)),
                fit=how, normal_dev_deg=ndev, outside_ratio=outr)
    info.update(ball_dict(ball))
    why = None
    if not lo <= r <= hi:
        why = 'radius'
    elif res > K['resid_max_sigma'] * sigma:
        why = 'residual'
    elif len(fr) < K['min_frames']:
        why = 'frames'
    elif cap < K['cap_min_deg']:
        why = 'cap'
    elif convex < K['convex_min']:
        why = 'not_convex'
    elif K['both_halves'] and min(halves) == 0:
        why = 'one_half'
    if why:
        info['rejected'] = why
        return None, info
    return ball, info


def corner_stats(Pv, V, tree, c, r, tol, rng, n_max=300, pca_r=0.003):
    """DIAGNOSTIC ONLY (reported, never used for acceptance; B7 notes and DEVIATIONS): two GT-free statistics that
    separate a sphere from a sharp corner or edge that a sphere fit also explains within the frozen residual limit
    (synthetic finding, B7). normal_dev_deg: median angle between the local surface normal (PCA of the voxel points
    within 3 mm) and the fitted radial direction over at most 300 fit inliers (the normal-compatibility test of
    Schnabel et al. 2007's efficient RANSAC; a sphere's normals are radial, a corner's faces are flat).
    outside_ratio: camera-facing points at r + band < d < 2 r from the centre per camera-facing point within the band
    (a ball stands clear of its surroundings except for its post; a corner's faces continue past the fitted sphere)."""
    nb = np.asarray(tree.query_ball_point(c, 2 * r), np.int64)
    if len(nb) == 0:
        return None, None
    X = Pv[nb]; D = X - c; d = np.linalg.norm(D, axis=1)
    face = np.einsum('ij,ij->i', D, V[nb]) > 0
    inl = np.nonzero(face & (np.abs(d - r) < tol))[0]
    out = int(np.sum(face & (d > r + tol)))
    outr = round(out / max(len(inl), 1), 4)
    if len(inl) > n_max:
        inl = np.sort(rng.choice(inl, n_max, replace=False))
    devs = []
    for q in tree.query_ball_point(X[inl], pca_r):
        devs.append(q)
    ang = []
    for j, q in zip(inl, devs):
        if len(q) < 6:
            continue
        Y = Pv[q]; Y = Y - Y.mean(0)
        n = np.linalg.eigh(Y.T @ Y)[1][:, 0]
        ang.append(math.degrees(math.acos(min(1.0, abs(float(n @ D[j])) / max(d[j], 1e-12)))))
    return (round(float(np.median(ang)), 3) if ang else None), outr


def _nms(balls, keep_first=()):
    """ball_nms: no two balls overlap; more votes first (ties: lower residual). keep_first: balls kept already."""
    kept = list(keep_first)
    for b in sorted(balls, key=lambda b: (-b.votes, b.resid)):
        if all(np.linalg.norm(np.subtract(b.c, k.c)) >= b.r + k.r for k in kept):
            kept.append(b)
    return kept[len(keep_first):]


def detect_object(obs, sigma, T, window=None, seed=0, pass_=1, keep_first=()):
    K = consts()
    window = tuple(K['radius_window_m']) if window is None else tuple(window)
    rng = np.random.default_rng(seed)
    t0 = time.time()
    P, C, F, Pv, V, Fv = _owned_points(obs, K, rng)
    diag = dict(points=int(len(P)), voxels=int(len(Pv)), window_mm=[round(w * 1e3, 4) for w in window], pass_=pass_)
    if len(Pv) < K['vote_min_pts']:
        diag['skipped'] = 'too few points'
        return [], diag
    tree = cKDTree(Pv)
    seeds = rng.choice(len(Pv), min(K['seeds'], len(Pv)), replace=False)
    votes = _votes(Pv, V, Fv, tree, seeds, sigma, window, K)
    cls = _clusters(votes, K)
    strong = [cl for cl in cls if len(cl['m']) >= K['cluster_min_votes']]
    strong.sort(key=lambda cl: -len(cl['m']))
    raw_tree = cKDTree(P)
    acc, infos = [], []
    for i, cl in enumerate(strong):
        b, info = _robust(cl, Pv, V, Fv, tree, raw_tree, P, C, F, sigma, window, T, K, seed=1000 * pass_ + i)
        infos.append(info)
        if b is not None:
            b.pass_ = pass_
            acc.append(b)
    kept = _nms(acc, keep_first)
    diag.update(seeds=int(len(seeds)), votes=len(votes), clusters=len(cls), candidates=len(strong),
                accepted=len(acc), after_nms=len(kept), candidates_info=infos, sec=round(time.time() - t0, 1))
    return kept, diag


def _sigmas(bundle, sigma, objects):
    if sigma is None:
        return {o: bundle.sigma(o) for o in objects}
    if isinstance(sigma, dict):
        return {o: float(sigma[o]) for o in objects}
    return {o: float(sigma) for o in objects}


def detect_episode(bundle, sigma=None, objects=None):
    K = consts()
    objects = list(bundle.objects if objects is None else objects)
    sig = _sigmas(bundle, sigma, objects)
    T = int(bundle.meta['T'])
    balls, per = {}, {}
    for o in objects:
        b, d = detect_object(bundle.obs(o), sig[o], T, pass_=1)
        balls[o] = b; per[o] = dict(pass1=d)
    radii = [b.r for o in objects for b in balls[o]]
    rc = float(np.median(radii)) if radii else None
    if rc is not None:
        guard.constant(f'marker_r_consensus_m_ep{bundle.meta.get("ep")}_{bundle.meta.get("split")}', rc,
                       'fitted:own accepted ball radii of this episode (SPEC section 10 consensus)')
        lo, hi = K['radius_window_m']                                  # the A.6 window bounds every pass (v2)
        win = (max(lo, rc * (1 - K['second_pass_rel'])), min(hi, rc * (1 + K['second_pass_rel'])))
        for o in objects:
            b2, d2 = detect_object(bundle.obs(o), sig[o], T, window=win, pass_=2, keep_first=balls[o])
            per[o]['pass2'] = d2
            balls[o] = balls[o] + b2
    allr = [b.r for o in objects for b in balls[o]]
    uni = None
    if allr:
        med = float(np.median(allr))
        share = float(np.mean(np.abs(np.asarray(allr) - med) <= K['unimodal_band'] * med))
        uni = dict(n=len(allr), median_mm=round(med * 1e3, 3), share_within_15pct=round(share, 4),
                   unimodal_b4=bool(share >= 0.8))
    return dict(schema='gmg-markers/1', split=bundle.meta.get('split'), ep=bundle.meta.get('ep'),
                tier=bundle.meta.get('tier'), objects=objects,
                sigma_mm={o: round(sig[o] * 1e3, 4) for o in objects},
                r_consensus_mm=None if rc is None else round(rc * 1e3, 4),
                balls={o: [ball_dict(b) for b in balls[o]] for o in objects},
                n_balls={o: len(balls[o]) for o in objects}, unimodal=uni, per_object=per,
                settings=dict(FROZEN), settings_sha256=SETTINGS_SHA256)


# ------------------------------------------------------------------------------------------------ attach
def attach(mesh, balls, obs=None):
    """Manifold union of MESH (watertight) with every ball; a post (cylinder to the nearest mesh surface point)
    where parts.fit_ball's stem rule finds observed points (needs obs). Returns a new trimesh with
    metadata['balls'] = per-ball report. Unobserved balls are never added (only what balls holds)."""
    import trimesh
    PT = _parts()
    PL = PT.PL
    K = dict(FROZEN)
    if isinstance(balls, list) and balls and isinstance(balls[0], dict):
        balls = balls_from_json(balls)
    if not balls:
        out = mesh.copy(); out.metadata['balls'] = []
        return out
    base = PT.to_mf(mesh)
    pq = trimesh.proximity.ProximityQuery(mesh)
    Pv = None
    if obs is not None:
        P = np.asarray(obs['pts'], np.float64)
        own = np.asarray(obs.get('own', np.zeros(len(P), np.uint8)))
        P = P[np.all(np.isfinite(P), 1) & (own == 0)]
        key = np.floor(P / K['vote_vox_m']).astype(np.int64)
        _, ui = np.unique(key, axis=0, return_index=True)
        Pv = P[np.sort(ui)]
        tree = cKDTree(Pv)
    solids, rep = [base], []
    for b in balls:
        c = np.asarray(b.c, np.float64); r = float(b.r)
        solids.append(PL.mf_sphere(c, r, seg=K['sphere_segments']))
        sp = pq.on_surface(c[None])[0][0]
        L_ = float(np.linalg.norm(sp - c))
        inside = bool(pq.signed_distance(c[None])[0] > 0)            # trimesh: > 0 inside
        row = dict(c=[float(x) for x in c], r_mm=round(r * 1e3, 3), gap_mm=round((L_ - r) * 1e3, 3) * (-1 if inside else 1),
                   stem=False)
        if Pv is not None and not inside and L_ - r > 2 * VOX_FIT:
            ax = (sp - c) / max(L_, 1e-12); rs = K['stem_r_rel'] * r

            def stem_pts(a0):
                X = Pv[tree.query_ball_point(a0 + 0.5 * L_ * ax, 0.5 * L_ + rs)] - a0
                if len(X) == 0:
                    return np.zeros(0)
                tp = X @ ax; pp = np.linalg.norm(X - tp[:, None] * ax, axis=1)
                return pp[(pp < rs) & (tp > r + 0.5 * VOX_FIT) & (tp < L_ - 2 * VOX_FIT)]
            pin = stem_pts(c)
            side = np.cross(ax, PT.L.frame_from(ax)[0]); side /= np.linalg.norm(side)
            n_ctl = max(len(stem_pts(c + (2 * r + rs) * side)), len(stem_pts(c - (2 * r + rs) * side)))
            row.update(stem_pts=int(len(pin)), stem_ctl=int(n_ctl))
            if len(pin) >= K['stem_min'] and len(pin) >= 2 * n_ctl:
                sr = float(np.clip(np.median(pin), VOX_FIT, rs))
                solids.append(PL.mf_cylinder(c, sp + sr * ax, sr))
                row.update(stem=True, stem_r_mm=round(sr * 1e3, 3))
        rep.append(row)
    out = PT.from_mf(PT.mf_union(solids))
    out.metadata['balls'] = rep
    return out
