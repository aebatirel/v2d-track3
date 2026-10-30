"""Structure hypotheses (module M5 of SPEC section 7; SPEC sections 8 and 10; PREREG A.6; build step B7).

  hypotheses(obs, state=None, sigma=None, *, axis_search=True) -> dict
      obs: a bundle object dict (pts, cam, frame, own, lo, vox, hits, free, state); state: the 3-state grid
      (default obs['state']); sigma: the object-episode noise sigma in m (PREREG A.2; required).
      Returns {sigma_mm, n_points, axis, rotc_sigma, lathe_mad_sigma, mirrors, planes, plane_pairs, repeats, accepted,
      timing_s}. GT-free: it reads nothing but its arguments.

What each hypothesis is (all from the object's OWNED points, voxel-downsampled at 2 mm, at most 60,000 of them):
  axis      body-of-revolution axis: candidates lathe_obs.fit_axis + parts.refine_axis_rot (line complex placement,
            rotational self-consistency) and parts.axis_search (rim flatness + rotational consistency; rim window
            E1 = 0.05 s of PREREG A.6b); the candidate with the lower rotational consistency wins.
            rotc = lathe_obs.rot_consistency (its defaults: rotations 45/90/135 deg, 80 % trimmed mean NN distance)
            on one fixed subsample; accepted (P-SYM lathe / rotation) if rotc <= 3 sigma (PREREG A.6 symmetry
            acceptance). lathe_mad (sym_probe's partial-view lathe score: median over height bins of the MAD across
            azimuth sectors of the 90th-percentile radius) and the observed / FREE shares of the rotated points
            (rot_observed, rot_free_viol) are reported, not used (a flat plate passes rotc alone: B7 notes).
  mirrors   sym_probe search: 400 hemisphere normals, offset by pairing, ranked by residual + 0.02 m x FREE share,
            top 3 distinct planes (> 20 deg apart), local perturbation (12 normals at 4 deg, then at 1.5 deg), then a
            Nelder-Mead refinement of (two tilt angles, offset) on the same ranking score (the probe's pairing offset
            stalls on boxy shapes: points on faces parallel to the normal slide onto themselves and hide the offset
            error; synthetic finding, B7 notes). Evaluation (on a 20,000 subsample):
            only the points the reflection MOVES by more than the noise band 3 sigma count; observed share = share
            of them landing in a voxel with any evidence (hits + free > 0, sym_probe's 'observed'); FREE share =
            share landing in a FREE voxel (PREREG A.2 state); residual = 80 % trimmed mean NN distance of the moved
            points that land in observed voxels. Accepted if residual <= 3 sigma, observed share >= 0.7, FREE share
            < 0.05 (PREREG A.6) and at least half the points move (otherwise the plane is degenerate: it holds the
            surface, e.g. one face of a plate, and completes nothing).
  planes    parts.segment_planes on camera-oriented normals (inlier band 3 sigma, the parts plate_set defaults
            otherwise); per plane: outward normal (towards the cameras), offset, in-plane extents, rms.
  plane_pairs  two parallel planes seen from opposite sides with the material between them, overlapping footprints,
            gap in the slab two-face window 3-25 mm (PREREG A.6, informed): a plate (thickness, mid plane).
  repeats   discrete rotations C_n, n = 2..6, about the axis candidate and the three principal axes; axis position
            by pairing (least squares of q = R (p - c) + c on the best half of the pairs), direction by the same
            perturbation search as the mirrors, then Nelder-Mead on (two tilts, two position offsets); same
            evaluation and acceptance as a mirror.
Constants are registered through guard.constant with their origins (PREREG A.6 rows, or generic search settings
carried from the obs-first probes). Code copied from the obs-first design probes (sym_probe.py, rot_probe.py) is
marked; the probes' outputs are never read.
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy.spatial import cKDTree

from gmg import guard
from gmg.bundle import STATE_FREE

ORDERS = (2, 3, 4, 5, 6)


def consts():
    c = guard.constant
    return dict(
        vox=c('struct_vox_m', 0.002, 'generic:obs-first sym_probe / rot_probe voxel downsample'),
        max_pts=c('struct_max_points', 60000, 'generic:obs-first probe cap (numerical)'),
        rot_trim=c('rot_consistency_trim', 0.8, 'generic:lathe_obs.rot_consistency default'),
        rot_angles=c('rot_consistency_angles_deg', [45, 90, 135], 'generic:lathe_obs.rot_consistency default'),
        rot_sub=c('rot_consistency_subsample', 20000, 'generic:lathe_obs.fit_axis subsample'),
        acc_rotc=c('sym_accept_rotc_sigma', 3.0, 'generic:PREREG A.6 symmetry acceptance (rotational consistency)'),
        acc_res=c('sym_accept_resid_sigma', 3.0, 'generic:PREREG A.6 symmetry acceptance (mirror residual)'),
        acc_obs=c('sym_accept_observed_share', 0.7, 'generic:PREREG A.6 symmetry acceptance (observed share)'),
        acc_free=c('sym_accept_free_share', 0.05, 'generic:PREREG A.6 symmetry acceptance (free share)'),
        band=c('noise_band_sigma', 3.0, 'generic:PREREG A.6 / SPEC section 8 noise band 3 sigma'),
        moved_min=c('sym_moved_min_share', 0.5, 'generic:a symmetry must move at least half the points'),
        trim=c('sym_resid_trim', 0.8, 'generic:obs-first sym_probe trimmed mean'),
        n_normals=c('mirror_search_normals', 400, 'generic:obs-first sym_probe search'),
        sub_search=c('sym_search_subsample', 6000, 'generic:obs-first sym_probe search'),
        sub_eval=c('sym_eval_subsample', 20000, 'generic:obs-first sym_probe evaluation'),
        distinct=c('mirror_distinct_deg', 20.0, 'generic:obs-first sym_probe search'),
        top=c('mirror_top', 3, 'generic:obs-first sym_probe search'),
        min_obs_search=c('mirror_search_min_observed', 0.3, 'generic:obs-first sym_probe search'),
        free_w=c('mirror_search_free_weight_m', 0.02, 'generic:obs-first sym_probe ranking weight'),
        perturb=c('sym_perturb_deg', [4.0, 1.5], 'generic:obs-first sym_probe refinement'),
        perturb_n=c('sym_perturb_n', 12, 'generic:obs-first sym_probe refinement'),
        nm_step=c('sym_nm_step', 2.0, 'generic:numerical refinement (initial simplex 2 deg / 2 mm)'),
        nm_xatol=c('sym_nm_xatol', 0.02, 'generic:numerical refinement (deg / mm)'),
        nm_maxfev=c('sym_nm_maxfev', 400, 'generic:numerical refinement'),
        pair_iters=c('sym_pairing_iters', 4, 'generic:numerical refinement (sym_probe refine_offset passes)'),
        rim_w=c('axis_search_rim_w_s', 0.05, 'generic:PREREG A.6b E1 (lathe.rim_w) = 0.05 s'),
        plane_min=c('plane_min_pts', 300, 'generic:autokit parts plate_set default'),
        plane_max=c('plane_max', 4, 'generic:autokit parts plate_set default'),
        plane_seeds=c('plane_seeds', 200, 'generic:autokit parts plate_set default'),
        plane_deg=c('plane_deg', 30.0, 'generic:autokit parts plate_set default'),
        plane_conn=c('plane_conn_vox_m', 0.003, 'generic:autokit parts plate_set default'),
        slab=c('slab_two_face_thickness_m', [0.003, 0.025], 'informed:slab two-face thickness (PREREG A.6)'),
        pair_overlap=c('plane_pair_overlap_min', 0.5, 'generic:footprints of a plate\'s two faces overlap'),
        orders=c('repeat_orders', list(ORDERS), 'generic:discrete rotations C2..C6'),
    )


def _libs():
    from autokit import parts as PT
    return PT, PT.L


# ------------------------------------------------------------------------------------------------ helpers
def fib(n, hemi=True):
    """Fibonacci directions (copied from obs-first sym_probe.py)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - (1 if hemi else 2) * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def vox_down(P, C, v):
    """First point per voxel of size v (sym_probe.vox_down)."""
    k = np.floor(P / v).astype(np.int64)
    _, idx = np.unique(k, axis=0, return_index=True)
    return P[idx], C[idx]


