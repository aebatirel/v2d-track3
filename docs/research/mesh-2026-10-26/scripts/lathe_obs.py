"""Closed-profile lathe (thin-walled surface of revolution) fitted to OBSERVED points (obs_points.py), no GT.

Why: the observed stereo points of a cup lie ~1 mm from the true surface (median, [D] diagnostic 2026-10-26), but the
TSDF mesher turns the 3 mm walls into 12-20 mm slabs. A body of revolution has few unknowns (axis + one 2-D closed
profile), so the unseen part (underside, back) is fixed by the seen part.
Steps:
  1. Axis: line-complex fit (Pottmann & Randrup): normal lines of a surface of revolution meet the axis;
     IRLS with a Cauchy weight so handles and markers lose influence.
  2. Classify points by where the camera saw them from (obs_points.py stores the camera centre per point):
     radial component of (camera - point) > +0.3 |.|: OUTER wall; < -0.3: INNER wall; otherwise CAP (rim, floor).
  3. Profiles per height bin: r_out(h) = median over sectors of the sector median outer radius; r_in(h) likewise.
     The open end is the end where inner-wall points exist. Wall thickness t = median(r_out - r_in) where both exist;
     unobserved inner wall = r_out - t; inner floor = lowest inner/up-facing cap evidence, else base + t.
     Unobserved outer wall near the base (table band): r_out extended at its last observed value.
  4. Closed profile (outer wall up, rim, inner wall down, floor) revolved -> watertight thin-walled mesh.
  5. Appendages (--appendages 1): points > APP_D outside the lathe, grouped by voxel connectivity; each group of
     >= APP_MIN points is meshed by voxel splatting (2 mm, closing) + marching cubes, its part inside the lathe solid
     dropped. Small compact groups (markers) can be fitted as spheres (--spheres 1).
Usage: lathe_obs.py OBS.npz OUT.glb [--solid 0] [--appendages 1] [--spheres 1]
"""
import argparse, json, math, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy import ndimage

DH = 0.003          # height bin (m)
TIE = 1.25          # axis candidates within this factor of the best rotational consistency are near-ties
NSEC = 24           # angular sectors


def frame_from(d):
    d = d / np.linalg.norm(d)
    a = np.eye(3)[np.argmin(np.abs(d))]
    e1 = np.cross(d, a); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
    return e1, e2, d


def cyl(P, c, d):
    e1, e2, d = frame_from(d)
    Q = P - c
    h = Q @ d; x = Q @ e1; y = Q @ e2
    return h, np.hypot(x, y), np.arctan2(y, x), (e1, e2, d)


