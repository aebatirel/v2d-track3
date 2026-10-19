"""Inferred V2D Track 3 scan-frame canonicalisation (rule R1) + a parametric spoon.

R1 (fits all 10 public scans to float precision for origin/axes; sign rule partial):
  origin  = exact area-weighted surface centroid (trimesh `mesh.centroid`)
  axes    = eigenvectors of the exact area-weighted surface covariance
            x = smallest variance, y = middle, z = largest
  z sign  = exact area-weighted surface third moment along z is positive (10/10 public scans)
  x/y     = NOT determined by the public data (pair sign = 180 deg roll about z);
            `xy_rule` selects a tie-break: 'skew_x' (x third moment > 0, 7/10 scans),
            'skew_y' (y third moment > 0, 7/10 scans), 'hybrid' (y rule if |skew_y|>=0.02 else
            x rule; 9/10 scans, threshold chosen post hoc), right-handed in all cases.
"""
import numpy as np


def tri_moments(V, F):
    T = V[F]
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    A = area.sum()
    s = a + b + c
    cen = (area[:, None] * s / 3.0).sum(0) / A
    M2 = (np.einsum("n,ni,nj->ij", area, a, a) + np.einsum("n,ni,nj->ij", area, b, b)
          + np.einsum("n,ni,nj->ij", area, c, c) + np.einsum("n,ni,nj->ij", area, s, s)) / 12.0 / A
    cov = M2 - np.outer(cen, cen)
    return area, A, cen, cov


def third_moment(V, F, origin, axis):
    T = V[F]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    f = (T - origin) @ axis
    a, b, c = f[:, 0], f[:, 1], f[:, 2]
    h3 = a**3 + b**3 + c**3 + a*a*b + a*a*c + b*b*a + b*b*c + c*c*a + c*c*b + a*b*c
    m3 = (area * h3 / 10.0).sum() / area.sum()
    m2 = (area * (a*a + b*b + c*c + a*b + a*c + b*c) / 6.0).sum() / area.sum()
    return m3 / m2**1.5


def canonical_frame(V, F, xy_rule="skew_x"):
    """Return (R, c): rows of R are the canonical axes in input coords; p_canon = R (p - c)."""
    _, _, c, cov = tri_moments(V, F)
    w, E = np.linalg.eigh(cov)  # ascending variance
    ex, ey, ez = E[:, 0].copy(), E[:, 1].copy(), E[:, 2].copy()
    if third_moment(V, F, c, ez) < 0:
        ez = -ez
    if xy_rule == "skew_x":
        if third_moment(V, F, c, ex) < 0:
            ex = -ex
        ey = np.cross(ez, ex)
    elif xy_rule == "hybrid":  # y by skew if |skew_y| >= 0.02, else x by skew (fits 9/10 public scans)
        if abs(third_moment(V, F, c, ey)) >= 0.02:
            if third_moment(V, F, c, ey) < 0:
                ey = -ey
            ex = np.cross(ey, ez)
        else:
            if third_moment(V, F, c, ex) < 0:
                ex = -ex
            ey = np.cross(ez, ex)
    elif xy_rule == "skew_y":
        if third_moment(V, F, c, ey) < 0:
            ey = -ey
        ex = np.cross(ey, ez)
    else:
        raise ValueError(xy_rule)
    R = np.stack([ex, ey, ez])
    assert np.linalg.det(R) > 0
    return R, c, w


def spoon_mesh(L=0.30, Lb=0.075, wb=0.027, wh0=0.008, wh1=0.011, tb=0.003, th=0.0045,
               Db=0.012, ns=600, nphi=64, bend=0.0, handle_tilt=0.0):
    """Closed parametric wooden spoon. z from bowl tip (0) to handle end (L) before canonicalisation.
    Concave side of the bowl faces +x (bowl floor dips toward -x)."""
    s = np.linspace(0.0, L, ns)
    # planform half width
    u = (s - Lb / 2) / (Lb / 2)
    wbowl = wb * np.sqrt(np.clip(1 - u**2, 0, None))
    wh = np.where(s > 0.6 * Lb, wh0 + (wh1 - wh0) * np.clip((s - Lb) / (L - Lb), 0, 1), 0.0)
    # round the handle end over the last 12 mm
    endr = 0.012
    k = np.clip((L - s) / endr, 0, 1)
    wh = wh * np.sqrt(1 - (1 - k) ** 2)
    # neck blend
    w = np.maximum(wbowl, wh)
    w[0] = 0.0; w[-1] = 0.0
    t = np.where(s < Lb, tb, th) * np.where(w > 0, 1.0, 0.0)
    t = np.minimum(t, w + 1e-6)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    S, P = np.meshgrid(s, phi, indexing="ij")
    W = np.interp(S, s, w); Tt = np.interp(S, s, t)
    cy = np.cos(P); sx = np.sin(P)
    U = (S - Lb / 2) / (Lb / 2)
    D = Db * np.clip(1 - cy**2 - U**2, 0, None)
    X = Tt * sx - D
    Y = W * cy + bend * (S / L) ** 2
    Z = S
    X = X + handle_tilt * np.clip(S - Lb, 0, None)  # handle raised relative to bowl plane
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = np.arange(ns * nphi).reshape(ns, nphi)
    F = []
    for i in range(ns - 1):
        a = idx[i]; b = idx[i + 1]
        a2 = np.roll(a, -1); b2 = np.roll(b, -1)
        F.append(np.stack([a, b, b2], 1)); F.append(np.stack([a, b2, a2], 1))
    F = np.concatenate(F)
    # drop degenerate
    T = V[F]
    ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return V, F[ar > 1e-14]


def apply(V, R, c):
    return (V - c) @ R.T


def sample_surface(V, F, n, seed=0):
    rng = np.random.default_rng(seed)
    T = V[F]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    i = rng.choice(len(F), n, p=area / area.sum())
    r1 = np.sqrt(rng.random(n)); r2 = rng.random(n)
    return T[i, 0] * (1 - r1)[:, None] + T[i, 1] * (r1 * (1 - r2))[:, None] + T[i, 2] * (r1 * r2)[:, None]
