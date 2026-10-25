"""Lathe (surface-of-revolution) analysis of OUR library meshes. GT-free: reads only our own mesh."""
import numpy as np, trimesh, math
from scipy.spatial import cKDTree

def load(path):
    m = trimesh.load(path, force='mesh')
    return m

def sample(m, n=80000, seed=0):
    pts, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    return np.asarray(pts), np.asarray(m.face_normals[fi])

def frame_from_axis(d):
    d = d / np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(d, a); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
    return e1, e2, d

def circle_fit(xy, w=None, iters=5):
    """Robust algebraic circle fit (Kasa + IRLS Huber-ish)."""
    if w is None: w = np.ones(len(xy))
    c = np.zeros(2); r = 0
    for _ in range(iters):
        A = np.c_[2 * xy, np.ones(len(xy))] * w[:, None]
        b = (xy ** 2).sum(1) * w
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        c = x[:2]; r = math.sqrt(max(x[2] + c @ c, 1e-12))
        res = np.abs(np.linalg.norm(xy - c, axis=1) - r)
        s = 1.4826 * np.median(res) + 1e-4
        w = 1.0 / np.maximum(1.0, res / (2 * s))
    res = np.linalg.norm(xy - c, axis=1) - r
    return c, r, res

def cyl(P, N, c0, d):
    e1, e2, d = frame_from_axis(d)
    Q = P - c0
    h = Q @ d; x = Q @ e1; y = Q @ e2
    r = np.hypot(x, y); th = np.arctan2(y, x)
    rhat = np.c_[x, y] / np.maximum(r, 1e-9)[:, None]
    nr = (N @ e1) * rhat[:, 0] + (N @ e2) * rhat[:, 1]   # radial component of the normal
    nh = N @ d
    return h, r, th, nr, nh

def refine_axis(P, N, c0, d, slab=0.004, iters=4, min_cov=0.6, nbin=36):
    """Fit circle centres per slab of outward-facing points; line-fit the centres; repeat."""
    for _ in range(iters):
        h, r, th, nr, nh = cyl(P, N, c0, d)
        e1, e2, d = frame_from_axis(d)
        cents, ws = [], []
        for h0 in np.arange(h.min(), h.max(), slab):
            k = (h >= h0) & (h < h0 + slab) & (nr > 0.5)
            if k.sum() < 40: continue
            cov = len(np.unique(((th[k] + np.pi) / (2 * np.pi) * nbin).astype(int))) / nbin
            if cov < min_cov: continue
            xy = np.c_[(P[k] - c0) @ e1, (P[k] - c0) @ e2]
            c, rr, res = circle_fit(xy)
            if np.median(np.abs(res)) > 0.08 * rr: continue
            cents.append(c0 + c[0] * e1 + c[1] * e2 + (h0 + slab / 2) * d); ws.append(cov)
        if len(cents) < 4: break
        C = np.array(cents); W = np.array(ws)
        mu = (C * W[:, None]).sum(0) / W.sum()
        U, S, Vt = np.linalg.svd((C - mu) * np.sqrt(W)[:, None], full_matrices=False)
        dn = Vt[0] * np.sign(Vt[0] @ d)
        c0, d = mu, dn / np.linalg.norm(dn)
    return c0, d

def profile(P, N, c0, d, dh=0.002, nbin=36):
    """Per height bin: outer radius per angle bin (max r of outward-facing points), inner radius per angle bin
    (max r of inward-facing points that lie inside the outer), coverage fractions."""
    h, r, th, nr, nh = cyl(P, N, c0, d)
    hb = np.floor((h - h.min()) / dh).astype(int); nb = hb.max() + 1
    tb = np.minimum(((th + np.pi) / (2 * np.pi) * nbin).astype(int), nbin - 1)
    Ro = np.full((nb, nbin), np.nan); Ri = np.full((nb, nbin), np.nan)
    out = nr > 0.3; inn = nr < -0.3
    for k in np.where(out)[0]:
        if not (Ro[hb[k], tb[k]] >= r[k]): Ro[hb[k], tb[k]] = r[k]
    for k in np.where(inn)[0]:
        if not (Ri[hb[k], tb[k]] >= r[k]): Ri[hb[k], tb[k]] = r[k]
    Ri[~(Ri < Ro - 0.001)] = np.nan
    hc = h.min() + (np.arange(nb) + 0.5) * dh
    return hc, Ro, Ri, h
