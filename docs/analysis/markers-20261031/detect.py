"""GT-free marker-sphere detector (markers-20261031).

A mocap marker is a grey ~14 mm sphere on a black base. In the rectified ego mono pair it images as a disc of radius
about 6 px at 0.5 m (the visible grey disc measures r ~ 5.6 mm, not the nominal 7.2 mm) whose rim contrast changes
sign around the circle (dark base on one side, brighter wood or table on another). So the detector is a
gradient-direction circle Hough that votes BOTH ways along the gradient (polarity-free) inside a region predicted by
our own track, followed by a robust sub-pixel circle fit on the radial edge pixels. Stereo pairs are formed on the
rectified rows (left = ego_cam_c, right = ego_cam_b, as pipeline/perc2.py) and triangulated.
Nothing is learned; no label of any kind is used; no ground truth, scan or scan-derived constant is read.
"""
import numpy as np, cv2

R_VIS = 0.0058             # m, visible disc radius of a large marker (measured on eval-35 rest frames, our video)
R3D_OK = (0.0038, 0.0080)  # accepted 3-D radius of a stereo detection (r_px * z / f)


def _grad(img):
    g = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 1.0)
    gx = cv2.Scharr(g, cv2.CV_32F, 1, 0) / 32.0; gy = cv2.Scharr(g, cv2.CV_32F, 0, 1) / 32.0
    return g, gx, gy


def circles(img, rect, rmin, rmax, k=20, min_sup=0.35, min_mag=4.0, max_isd=None, min_dark=None):
    """Circle candidates with centre inside rect=(x0,y0,x1,y1). Returns list of dicts (u, v, r, sup, rms, cov, isd,
    ictr, imean), best support first. sup = share of the perimeter carrying a radial edge that votes for the centre."""
    H, W = img.shape
    pad = int(np.ceil(rmax)) + 4
    x0, y0 = int(max(0, rect[0] - pad)), int(max(0, rect[1] - pad))
    x1, y1 = int(min(W, rect[2] + pad + 1)), int(min(H, rect[3] + pad + 1))
    if x1 - x0 < 2 * pad + 3 or y1 - y0 < 2 * pad + 3:
        return []
    crop = img[y0:y1, x0:x1]
    g, gx, gy = _grad(crop)
    mag = np.hypot(gx, gy)
    thr = max(min_mag, np.percentile(mag, 70))
    ys, xs = np.nonzero(mag > thr)
    if len(xs) < 10:
        return []
    m = mag[ys, xs]; dx, dy = gx[ys, xs] / m, gy[ys, xs] / m
    radii = np.arange(rmin, rmax + 0.01, 0.5)
    h, w = crop.shape
    best = np.zeros((h, w), np.float32); ridx = np.zeros((h, w), np.int16)
    for i, r in enumerate(radii):
        a = np.zeros((h, w), np.float32)
        for s in (1, -1):
            cx = np.rint(xs + s * r * dx).astype(int); cy = np.rint(ys + s * r * dy).astype(int)
            ok = (cx >= 0) & (cx < w) & (cy >= 0) & (cy < h)
            np.add.at(a, (cy[ok], cx[ok]), 1.0)
        a = cv2.GaussianBlur(a, (0, 0), 0.8) * (2 * np.pi * 0.8 ** 2) / (2 * np.pi * r)
        upd = a > best; best[upd] = a[upd]; ridx[upd] = i
    loc = (best == cv2.dilate(best, np.ones((5, 5), np.uint8))) & (best > min_sup)
    loc[:max(0, rect[1] - y0)] = False; loc[:, :max(0, rect[0] - x0)] = False
    loc[rect[3] - y0 + 1:] = False; loc[:, rect[2] - x0 + 1:] = False
    py, px = np.nonzero(loc)
    order = np.argsort(-best[py, px])[:k * 3]
    out = []
    for j in order:
        cy0, cx0 = py[j], px[j]; r = radii[ridx[cy0, cx0]]
        fit = _refine(xs, ys, dx, dy, cx0, cy0, r)
        if fit is None:
            continue
        u, v, rr, rms, cov = fit
        if any(np.hypot(u + x0 - c['u'], v + y0 - c['v']) < 0.8 * rmin for c in out):
            continue
        cin = _contrast(g, u, v, rr)
        if (max_isd is not None and cin['isd'] > max_isd) or (min_dark is not None and cin['dark'] < min_dark):
            continue
        out.append(dict(u=u + x0, v=v + y0, r=rr, sup=float(best[cy0, cx0]), rms=rms, cov=cov, **cin))
        if len(out) >= k:
            break
    return out