def lathe_score(P, c, a, dh=0.003, nsec=24):
    """sym_probe.lathe_score (copied): median over height bins of the MAD across azimuth sectors of the q90 outer
    radius (cells with >= 5 points, bins with >= 4 sectors), mm; mean sector coverage; bins used; bins."""
    _, L = _libs()
    e1, e2, d = L.frame_from(a); X = P - c
    h = X @ d; x = X @ e1; y = X @ e2; r = np.hypot(x, y); th = np.arctan2(y, x)
    hb = np.floor((h - h.min()) / dh).astype(int); sb = ((th + np.pi) / (2 * np.pi) * nsec).astype(int) % nsec
    key = hb * nsec + sb
    o = np.argsort(key, kind='stable'); ks, st, cnt = np.unique(key[o], return_index=True, return_counts=True)
    cell = {}
    for k, s0, cn in zip(ks, st, cnt):
        if cn >= 5:
            cell[int(k)] = np.percentile(r[o[s0:s0 + cn]], 90)
    byh = {}
    for k, v in cell.items():
        byh.setdefault(k // nsec, []).append(v)
    mads, secs = [], []
    for _, vs in byh.items():
        secs.append(len(vs))
        if len(vs) >= 4:
            vs = np.array(vs); mads.append(np.median(np.abs(vs - np.median(vs))))
    return (float(np.median(mads)) * 1e3 if mads else None, float(np.mean(np.array(secs) / nsec)) if secs else 0.0,
            len(mads), len(byh))


class Grid:
    """Lookup of hits, free and state at points (object frame)."""

    def __init__(self, obs, state):
        self.lo = np.asarray(obs['lo'], np.float64); self.vox = float(obs['vox'])
        self.hits = np.asarray(obs['hits']); self.free = np.asarray(obs['free']); self.state = np.asarray(state)
        self.shape = np.array(self.hits.shape)

    def at(self, X):
        ijk = np.floor((X - self.lo) / self.vox).astype(np.int64)
        ok = np.all((ijk >= 0) & (ijk < self.shape), 1)
        h = np.zeros(len(X), np.int64); f = np.zeros(len(X), np.int64); s = np.zeros(len(X), np.uint8)
        i = ijk[ok]
        h[ok] = self.hits[i[:, 0], i[:, 1], i[:, 2]]; f[ok] = self.free[i[:, 0], i[:, 1], i[:, 2]]
        s[ok] = self.state[i[:, 0], i[:, 1], i[:, 2]]
        return ok, h, f, s


def sym_eval(P, Q, tree, grid, band_m, trim):
    """Evaluate a symmetry T given P (points) and Q = T(P). Moved = |Q - P| > band_m. Returns dict(resid (m),
    observed, free, moved) with shares over the moved points (see the module doc)."""
    mv = np.linalg.norm(Q - P, axis=1) > band_m
    n_mv = int(mv.sum())
    out = dict(moved=n_mv / max(len(P), 1), observed=0.0, free=0.0, resid=float('inf'), n=n_mv)
    if n_mv < 50:
        return out
    ok, h, f, s = grid.at(Q[mv])
    seen = ok & ((h + f) > 0)
    viol = ok & (s == STATE_FREE)
    out.update(observed=float(seen.mean()), free=float(viol.mean()))
    if seen.sum() >= 50:
        d = tree.query(Q[mv][seen])[0]
        d = np.sort(d)[:max(1, int(trim * len(d)))]
        out['resid'] = float(d.mean())
    return out


def _reflect(P, n, d):
    return P - 2 * ((P @ n) - d)[:, None] * n


def _rotmat(a, t):
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.cos(t) * np.eye(3) + (1 - np.cos(t)) * np.outer(a, a) + np.sin(t) * K


def _rotate(P, c, a, t):
    return (P - c) @ _rotmat(a, t).T + c


def _perturb(n, ang, rng, k):
    """sym_probe.perturb (copied)."""
    out = []
    for _ in range(k):
        v = rng.normal(size=3); v -= (v @ n) * n; v /= np.linalg.norm(v)
        m = np.cos(ang) * n + np.sin(ang) * v; out.append(m / np.linalg.norm(m))
    return out


def _refine_offset(P, tree, n, d, iters):
    """sym_probe.refine_offset (copied): offset from the midpoints of the better half of the reflection pairs."""
    for _ in range(iters):
        Q = _reflect(P, n, d)
        dist, j = tree.query(Q)
        m = dist < np.percentile(dist, 50)
        d = float(np.median(((P[m] + tree.data[j[m]]) / 2) @ n))
    return d


def _tilt(n, x_deg):
    """Unit vector n tilted by the angles x_deg[0], x_deg[1] (deg) towards two fixed perpendicular directions."""
    _, L = _libs()
    e1, e2, n = L.frame_from(n)
    m = n + math.tan(math.radians(x_deg[0])) * e1 + math.tan(math.radians(x_deg[1])) * e2
    return m / np.linalg.norm(m)


def _nelder_mead(f, x0, step, K):
    """Derivative-free local minimisation of f from x0 (scipy Nelder-Mead, initial simplex x0 + step along each
    coordinate)."""
    from scipy.optimize import minimize
    x0 = np.asarray(x0, np.float64)
    simplex = np.vstack([x0] + [x0 + step * np.eye(len(x0))[i] for i in range(len(x0))])
    r = minimize(f, x0, method='Nelder-Mead', options=dict(initial_simplex=simplex, xatol=K['nm_xatol'],
                                                             fatol=1e-7, maxfev=K['nm_maxfev']))
    return r.x, float(r.fun), int(r.nfev)


def _place_rot(P, tree, c, a, t, iters):
    """Axis position for a rotation by t about direction a: least squares of q = R (p - c) + c over the better half
    of the pairs (p, q = nearest point to R (p - c) + c); c moves perpendicular to a only."""
    _, L = _libs()
    e1, e2, a = L.frame_from(a)
    R = _rotmat(a, t)
    M = (np.eye(3) - R) @ np.stack([e1, e2], 1)                   # (3, 2)
    for _ in range(iters):
        Q = (P - c) @ R.T + c
        dist, j = tree.query(Q)
        m = dist < np.percentile(dist, 50)
        rhs = (tree.data[j[m]] - Q[m])                            # q - (R (p - c) + c) = (I - R) dc
        A = np.tile(M, (int(m.sum()), 1))
        x = np.linalg.lstsq(A, rhs.reshape(-1), rcond=None)[0]
        c = c + e1 * x[0] + e2 * x[1]
    return c


# ------------------------------------------------------------------------------------------------ hypotheses
def _points(obs, K, rng):
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    own = np.asarray(obs.get('own', np.zeros(len(P), np.uint8)))
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1) & (own == 0)
    P, C = P[ok], C[ok]
    Pd, Cd = vox_down(P, C, K['vox'])
    if len(Pd) > K['max_pts']:
        s = rng.choice(len(Pd), K['max_pts'], replace=False); Pd, Cd = Pd[s], Cd[s]
    return Pd, Cd, int(len(P))