def sector_stat(h, r, th, sel, q=50, min_pts=8):
    """(nbins, NSEC) array of the q-th percentile radius per (height bin, sector), NaN where too few points."""
    hb = np.floor((h - h.min()) / DH).astype(int); nb = hb.max() + 1
    sb = ((th + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC
    out = np.full((nb, NSEC), np.nan)
    key = hb[sel] * NSEC + sb[sel]; rr = r[sel]
    order = np.argsort(key); key, rr = key[order], rr[order]
    u, start, cnt = np.unique(key, return_index=True, return_counts=True)
    for k, s0, n in zip(u, start, cnt):
        if n >= min_pts:
            out[k // NSEC, k % NSEC] = np.percentile(rr[s0:s0 + n], q)
    return out, h.min()


def normals(P, C, k=24):
    """PCA normals over k nearest neighbours, oriented towards the camera that saw each point; planarity weight."""
    tree = cKDTree(P)
    _, nb = tree.query(P, k=k)
    Q = P[nb] - P[nb].mean(1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', Q, Q) / k
    w, V = np.linalg.eigh(cov)
    n = V[:, :, 0]
    flip = np.einsum('ni,ni->n', n, C - P) < 0
    n[flip] *= -1
    planar = 1 - w[:, 0] / np.maximum(w[:, 1], 1e-12)          # 1 = flat neighbourhood
    return n, planar


def _irls(n, nb, planar, w, iters):
    a = abar = res = None
    for it in range(iters):
        Maa = (nb * w[:, None]).T @ nb; Mab = (nb * w[:, None]).T @ n; Mbb = (n * w[:, None]).T @ n
        S = Maa - Mab @ np.linalg.solve(Mbb, Mab.T)
        ev, evec = np.linalg.eigh(S); a = evec[:, 0]
        abar = -np.linalg.solve(Mbb, Mab.T @ a)
        res = n @ abar + nb @ a
        s = max(np.median(np.abs(res[w > 0.05 * w.max()])) * 1.5, 1e-4)
        w = planar.clip(0, 1) ** 2 / (1 + (res / s) ** 2) * (w > 0)
    return a, abar


def _place(n, nb, planar, a, iters=6):
    """Best axis LINE for a fixed direction a: abar by weighted least squares, Cauchy IRLS."""
    w = planar.clip(0, 1) ** 2
    for _ in range(iters):
        Mab = (nb * w[:, None]).T @ n; Mbb = (n * w[:, None]).T @ n
        abar = -np.linalg.solve(Mbb, Mab.T @ a)
        res = n @ abar + nb @ a
        s = max(np.median(np.abs(res)) * 1.5, 1e-4)
        w = planar.clip(0, 1) ** 2 / (1 + (res / s) ** 2)
    return abar


def rot_consistency(P, c, a, angles=(45, 90, 135), trim=0.8):
    """Median-trimmed mean NN distance between the cloud and itself rotated about the axis (c, a): small for the true
    axis of a body of revolution; handles, markers are a minority and are trimmed. Non-degenerate for bowls."""
    tree = cKDTree(P)
    e1, e2, d = frame_from(a); X = P - c
    out = []
    for ang in angles:
        t = np.radians(ang)
        Rm = (np.cos(t) * np.eye(3) + (1 - np.cos(t)) * np.outer(d, d)
              + np.sin(t) * np.array([[0, -d[2], d[1]], [d[2], 0, -d[0]], [-d[1], d[0], 0]]))
        dist = tree.query(X @ Rm.T + c)[0]
        out.append(np.mean(np.sort(dist)[:int(trim * len(dist))]))
    return float(np.mean(out))


def fit_axis(P, C, iters=8, nclust=6, knn=24):
    """Axis of a body of revolution from observed points + camera centres (no GT).
    Directions: line-complex fits (Pottmann & Randrup: normal lines meet the axis; IRLS) on all points and on NCLUST
    spatial clusters, plus the PCA axes of all points and of the inside-viewed points. Each direction is placed by
    the line-complex least squares with the direction fixed, then scored by rotational self-consistency; the lowest
    wins. (Line-complex alone fails on a bowl, where every axis through the centre fits, and locks onto a long
    handle; PCA alone fails on squat objects.) Returns (consistency_mm, centre, direction, n_candidates)."""
    from scipy.cluster.vq import kmeans2
    c0 = P.mean(0); X = P - c0
    n, planar = normals(X, C - c0, k=knn)
    nb = np.cross(X, n)
    w0 = planar.clip(0, 1) ** 2
    dirs = [_irls(n, nb, planar, w0.copy(), iters)[0]]
    _, lab = kmeans2(X, nclust, seed=0, minit='++')
    for q in range(nclust):
        m = lab == q
        if m.sum() > 500:
            dirs.append(_irls(n, nb, planar, w0 * m, iters)[0])
    dirs += list(np.linalg.eigh(np.cov(X.T))[1].T)
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    inside = np.einsum('ni,ni->n', n, X - X.mean(0)) < 0        # normals pointing towards the centroid
    opening = None
    if inside.sum() > 100:
        dirs += list(np.linalg.eigh(np.cov(X[inside].T))[1].T)
        # the inside of a container is seen through its opening: the mean view direction of inside-facing points
        opening = v[inside].mean(0); opening /= np.linalg.norm(opening)
        dirs.append(opening)
    sub = np.random.default_rng(1).choice(len(P), min(20000, len(P)), replace=False)
    scored = []
    for a in dirs:
        a = a / np.linalg.norm(a)
        abar = _place(n, nb, planar, a)
        c = c0 + np.cross(a, abar)
        c = c + a * ((P - c) @ a).mean()
        scored.append((rot_consistency(P[sub], c, a), c, a))
    best = min(scored, key=lambda x: x[0])
    if opening is not None:
        # near-ties (a bowl fits any axis through its centre): prefer the direction closest to the opening direction
        ties = [x for x in scored if x[0] <= TIE * best[0]]
        best = max(ties, key=lambda x: abs(x[2] @ opening))
    return best[0] * 1e3, best[1], best[2], len(dirs)


def smooth_fill(prof, valid, win=5):
    """Fill gaps by linear interpolation (ends held), then a running median."""
    x = np.arange(len(prof)); y = prof.copy()
    if valid.sum() == 0:
        return y
    y[~valid] = np.interp(x[~valid], x[valid], prof[valid])
    return ndimage.median_filter(y, size=win, mode='nearest')


def revolve(profile, nseg=96):
    """Closed 2-D profile [(r, h), ...] from the axis (r=0) round to the axis -> watertight mesh (z = axis)."""
    prof = np.asarray(profile, float)
    assert prof[0, 0] == 0 and prof[-1, 0] == 0
    inner = prof[1:-1]; m = len(inner)
    ang = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    V = [[0, 0, prof[0, 1]]]
    for r, h in inner:
        V += [[r * math.cos(t), r * math.sin(t), h] for t in ang]
    V.append([0, 0, prof[-1, 1]])
    V = np.array(V); F = []
    top = len(V) - 1
    for j in range(nseg):
        F.append([0, 1 + (j + 1) % nseg, 1 + j])
    for i in range(m - 1):
        a0, b0 = 1 + i * nseg, 1 + (i + 1) * nseg
        for j in range(nseg):
            j1 = (j + 1) % nseg
            F += [[a0 + j, a0 + j1, b0 + j], [a0 + j1, b0 + j1, b0 + j]]
    last = 1 + (m - 1) * nseg
    for j in range(nseg):
        F.append([top, last + j, last + (j + 1) % nseg])
    mesh = trimesh.Trimesh(V, np.array(F), process=True)
    mesh.fix_normals()
    return mesh


def main():
    global DH
    p = argparse.ArgumentParser()
    p.add_argument('obs'); p.add_argument('out')
    p.add_argument('--solid', type=int, default=0, help='1: no inner wall (closed solid of the outer profile)')
    p.add_argument('--appendages', type=int, default=1); p.add_argument('--app_d', type=float, default=0.004)
    p.add_argument('--app_min', type=int, default=400); p.add_argument('--spheres', type=int, default=0)
    p.add_argument('--vox_ds', type=float, default=0.0015); p.add_argument('--tmin', type=float, default=0.0015)
    p.add_argument('--floor', choices=['base', 'observed', 'base_t'], default='base',
                   help='base: cavity down to base + t; observed: cavity only as deep as the inner wall was seen; '
                        'base_t (C0b): floor top = base + t always, no cap-point density rule')
    # C0b options (PREREG cdo-sprint/C0b 3.3, 3.5, 3.7); unset = the behaviour above, byte for byte
    p.add_argument('--tie', type=float, default=None, help='C0b: axis near-tie factor (TIE)')
    p.add_argument('--t_fallback', type=float, default=None, help='C0b: wall when < 3 two-wall bins (m)')
    p.add_argument('--tmax', type=float, default=None, help='C0b: upper clamp of the wall thickness (m)')
    p.add_argument('--gap', type=int, default=3)
    p.add_argument('--minsec', type=int, default=6)
    p.add_argument('--dh', type=float, default=DH, help='height bin (m)')
    p.add_argument('--min_pts', type=int, default=8, help='points per (height bin, sector) cell')
    p.add_argument('--knn', type=int, default=24, help='neighbours for normals')
    a = p.parse_args()
    DH = a.dh
    global TIE
    if a.tie is not None:
        TIE = a.tie
    Z = np.load(a.obs); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    # voxel downsample (keep one point per voxel, the first)
    key = np.floor(P / a.vox_ds).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    P, C = P[first], C[first]
    sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)
    cost, c, d, k = fit_axis(P[sub], C[sub], knn=a.knn)
    h, r, th, (e1, e2, d) = cyl(P, c, d)
    # classification by viewing side
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    radial = np.stack([np.cos(th), np.sin(th)], 1)
    vr = (v @ e1) * radial[:, 0] + (v @ e2) * radial[:, 1]
    outer, inner = vr > 0.3, vr < -0.3
    Sout, h0 = sector_stat(h, r, th, outer, q=50, min_pts=a.min_pts)
    Sin, _ = sector_stat(h, r, th, inner, q=50, min_pts=a.min_pts)
    nb = Sout.shape[0]
    nsec_out = np.sum(np.isfinite(Sout), 1); nsec_in = np.sum(np.isfinite(Sin), 1)
    # a height bin belongs to the body of revolution only if >= MINSEC of the NSEC sectors saw it (a handle or a
    # marker fills 1-3 sectors)
    r_out = np.where(nsec_out >= a.minsec, np.nanmedian(np.where(np.isfinite(Sout), Sout, np.nan), 1), np.nan)
    r_in = np.where(nsec_in >= a.minsec, np.nanmedian(np.where(np.isfinite(Sin), Sin, np.nan), 1), np.nan)
    hc = h0 + (np.arange(nb) + 0.5) * DH
    vo = np.isfinite(r_out); vi = np.isfinite(r_in) & vo & (r_in < r_out)
    if vo.sum() < 5:
        raise SystemExit('too few outer-wall bins')
    # extent along the axis: robust 0.5 / 99.5 % of the points within the body's radius (not the handle's)
    body = r < np.nanmax(r_out) + 0.005
    hlo, hhi = np.percentile(h[body], [0.5, 99.5])
    # open end = the end with inner-wall evidence (else the solid case)
    hi_in = hc[vi]
    open_top = (len(hi_in) > 0) and (np.mean(hi_in > 0.5 * (hlo + hhi)) >= 0.5)
    if not open_top:                              # flip so the open end is +h
        d = -d; h = -h; hlo, hhi = -hhi, -hlo
        r_out, r_in, vo, vi, hc = r_out[::-1], r_in[::-1], vo[::-1], vi[::-1], -hc[::-1]
    if vi.sum() < 3 and a.t_fallback is not None and a.t_fallback < 0:
        raise SystemExit('C0b: wall fallback needed (< 3 two-wall bins) but no fallback thickness (t0_C0b not fittable)')
    t = float(np.median((r_out - r_in)[vi])) if vi.sum() >= 3 else (0.003 if a.t_fallback is None else a.t_fallback)
    t_src = 'measured' if vi.sum() >= 3 else 'fallback'
    t = max(t, a.tmin)
    if a.tmax is not None:
        t = min(t, a.tmax)
    sel = (hc >= hlo) & (hc <= hhi)
    hc, r_out, r_in, vo, vi = hc[sel], r_out[sel], r_in[sel], vo[sel], vi[sel]
    ro = smooth_fill(r_out, vo)
    ri = np.minimum(smooth_fill(np.where(vi, r_in, r_out - t), vi | vo), ro - a.tmin)
    # inner floor: lowest height with inner evidence (inner wall or caps inside r_in), at least t above the base
    capin = (~outer) & (~inner) & (r < np.interp(h, hc, ri) - 0.003) & (h > hlo) & (h < hhi)
    # an observed floor = a dense, thin layer of such points within the lower 40 % of the height (seen from above
    # through the opening); anything else (stray inner samples, hands) is not floor evidence -> base + t
    hfloor = hlo + t
    low = capin & (h < hlo + 0.4 * (hhi - hlo))
    if low.sum() > 200 and not a.solid and a.floor != 'base_t':
        q10, q50, q90 = np.percentile(h[low], [10, 50, 90])
        if q90 - q10 < 0.01:
            hfloor = max(float(q50), hlo + t)
    if a.floor == 'observed' and vi.any() and not a.solid:
        # cavity only as deep as the inner wall was observed: contiguous inner-wall bins from the open end down,
        # gaps up to GAP bins bridged; the floor is put where that evidence stops (a scanner sees about as far in)
        idx = np.nonzero(vi)[0]; j = idx[-1]; gap = 0
        for i in range(idx[-1], -1, -1):
            if vi[i]:
                j, gap = i, 0
            else:
                gap += 1
                if gap > a.gap:
                    break
        hfloor = max(float(hc[j]) - DH, hlo + t)
    base, top = hlo, hhi
    prof = [(0.0, base), (float(ro[0]), base)]
    prof += [(float(ro[i]), float(hc[i])) for i in range(len(hc))]
    prof += [(float(ro[-1]), top)]
    if a.solid:
        prof += [(0.0, top)]
    else:
        keep = hc > hfloor
        prof += [(float(ri[-1]), top)]
        prof += [(float(ri[i]), float(hc[i])) for i in range(len(hc) - 1, -1, -1) if keep[i]]
        prof += [(float(ri[keep][0]) if keep.any() else float(ro[0] - t), hfloor), (0.0, hfloor)]
    mesh = revolve(prof)
    R = np.stack([e1, np.cross(d, e1), d], 1)              # columns: local x, y, z(axis) in the object frame
    mesh.apply_transform(np.r_[np.c_[R, c], [[0, 0, 0, 1]]])
    parts = [mesh]; info = dict(axis_rotcons_mm=cost, axis_cands=int(k), t_mm=t * 1e3, height_mm=(top - base) * 1e3,
                                rmax_mm=float(ro.max() * 1e3), open_top=bool(open_top), n_outer=int(outer.sum()),
                                n_inner=int(inner.sum()), hfloor_mm=(hfloor - base) * 1e3)
    if a.tie is not None or a.t_fallback is not None or a.tmax is not None or a.floor == 'base_t':
        info.update(c0b=dict(tie=TIE, t_fallback=a.t_fallback, tmax=a.tmax, floor=a.floor, app_d=a.app_d,
                             tmin=a.tmin, t_src=t_src, bins_both=int(vi.sum())))
    if a.appendages:
        # points well outside the lathe body (radius beyond the outer profile at their height, or beyond the ends)
        h2 = (P - c) @ d; Q = P - c - h2[:, None] * d; r2 = np.linalg.norm(Q, axis=1)
        rprof = np.interp(h2, hc, ro)
        out = (r2 > rprof + a.app_d) | (h2 > top + a.app_d) | (h2 < base - a.app_d)
        A = P[out]; info['app_pts'] = int(out.sum())
        if len(A) >= a.app_min:
            vox = 0.002; lo = A.min(0) - 3 * vox
            idx = np.floor((A - lo) / vox).astype(int); shp = idx.max(0) + 4
            occ = np.zeros(shp, bool); occ[tuple(idx.T)] = True
            occ = ndimage.binary_closing(ndimage.binary_dilation(occ, iterations=1), iterations=2)
            lab, nl = ndimage.label(occ)
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1))
            cnts = np.bincount(lab[tuple(idx.T)], minlength=nl + 1)[1:]
            from skimage.measure import marching_cubes
            napp = 0
            for q in range(nl):
                if cnts[q] < a.app_min:
                    continue
                g = np.pad(lab == q + 1, 1).astype(np.float32)
                g = ndimage.gaussian_filter(g, 0.7)
                vv, ff, _, _ = marching_cubes(g, 0.5, spacing=(vox,) * 3)
                m = trimesh.Trimesh(vv + lo - vox, ff, process=True)
                parts.append(m); napp += 1
            info['appendages'] = napp
    full = trimesh.util.concatenate(parts)
    full.export(a.out)
    json.dump(dict(centre=c.tolist(), axis=d.tolist(), e1=e1.tolist(), profile=[list(map(float, q)) for q in prof]),
              open(a.out.rsplit('.', 1)[0] + '.lathe.json', 'w'))
    info.update(faces=int(len(full.faces)), out=a.out)
    print(json.dumps(info))


if __name__ == '__main__':
    main()