def _refine(xs, ys, dx, dy, cx, cy, r, it=3):
    """Robust algebraic circle fit to edge pixels that lie ~r from (cx, cy) with a radial gradient."""
    for _ in range(it):
        ox, oy = xs - cx, ys - cy; d = np.hypot(ox, oy) + 1e-6
        rad = np.abs((ox * dx + oy * dy) / d)
        sel = (np.abs(d - r) < max(1.5, 0.2 * r)) & (rad > 0.85)
        if sel.sum() < 8:
            return None
        X, Y = xs[sel].astype(float), ys[sel].astype(float)
        A = np.c_[2 * X, 2 * Y, np.ones_like(X)]; b = X ** 2 + Y ** 2
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        ncx, ncy = sol[0], sol[1]; nr = np.sqrt(max(sol[2] + ncx ** 2 + ncy ** 2, 1e-6))
        if not (0.6 * r < nr < 1.5 * r) or np.hypot(ncx - cx, ncy - cy) > 0.6 * r:
            return None
        cx, cy, r = ncx, ncy, nr
    res = np.hypot(X - cx, Y - cy) - r
    ang = np.arctan2(Y - cy, X - cx); cov = len(np.unique(((ang + np.pi) / (np.pi / 6)).astype(int) % 12)) / 12.0
    return float(cx), float(cy), float(r), float(np.sqrt(np.mean(res ** 2))), float(cov)


def _contrast(g, u, v, r):
    """Interior uniformity (sd inside 0.6 r), |inside mean - ring median| and the black-base cue
    dark = inside mean - 10th percentile of the ring 1.1-2.0 r (the sphere sits on a black base)."""
    h, w = g.shape
    x0, x1 = int(max(0, u - 2.2 * r)), int(min(w, u + 2.2 * r + 1)); y0, y1 = int(max(0, v - 2.2 * r)), int(min(h, v + 2.2 * r + 1))
    yy, xx = np.mgrid[y0:y1, x0:x1]; d = np.hypot(xx - u, yy - v); p = g[y0:y1, x0:x1]
    inn = p[d < 0.6 * r]; ring = p[(d > 1.1 * r) & (d < 2.0 * r)]
    if len(inn) < 5 or len(ring) < 5:
        return dict(isd=99.0, ictr=0.0, imean=0.0, dark=0.0)
    return dict(isd=float(inn.std()), ictr=float(abs(inn.mean() - np.median(ring))), imean=float(inn.mean()),
                dark=float(inn.mean() - np.percentile(ring, 10)))


def _patch(img, u, v, h):
    M = np.float32([[1, 0, h - u], [0, 1, h - v]])
    return cv2.warpAffine(img, M, (2 * h + 1, 2 * h + 1), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def stereo(rig, imL, imR, rectL, zrange, dv0=0.0, dv_tol=2.0, k=30, min_sup=0.35, max_isd=12.0, min_dark=30.0):
    """Stereo marker detections inside the left rect. zrange=(zmin, zmax) m from our track (+ margin).
    Returns list of dicts with X (camera, m), uL, uR, r3d, quality fields."""
    zmin, zmax = max(0.15, zrange[0]), zrange[1]
    rmin = max(3.0, 0.65 * rig.FR * R_VIS / zmax); rmax = 1.35 * rig.FR * R_VIS / zmin
    CL = circles(imL, rectL, rmin, rmax, k, min_sup, max_isd=max_isd, min_dark=min_dark)
    if not CL:
        return []
    dmin, dmax = rig.FR * rig.BASE / zmax, rig.FR * rig.BASE / zmin
    rectR = (int(rectL[0] - dmax - 4), rectL[1] - 4, int(rectL[2] - dmin + 4), rectL[3] + 4)
    CR = circles(imR, rectR, rmin, rmax, k + 5, min_sup, max_isd=max_isd, min_dark=min_dark)
    out = []
    for a in CL:
        best = None
        for b in CR:
            d = a['u'] - b['u']
            if not (dmin - 3 <= d <= dmax + 3) or abs(a['v'] - b['v'] - dv0) > dv_tol:
                continue
            if not (0.7 < b['r'] / a['r'] < 1.43):
                continue
            h = int(max(5, round(1.6 * a['r'])))
            s = ncc(_patch(imL, a['u'], a['v'], h), _patch(imR, b['u'], b['v'], h))
            if best is None or s > best[0]:
                best = (s, b)
        if best is None or best[0] < 0.5:
            continue
        s, b = best
        uL = np.array([a['u'], a['v']]); uR = np.array([b['u'], b['v'] + dv0])
        X = rig.tri(uL, uR); r3 = 0.5 * (a['r'] + b['r']) * X[2] / rig.FR
        if not (R3D_OK[0] <= r3 <= R3D_OK[1]):
            continue
        out.append(dict(X=X.tolist(), uL=uL.tolist(), uR=[b['u'], b['v']], r3=float(r3), ncc=s,
                        sup=min(a['sup'], b['sup']), cov=min(a['cov'], b['cov']), isd=max(a['isd'], b['isd']),
                        dark=min(a['dark'], b['dark']), rL=a['r'], rR=b['r']))
    return out