def _axis(Pd, Cd, sigma, K, use_search, grid=None):
    PT, L = _libs()
    info = {}
    cands = []
    rc0, c0, a0, nd = L.fit_axis(Pd, Cd)
    cost, c1, a1 = PT.refine_axis_rot(Pd, Cd, c0, a0, info)
    cands.append(dict(source='fit_axis+refine_axis_rot', c=c1, a=a1, fit_axis_rotc_mm=round(rc0, 3),
                      n_dirs=int(nd), refine=dict(info)))
    if use_search:
        s = PT.robust_scale(Pd)[0]

        class _Ctx:
            def w(self, spec, name):
                return PT.window_value(spec['params'][name], s, name)
        info2 = {}
        c2, a2 = PT.axis_search(_Ctx(), Pd, Cd, dict(params=dict(rim_w=K['rim_w'])), info2)
        cands.append(dict(source='axis_search', c=np.asarray(c2, np.float64), a=np.asarray(a2, np.float64),
                          info=dict(info2)))
    rng = np.random.default_rng(1)
    sub = rng.choice(len(Pd), min(K['rot_sub'], len(Pd)), replace=False)
    for cd in cands:
        a = cd['a'] / np.linalg.norm(cd['a'])
        c = cd['c'] + a * ((Pd - cd['c']) @ a).mean()
        cd['a'], cd['c'] = a, c
        cd['rotc_m'] = L.rot_consistency(Pd[sub], c, a, angles=tuple(K['rot_angles']), trim=K['rot_trim'])
    best = min(cands, key=lambda x: x['rotc_m'])
    c, a = best['c'], best['a']
    rotc50 = L.rot_consistency(Pd[sub], c, a, angles=tuple(K['rot_angles']), trim=0.5)
    mad, cov, nb, nh = lathe_score(Pd, c, a)
    # diagnostic only (not an acceptance test; PREREG A.6 accepts on rotc alone): Thrun-Wegbreit shares of the
    # points rotated by the same angles (observed / FREE landings, as for a mirror)
    tw = []
    if grid is not None:
        tree = cKDTree(Pd)
        for ang in K['rot_angles']:
            tw.append(sym_eval(Pd[sub], _rotate(Pd[sub], c, a, math.radians(ang)), tree, grid, K['band'] * sigma,
                               K['rot_trim']))
    h = (Pd - c) @ a
    r = np.linalg.norm((Pd - c) - np.outer(h, a), axis=1)
    sg = sigma * 1e3
    out = dict(c=[float(x) for x in c], a=[float(x) for x in a], source=best['source'],
               rotc_mm=round(best['rotc_m'] * 1e3, 4), rotc_sigma=round(best['rotc_m'] / sigma, 4),
               rotc50_mm=round(rotc50 * 1e3, 4),
               lathe_mad_mm=None if mad is None else round(mad, 4),
               lathe_mad_sigma=None if mad is None else round(mad / sg, 4),
               sector_cov=round(cov, 4), lathe_bins=nb, h_bins=nh,
               h_span_m=[float(h.min()), float(h.max())], r_median_m=float(np.median(r)),
               accepted=bool(best['rotc_m'] <= K['acc_rotc'] * sigma),
               rot_free_viol=round(float(np.mean([e['free'] for e in tw])), 5) if tw else None,
               rot_observed=round(float(np.mean([e['observed'] for e in tw])), 4) if tw else None,
               candidates=[dict(source=cd['source'], rotc_mm=round(cd['rotc_m'] * 1e3, 4),
                                a=[round(float(x), 5) for x in cd['a']],
                                angle_to_best_deg=round(math.degrees(math.acos(min(1.0, abs(float(cd['a'] @ a))))), 3))
                           for cd in cands])
    return out


