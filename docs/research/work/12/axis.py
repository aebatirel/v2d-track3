"""Fit a revolution axis and build unrolled (theta, h) maps of radius and colour."""
import numpy as np
from meshlib import *

def frame_from_axis(a):
    a = a / np.linalg.norm(a)
    t = np.array([1., 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1., 0])
    e1 = np.cross(a, t); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
    return e1, e2, a

def circle_fit(x, y):
    A = np.stack([x, y, np.ones_like(x)], 1)
    b = x * x + y * y
    s, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = s[0] / 2, s[1] / 2
    r = np.sqrt(s[2] + cx * cx + cy * cy)
    return cx, cy, r

def fit_axis(P, a0, p0=None, hrange=None, nslab=20, iters=4, tol=0.004):
    """Line (p, a) such that slices perpendicular to a have circular cross-sections."""
    a = a0 / np.linalg.norm(a0); p = P.mean(0) if p0 is None else p0
    keep = np.ones(len(P), bool)
    for it in range(iters):
        e1, e2, a = frame_from_axis(a)
        Q = P - p
        h = Q @ a; x = Q @ e1; y = Q @ e2
        lo, hi = (np.percentile(h, 5), np.percentile(h, 95)) if hrange is None else hrange
        cents = []; res_all = np.full(len(P), np.inf)
        for k in range(nslab):
            m = (h >= lo + (hi - lo) * k / nslab) & (h < lo + (hi - lo) * (k + 1) / nslab) & keep
            if m.sum() < 200: continue
            # outer surface only: points beyond median radius from rough centre
            cx, cy, r = circle_fit(x[m], y[m])
            rr = np.hypot(x[m] - cx, y[m] - cy)
            mo = rr > np.median(rr) - 0.003   # drop inner wall
            idx = np.where(m)[0][mo]
            cx, cy, r = circle_fit(x[idx], y[idx])
            res_all[idx] = np.abs(np.hypot(x[idx] - cx, y[idx] - cy) - r)
            cents.append([cx, cy, (lo + hi) / 2 + (hi - lo) * (k + 0.5) / nslab - (lo + hi) / 2 + 0, r])
            cents[-1][2] = lo + (hi - lo) * (k + 0.5) / nslab
        C = np.array(cents)
        # line fit through centres: x = cx0 + sx*h
        A = np.stack([np.ones(len(C)), C[:, 2]], 1)
        sx, *_ = np.linalg.lstsq(A, C[:, 0], rcond=None); sy, *_ = np.linalg.lstsq(A, C[:, 1], rcond=None)
        p = p + sx[0] * e1 + sy[0] * e2
        a = a + sx[1] * e1 + sy[1] * e2; a /= np.linalg.norm(a)
        keep = ~(res_all < np.inf) | (res_all < tol)
    return p, a, C

def cyl(P, p, a):
    e1, e2, a = frame_from_axis(a)
    Q = P - p
    return np.arctan2(Q @ e2, Q @ e1), Q @ a, np.hypot(Q @ e1, Q @ e2), (e1, e2, a)
