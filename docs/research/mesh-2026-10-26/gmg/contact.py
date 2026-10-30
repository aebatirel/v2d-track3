"""Contact census and partner samples (module M4, minimal form for build step B1; B4 adds the full M4).

GT-free: our tracks (cam_T_<obj>, world_T_cam), our owned points and grids, the rectified camera matrix. No file
access here (the bundle passes arrays in).

  observed_samples(obs)                  one sample per OBSERVED voxel (centroid of the owned points in it) with a
                                         normal oriented towards the cameras that saw it (PREREG A.2 "partner samples")
  census(objs, poses, frames, K, ...)    per ordered pair (o, p) and frame: 3-D gap (mm), 2-D mask gap (px);
                                         contact / separated / sep3d frame lists (SPEC section 4, PREREG A.6)
  rel(poses, o, p, f)                    T_{o<-p}[f] = inv(cam_T_o[f]) . cam_T_p[f]
  partner_samples(bundle, target, partner, frames)   P_p moved into the target frame at each frame
  jitter(bundle, o, p)                   pair jitter j (PREREG A.2)

Dev bundles (bundle.from_obs_all) use this module with obs_all points, whose partner points within 12 mm of the
library_v3 meshes were removed: dev contact numbers overstate separation and are never evidence for the pot-and-lid
rule (SPEC section 2).
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from gmg import guard

IMG_W, IMG_H = 1600, 1000           # rectified image size (pipeline/recon_mesh.rectified_K newImageSize)
CEN_VOX = 0.002                     # 3-D gap: owned points reduced to 2 mm centroids (numerical, < 1/5 of 10 mm)
K_NORMAL = 12                       # observed_samples: PCA over the 12 nearest voxel samples (about 8 mm)


def _consts():
    return dict(
        contact_d3=guard.constant('contact_frame_gap3d_m', 0.010, 'generic:PREREG A.6 contact frame, > 10 sigma of '
                                                                    'depth noise and 2.5 voxels'),
        contact_px=guard.constant('contact_frame_gap2d_px', 10, 'generic:PREREG A.6 contact frame, 10 px ~ 10 mm at '
                                                                 '0.5-0.6 m'),
        sep_d3=guard.constant('separated_gap3d_m', 0.020, 'generic:PREREG A.6 separated frame, twice the contact gap'),
        sep_px=guard.constant('separated_gap2d_px', 16, 'generic:PREREG A.6 separated frame, two 8-px cells'),
    )


def rel(poses, o, p, f):
    return np.linalg.inv(poses[f'cam_T_{o}'][f].astype(np.float64)) @ poses[f'cam_T_{p}'][f].astype(np.float64)


def _vox_index(P, lo, vox, shape):
    vi = np.floor((P - lo) / vox).astype(np.int64)
    ok = np.all((vi >= 0) & (vi < np.asarray(shape)), axis=1)
    return vi, ok


def observed_samples(obs):
    """(X (M,3), N (M,3), lin (M,)): centroid of the owned points (own == 0) in each OBSERVED voxel, a PCA normal over
    the K_NORMAL nearest such centroids, turned towards the mean viewing direction of the voxel's points; lin = the
    voxel's linear index in obs' grid."""
    P = np.asarray(obs['pts'], np.float64)
    C = np.asarray(obs['cam'], np.float64)
    own = np.asarray(obs.get('own', np.zeros(len(P), np.uint8)))
    P, C = P[own == 0], C[own == 0]
    state = np.asarray(obs['state'])
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    vi, ok = _vox_index(P, lo, vox, state.shape)
    P, C, vi = P[ok], C[ok], vi[ok]
    lin = np.ravel_multi_index(vi.T, state.shape)
    keep = state.ravel()[lin] == 2
    P, C, lin = P[keep], C[keep], lin[keep]
    if len(P) == 0:
        z = np.zeros((0, 3))
        return z, z, np.zeros(0, np.int64)
    u, inv = np.unique(lin, return_inverse=True)
    cnt = np.bincount(inv).astype(np.float64)
    X = np.stack([np.bincount(inv, P[:, k]) for k in range(3)], 1) / cnt[:, None]
    V = C - P
    V /= np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-12)
    Vm = np.stack([np.bincount(inv, V[:, k]) for k in range(3)], 1) / cnt[:, None]
    k = min(K_NORMAL, len(X))
    _, nb = cKDTree(X).query(X, k=k)
    nb = nb.reshape(len(X), -1)
    Q = X[nb] - X[nb].mean(1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', Q, Q)
    _, vec = np.linalg.eigh(cov)
    N = vec[:, :, 0]
    flip = np.einsum('ij,ij->i', N, Vm) < 0
    N[flip] *= -1
    return X, N, u


def centroids(P, vox=CEN_VOX):
    P = np.asarray(P, np.float64)
    if len(P) == 0:
        return P.reshape(0, 3)
    key = np.floor(P / vox).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    cnt = np.bincount(inv).astype(np.float64)
    return np.stack([np.bincount(inv, P[:, k]) for k in range(3)], 1) / cnt[:, None]


def _mask(Pc, K):
    """Projected footprint of camera-frame points on the full rectified image: pixels hit, dilated by the point
    spacing (CEN_VOX at the points' median depth) and closed (3x3). Returns (y0, x0, bool mask cropped to its
    bounding box) or None if nothing lands in the image."""
    import cv2
    z = Pc[:, 2]
    ok = z > 0.05
    if not ok.any():
        return None
    u = K[0, 0] * Pc[ok, 0] / z[ok] + K[0, 2]
    v = K[1, 1] * Pc[ok, 1] / z[ok] + K[1, 2]
    ins = (u >= 0) & (u < IMG_W) & (v >= 0) & (v < IMG_H)
    if not ins.any():
        return None
    r = int(np.ceil(K[0, 0] * CEN_VOX / max(float(np.median(z[ok][ins])), 0.05)))
    ui, vi = u[ins].astype(np.int64), v[ins].astype(np.int64)
    x0, y0 = max(int(ui.min()) - r - 2, 0), max(int(vi.min()) - r - 2, 0)
    x1, y1 = min(int(ui.max()) + r + 3, IMG_W), min(int(vi.max()) + r + 3, IMG_H)
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    m[vi - y0, ui - x0] = 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    m = cv2.dilate(m, ker)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return y0, x0, m.astype(bool)


def _gap2d(ma, mb):
    """Smallest pixel distance between two cropped masks (0 if they overlap; inf if either is empty)."""
    import cv2
    if ma is None or mb is None:
        return float('inf')
    ya, xa, a = ma
    yb, xb, b = mb
    y0, x0 = min(ya, yb), min(xa, xb)
    y1, x1 = max(ya + a.shape[0], yb + b.shape[0]), max(xa + a.shape[1], xb + b.shape[1])
    A = np.zeros((y1 - y0, x1 - x0), bool); B = np.zeros_like(A)
    A[ya - y0:ya - y0 + a.shape[0], xa - x0:xa - x0 + a.shape[1]] = a
    B[yb - y0:yb - y0 + b.shape[0], xb - x0:xb - x0 + b.shape[1]] = b
    if (A & B).any():
        return 0.0
    dt = cv2.distanceTransform((~B).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dt[A].min())


def census(objs, poses, frames, K):
    """objs: {name: (cen (n,3) 2 mm centroids of owned points, object frame)}. For every unordered pair and frame:
    d3 (m) = smallest distance between the two centroid sets under the tracks; gap2d (px) between their projected
    footprints. Returns {"o|p": {...}} for both orders (same numbers), with frame lists (track frame indices)."""
    c = _consts()
    names = list(objs)
    out = {}
    masks = {}
    for f in frames:
        for o in names:
            T = poses[f'cam_T_{o}'][f].astype(np.float64)
            masks[(o, f)] = _mask(objs[o] @ T[:3, :3].T + T[:3, 3], K) if len(objs[o]) else None
    for i, o in enumerate(names):
        tree = cKDTree(objs[o]) if len(objs[o]) else None
        for p in names[i + 1:]:
            d3, g2 = [], []
            for f in frames:
                A = rel(poses, o, p, f)
                if tree is None or len(objs[p]) == 0:
                    d3.append(float('inf'))
                else:
                    Q = objs[p] @ A[:3, :3].T + A[:3, 3]
                    d3.append(float(tree.query(Q, k=1)[0].min()))
                g2.append(_gap2d(masks[(o, f)], masks[(p, f)]))
            d3, g2 = np.array(d3), np.array(g2)
            fr = np.asarray(frames)
            contact = (d3 <= c['contact_d3']) | (g2 <= c['contact_px'])
            sep = (d3 > c['sep_d3']) & (g2 > c['sep_px'])
            sep3 = d3 > c['sep_d3']
            rec = dict(frames=[int(x) for x in fr], contact=[int(x) for x in fr[contact]],
                       separated=[int(x) for x in fr[sep]], sep3d=[int(x) for x in fr[sep3]],
                       d3_mm=[round(float(x) * 1e3, 2) if np.isfinite(x) else None for x in d3],
                       gap2d_px=[round(float(x), 1) if np.isfinite(x) else None for x in g2],
                       overlap2d=int((g2 == 0).sum()))
            out[f'{o}|{p}'] = rec
            out[f'{p}|{o}'] = dict(rec)
    return out


def separated_for(contact, target, others):
    """Frames in which TARGET is separated from every other tracked object (SPEC section 4)."""
    sets = [set(contact[f'{target}|{p}']['separated']) for p in others]
    return sorted(set.intersection(*sets)) if sets else []


def moved(X, T):
    return X @ T[:3, :3].T + T[:3, 3]


def partner_samples(bundle, target, partner, frames):
    """P_p (one sample per p-OBSERVED voxel, normal towards the cameras; PREREG A.2) moved into TARGET's frame at each
    of FRAMES by T_{o<-p}[f]. Returns (X (M,3), N (M,3), fid (M,) frame of each row, n_p = |P_p|)."""
    Xp, Np, _ = bundle.samples(partner)
    xs, ns, fs = [], [], []
    for f in frames:
        T = rel(bundle.poses, target, partner, f)
        xs.append(moved(Xp, T)); ns.append(Np @ T[:3, :3].T); fs.append(np.full(len(Xp), f, np.int64))
    if not xs:
        z = np.zeros((0, 3))
        return z, z, np.zeros(0, np.int64), len(Xp)
    return np.concatenate(xs), np.concatenate(ns), np.concatenate(fs), len(Xp)


def jitter(poses, o, p, Xp, contact_frames, stride):
    """PREREG A.2: over consecutive contact frames f, f' = f + stride, d = mean over P_p of |T[f']x - T[f]x|;
    j = median d / sqrt 2; 0 if fewer than 5 such pairs. Returns (j in m, number of pairs)."""
    cf = set(contact_frames)
    ds = []
    for f in sorted(cf):
        g = f + stride
        if g in cf and len(Xp):
            ds.append(float(np.linalg.norm(moved(Xp, rel(poses, o, p, g)) - moved(Xp, rel(poses, o, p, f)),
                                           axis=1).mean()))
    if len(ds) < 5:
        return 0.0, len(ds)
    return float(np.median(ds) / np.sqrt(2.0)), len(ds)