def _accept(ev, sigma, K):
    return bool(ev['resid'] <= K['acc_res'] * sigma and ev['observed'] >= K['acc_obs'] and ev['free'] < K['acc_free']
                and ev['moved'] >= K['moved_min'])


def _ev_json(ev, sigma):
    return dict(resid_mm=round(ev['resid'] * 1e3, 4) if np.isfinite(ev['resid']) else None,
                resid_sigma=round(ev['resid'] / sigma, 4) if np.isfinite(ev['resid']) else None,
                observed=round(ev['observed'], 4), free_viol=round(ev['free'], 5), moved=round(ev['moved'], 4))


def _mirrors(Pd, grid, sigma, K, rng):
    tree = cKDTree(Pd)
    band = K['band'] * sigma
    sub = Pd[rng.choice(len(Pd), min(K['sub_search'], len(Pd)), replace=False)]
    sub2 = Pd[rng.choice(len(Pd), min(K['sub_eval'], len(Pd)), replace=False)]
    c0 = np.median(Pd, 0)

    def score(ev):
        return ev['resid'] + K['free_w'] * ev['free']

    cands = []
    for n in fib(K['n_normals']):
        d = _refine_offset(sub, tree, n, float(c0 @ n), iters=2)
        ev = sym_eval(sub, _reflect(sub, n, d), tree, grid, band, K['trim'])
        cands.append((score(ev), ev, n, d))
    cands.sort(key=lambda x: x[0])
    picked = []
    cosd = math.cos(math.radians(K['distinct']))
    for cnd in cands:
        ev = cnd[1]
        if not np.isfinite(cnd[0]) or ev['observed'] < K['min_obs_search'] or ev['moved'] < K['moved_min']:
            continue
        if all(abs(cnd[2] @ p[2]) < cosd for p in picked):
            picked.append(cnd)
        if len(picked) == K['top']:
            break
    out = []
    for sc, ev, n, d in picked:
        best = (sc, ev, n, d)
        for ang in K['perturb']:
            for m in _perturb(best[2], math.radians(ang), rng, K['perturb_n']):
                dd = _refine_offset(sub, tree, m, best[3], iters=2)
                e2 = sym_eval(sub, _reflect(sub, m, dd), tree, grid, band, K['trim'])
                if e2['observed'] >= K['min_obs_search'] and score(e2) < best[0]:
                    best = (score(e2), e2, m, dd)
        n0, d0 = best[2], best[3]

        def f(x):
            m = _tilt(n0, x[:2]); dd = d0 + x[2] * 1e-3
            return score(sym_eval(sub, _reflect(sub, m, dd), tree, grid, band, K['trim']))
        x, fx, nfev = _nelder_mead(f, [0.0, 0.0, 0.0], K['nm_step'], K)
        e_pre = sym_eval(sub2, _reflect(sub2, n0, d0), tree, grid, band, K['trim'])
        n_nm, d_nm = _tilt(n0, x[:2]), d0 + x[2] * 1e-3
        e_nm = sym_eval(sub2, _reflect(sub2, n_nm, d_nm), tree, grid, band, K['trim'])
        if score(e_nm) <= score(e_pre):
            n_f, d_f, e_f, how = n_nm, d_nm, e_nm, f'nelder-mead ({nfev} evaluations)'
        else:
            n_f, d_f, e_f, how = n0, d0, e_pre, 'search'
        row = dict(n=[float(x) for x in n_f], d=float(d_f), refined_by=how, **_ev_json(e_f, sigma))
        row['accepted'] = _accept(e_f, sigma, K)
        out.append(row)
    return out


def _planes(Pd, Cd, sigma, K):
    PT, L = _libs()
    n, _ = L.normals(Pd, Cd)
    idxs, sinfo = PT.segment_planes(Pd, n, K['band'] * sigma, math.cos(math.radians(K['plane_deg'])), K['plane_min'],
                                    K['plane_max'], K['plane_seeds'], K['plane_conn'], np.random.default_rng(0))
    planes = []
    for q in idxs:
        Q = Pd[q]; c = Q.mean(0)
        w, V = np.linalg.eigh(np.cov((Q - c).T))
        a = V[:, 0]
        view = np.einsum('ij,j->i', Cd[q] - Q, a)
        side = 1.0 if np.median(view) >= 0 else -1.0
        a = a * side
        d = float(np.median(Q @ a))
        e1, e2 = V[:, 2], V[:, 1]
        u, v = (Q - c) @ e1, (Q - c) @ e2
        planes.append(dict(n=[float(x) for x in a], d=d, c=[float(x) for x in c], e1=[float(x) for x in e1],
                           e2=[float(x) for x in e2], n_pts=int(len(q)),
                           extent_m=[[float(np.percentile(u, 2)), float(np.percentile(u, 98))],
                                     [float(np.percentile(v, 2)), float(np.percentile(v, 98))]],
                           rms_mm=round(float(np.std(Q @ a - d)) * 1e3, 4),
                           two_sided_share=round(float(min(np.mean(view > 0), np.mean(view < 0))), 4)))
    pairs = []
    cosp = math.cos(math.radians(K['plane_deg']))
    for i in range(len(planes)):
        for j in range(i + 1, len(planes)):
            A, B = planes[i], planes[j]
            na, nb = np.array(A['n']), np.array(B['n'])
            if abs(na @ nb) < cosp or na @ nb >= 0:
                continue
            ca, cb = np.array(A['c']), np.array(B['c'])
            gab, gba = float((cb - ca) @ na), float((ca - cb) @ nb)
            if gab >= 0 or gba >= 0:                               # the material must lie between the two faces
                continue
            gap = 0.5 * (abs(gab) + abs(gba))
            if not K['slab'][0] <= gap <= K['slab'][1]:
                continue
            e1, e2 = np.array(A['e1']), np.array(A['e2'])

            def box(P):
                u, v = (P - ca) @ e1, (P - ca) @ e2
                return np.percentile(u, 2), np.percentile(u, 98), np.percentile(v, 2), np.percentile(v, 98)
            ba, bb = box(Pd[idxs[i]]), box(Pd[idxs[j]])
            iu = max(0.0, min(ba[1], bb[1]) - max(ba[0], bb[0])); iv = max(0.0, min(ba[3], bb[3]) - max(ba[2], bb[2]))
            area = min((ba[1] - ba[0]) * (ba[3] - ba[2]), (bb[1] - bb[0]) * (bb[3] - bb[2]))
            ov = float(iu * iv / max(area, 1e-12))
            if ov < K['pair_overlap']:
                continue
            nm = na - nb; nm /= np.linalg.norm(nm)
            dm = 0.5 * (float(A['d']) - float(B['d']))             # mid plane: nm . x = dm (faces at d_A and -d_B)
            pairs.append(dict(faces=[i, j], thickness_mm=round(gap * 1e3, 4), overlap=round(ov, 4),
                              mid_n=[float(x) for x in nm], mid_d=dm,
                              parallel_deg=round(math.degrees(math.acos(min(1.0, abs(float(na @ nb))))), 3)))
    return planes, pairs, sinfo


def _repeats(Pd, Cd, grid, sigma, K, axis, rng):
    _, L = _libs()
    tree = cKDTree(Pd)
    band = K['band'] * sigma
    sub = Pd[rng.choice(len(Pd), min(K['sub_search'], len(Pd)), replace=False)]
    sub2 = Pd[rng.choice(len(Pd), min(K['sub_eval'], len(Pd)), replace=False)]
    c0 = Pd.mean(0)
    axes = [('axis', np.asarray(axis['c']), np.asarray(axis['a']))]
    V = np.linalg.eigh(np.cov((Pd - c0).T))[1]
    for k in range(3):
        axes.append((f'pc{3 - k}', np.median(Pd, 0), V[:, k]))
    out = []
    for n_ord in K['orders']:
        t = 2 * math.pi / n_ord
        best = None
        for name, c, a in axes:
            c = _place_rot(sub, tree, c, a, t, K['pair_iters'])
            ev = sym_eval(sub, _rotate(sub, c, a, t), tree, grid, band, K['trim'])
            cur = (ev['resid'] + K['free_w'] * ev['free'], ev, c, a, name)
            for ang in K['perturb']:
                for m in _perturb(cur[3], math.radians(ang), rng, K['perturb_n']):
                    cm = _place_rot(sub, tree, cur[2], m, t, K['pair_iters'])
                    e2 = sym_eval(sub, _rotate(sub, cm, m, t), tree, grid, band, K['trim'])
                    s2 = e2['resid'] + K['free_w'] * e2['free']
                    if e2['observed'] >= K['min_obs_search'] and s2 < cur[0]:
                        cur = (s2, e2, cm, m, name)
            if best is None or cur[0] < best[0]:
                best = cur
        _, _, c0, a0, name = best
        _, L = _libs()
        e1, e2, _ = L.frame_from(a0)

        def f(x):
            a = _tilt(a0, x[:2]); c = c0 + (x[2] * e1 + x[3] * e2) * 1e-3
            ev = sym_eval(sub, _rotate(sub, c, a, t), tree, grid, band, K['trim'])
            return ev['resid'] + K['free_w'] * ev['free']
        x, fx, nfev = _nelder_mead(f, [0.0, 0.0, 0.0, 0.0], K['nm_step'], K)
        a_nm, c_nm = _tilt(a0, x[:2]), c0 + (x[2] * e1 + x[3] * e2) * 1e-3
        ev0 = sym_eval(sub2, _rotate(sub2, c0, a0, t), tree, grid, band, K['trim'])
        ev = sym_eval(sub2, _rotate(sub2, c_nm, a_nm, t), tree, grid, band, K['trim'])
        if ev['resid'] + K['free_w'] * ev['free'] <= ev0['resid'] + K['free_w'] * ev0['free']:
            c, a, how = c_nm, a_nm, f'nelder-mead ({nfev} evaluations)'
        else:
            c, a, ev, how = c0, a0, ev0, 'search'
        row = dict(order=n_ord, start=name, refined_by=how, c=[float(x) for x in c], a=[float(x) for x in a],
                   **_ev_json(ev, sigma))
        row['accepted'] = _accept(ev, sigma, K)
        row['implied_by_lathe'] = bool(axis['accepted'] and abs(float(np.asarray(axis['a']) @ a)) > math.cos(
            math.radians(K['distinct'])))
        out.append(row)
    return out


def hypotheses(obs, state=None, sigma=None, *, axis_search=True, repeats=True):
    if sigma is None or not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('structure.hypotheses: sigma (m) is required')
    K = consts()
    rng = np.random.default_rng(0)
    t0 = time.time()
    Pd, Cd, n_raw = _points(obs, K, rng)
    res = dict(schema='gmg-structure/1', sigma_mm=round(sigma * 1e3, 4), n_points=n_raw, n_down=int(len(Pd)),
               timing_s={})
    if len(Pd) < max(K['plane_min'], 500):
        res.update(axis=None, rotc_sigma=None, lathe_mad_sigma=None, mirrors=[], planes=[], plane_pairs=[],
                   repeats=[], accepted=dict(lathe=False, mirrors=[], plate=False, repeats=[]),
                   flags=['too_few_points'])
        return res
    grid = Grid(obs, obs['state'] if state is None else state)
    t = time.time()
    ax = _axis(Pd, Cd, sigma, K, axis_search, grid)
    res['timing_s']['axis'] = round(time.time() - t, 2); t = time.time()
    mir = _mirrors(Pd, grid, sigma, K, np.random.default_rng(0))
    res['timing_s']['mirrors'] = round(time.time() - t, 2); t = time.time()
    planes, pairs, sinfo = _planes(Pd, Cd, sigma, K)
    res['timing_s']['planes'] = round(time.time() - t, 2); t = time.time()
    rep = _repeats(Pd, Cd, grid, sigma, K, ax, np.random.default_rng(0)) if repeats else []
    res['timing_s']['repeats'] = round(time.time() - t, 2)
    res['timing_s']['total'] = round(time.time() - t0, 2)
    res.update(axis=ax, rotc_sigma=ax['rotc_sigma'], lathe_mad_sigma=ax['lathe_mad_sigma'], mirrors=mir,
               planes=planes, plane_pairs=pairs, plane_segmentation=sinfo, repeats=rep,
               accepted=dict(lathe=ax['accepted'], mirrors=[i for i, m in enumerate(mir) if m['accepted']],
                             plate=bool(pairs), repeats=[r['order'] for r in rep if r['accepted']]),
               flags=[])
    return res
