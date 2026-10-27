#!/usr/bin/env python
"""Family B (flat boards: wooden_piece_1/2) primitive meshes fitted to OUR observed stereo points, no GT.

Inputs: obs_points.py files only (pts, cam, frame, and its voxel hit grid; object frame = our track frame). Never
reads scans, *_align.npz, mocap or parquet poses (pre-registered rule 1, work log 2026-10-27).

Model: a flat slab (outline polygon extruded between two parallel face planes) - slot + marker spheres (+ stems).
  1. Plane: PCA normals (k=24, oriented to the camera that saw each point); board normal a = principal direction of
     the normals (planarity weighted, refined on face-like points). Faces: points whose normal is within ~25 deg of
     +-a; each face offset = view-weighted mode of a.p; joint two-plane refit of a. Thickness t = separation of the
     two faces when both are seen (>= NFACE points each), else t_default = median two-face t of the family
     (driver pass 1); the unseen face is put at t from the seen one.
  2. In-plane frame: e1 = long axis (PCA of slab points), e2 = a x e1.
  3. Crossing board: in-plane-normal points beyond the slab on one line (RANSAC). Its in-plane-normal points inside
     our slab are not used for the outline; it limits the slot search and gives the slot width.
  4. Outline: 2-D occupancy (GRID) of slab points, closing 3 mm, hole filling, opening 4.5 mm (spurs), significant
     components (bridged by a growing closing), Gaussian-smoothed contour, simplified (EPS).
  5. Slot (slot_from_grid): in assembled frames the other board's faces pass through our slab only inside our slot,
     so obs_points' voxel HIT grid shows a line of hits in the slab interior from one long edge to about mid-width,
     on one side only. Accepted on contrast (band vs flanks) >= 0.35 with the other half <= 0.15. Width = crossing
     board thickness when its points were found, else t_default. Not carved when undecided.
  6. Markers: points beyond a face by > MOFF, voxel-connected (3 mm), compact (<= 30 mm), >= MIN_MPTS points in
     >= MIN_MFRAMES frames -> centre votes p - R0 n (mean shift), robust sphere LSQ with a radius prior R0 = 7 mm
     (sigma 1.5 mm; our own stereo); accepted if r in [4, 11] mm, RMS <= 1.6 mm, cap protrudes >= MOFF.
     Stem: a cylinder face -> ball only if >= STEM_MIN points lie in the gap below a ball that floats above the face.
  7. Union (manifold3d) -> watertight mesh, 0.2-4k faces.
Variants (<= 4 for the family; all parameters shared by both boards and both episodes):
  occ    : observed-occupancy outline (cells with >= 1 point), slot, markers.
  occ_d2 : same, cells with >= 2 points (tighter outline: less track-jitter halo and stray points).
  rect   : minimum-area rectangle of the outline body (8 mm opening drops tabs and spurs) - slot, markers;
           completes unseen corners and edges.
  occ_nm : occ without markers (ablation: what the markers do for registration).
Usage:
  prim_boards.py build OBS.npz OUT_PREFIX [--variants occ,occ_d2,rect,occ_nm] [--t_default T] [--dump 1]
  prim_boards.py run --obs_dir DIR --out OUT [--objects wooden_piece_1,wooden_piece_2] [--episodes 23,24]
     (pass 1 thickness default, all candidates, GT-free selection by obs_fidelity.py over all episodes' points;
      writes candidates.jsonl, selection.json, manifest_all.tsv for mesh_metric.py)
"""
import argparse, json, math, os, sys
import numpy as np
import cv2
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lathe_obs import normals  # noqa: E402

VOX_DS = 0.0015      # voxel downsample of the observed points (m)
GRID = 0.0015        # 2-D occupancy cell (m)
COS_FACE = 0.9       # |n.a| above this: face point
NFACE = 1500         # points needed per face for a two-face thickness
SLAB_M = 0.0015      # slab margin beyond the faces for outline points (m)
MOFF = 0.004         # marker cluster cores: beyond a face by more than this (m); face jitter is ~+-2 mm
R0, SIG_R = 0.007, 0.0015    # marker radius prior (our own stereo, measured earlier) and its sigma
MIN_MPTS = 25
MIN_MFRAMES = 10     # a marker is rigidly attached: seen in >= 10 frames (hands, clutter: fewer)
STEM_MIN = 15
W_MIN, W_MAX = 0.004, 0.020  # slot width range (m)
EPS = 0.001          # polygon simplification (m)
SMOOTH_PX = 1.5      # outline smoothing (cells)


# ------------------------------------------------------------------------------------------------ io
def load_obs(path, vox=VOX_DS):
    Z = np.load(path)
    P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    F = Z['frame'] if 'frame' in Z.files else np.zeros(len(P), int)
    key = np.floor(P / vox).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    first = np.sort(first)
    return P[first], C[first], F[first]


def wmode(x, w=None, bw=0.00025, sigma=2.0):
    """Weighted mode of x (histogram, Gaussian smoothed)."""
    if len(x) == 0:
        return float('nan')
    lo, hi = x.min() - 5 * bw, x.max() + 5 * bw
    nb = max(3, int(math.ceil((hi - lo) / bw)))
    h, e = np.histogram(x, bins=nb, range=(lo, hi), weights=w)
    h = ndimage.gaussian_filter1d(h.astype(float), sigma)
    k = int(np.argmax(h))
    return float(0.5 * (e[k] + e[k + 1]))


# ------------------------------------------------------------------------------------------------ plane
def fit_plane(P, C, n, planar):
    w = planar.clip(0, 1) ** 2
    M = (n * w[:, None]).T @ n
    a = np.linalg.eigh(M)[1][:, -1]
    for _ in range(3):
        sel = np.abs(n @ a) > 0.85
        M = (n[sel] * w[sel, None]).T @ n[sel]
        a = np.linalg.eigh(M)[1][:, -1]
    if a[np.argmax(np.abs(a))] < 0:
        a = -a
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    info = {}
    for it in range(2):
        d = P @ a; cn = n @ a; vc = np.abs(v @ a)
        fp, fm = cn > COS_FACE, cn < -COS_FACE
        op = wmode(d[fp], vc[fp]) if fp.sum() else float('nan')
        om = wmode(d[fm], vc[fm]) if fm.sum() else float('nan')
        # joint refit of the normal from the points within 2 mm of either face (de-meaned per face)
        groups = []
        if fp.sum() >= 200:
            groups.append(P[fp & (np.abs(d - op) < 0.002)])
        if fm.sum() >= 200:
            groups.append(P[fm & (np.abs(d - om) < 0.002)])
        if it == 0 and groups:
            Q = np.concatenate([g - g.mean(0) for g in groups if len(g) > 50])
            a2 = np.linalg.eigh(Q.T @ Q)[1][:, 0]
            if a2 @ a < 0:
                a2 = -a2
            if a2 @ a > math.cos(math.radians(10)):
                a = a2
    info.update(n_face_p=int(fp.sum()), n_face_m=int(fm.sum()), off_p=op, off_m=om)
    return a, info


def inplane_frame(P, a, sel):
    Q = P[sel] - np.outer(P[sel] @ a, a)
    o = Q.mean(0)
    w, V = np.linalg.eigh(np.cov((Q - o).T))
    e1 = V[:, -1]
    e1 = e1 - (e1 @ a) * a; e1 /= np.linalg.norm(e1)
    if e1[np.argmax(np.abs(e1))] < 0:
        e1 = -e1
    e2 = np.cross(a, e1)
    return o, e1, e2


# ------------------------------------------------------------------------------------------------ crossing board
def crossing_board(U, V, rng, iters=400, tol=0.006, min_in=300):
    """RANSAC line through the in-plane projections of the other board's points; returns (p0, dir, inlier mask)."""
    X = np.stack([U, V], 1)
    if len(X) < min_in:
        return None
    best = None
    for _ in range(iters):
        i, j = rng.choice(len(X), 2, replace=False)
        dvec = X[j] - X[i]; L = np.linalg.norm(dvec)
        if L < 0.02:
            continue
        dvec /= L; nrm = np.array([-dvec[1], dvec[0]])
        dist = np.abs((X - X[i]) @ nrm)
        inl = dist < tol
        if best is None or inl.sum() > best[2].sum():
            best = (X[i], dvec, inl)
    if best is None or best[2].sum() < min_in:
        return None
    p0, dvec, inl = best
    # refine by PCA of the inliers
    Y = X[inl]; c = Y.mean(0); w, Vv = np.linalg.eigh(np.cov((Y - c).T)); dvec = Vv[:, -1]
    ext = (Y - c) @ dvec
    if ext.max() - ext.min() < 0.03:
        return None
    nrm = np.array([-dvec[1], dvec[0]])
    s = (X - c) @ nrm
    inl = np.abs(s) < tol
    # the other board's two faces: the two halves of the signed-distance distribution
    si = s[inl]
    tb = float(np.percentile(si, 90) - np.percentile(si, 10))
    centre = c + nrm * float(np.median(si))
    return dict(c=centre, d=dvec, n=nrm, inl=inl, tb=tb, n_in=int(inl.sum()),
                angle_deg=float(math.degrees(math.atan2(abs(dvec[0]), abs(dvec[1])))))


# ------------------------------------------------------------------------------------------------ markers
def fit_sphere(Q, N, r0=R0, sig_r=SIG_R, noise=0.001):
    c0 = Q.mean(0) - r0 * N.mean(0) / max(np.linalg.norm(N.mean(0)), 1e-9)

    def res(x):
        c, r = x[:3], x[3]
        return np.r_[(np.linalg.norm(Q - c, axis=1) - r) / noise, (r - r0) / sig_r]
    sol = least_squares(res, np.r_[c0, r0], loss='soft_l1', f_scale=2.0)
    c, r = sol.x[:3], float(sol.x[3])
    e = np.linalg.norm(Q - c, axis=1) - r
    return c, r, float(np.sqrt(np.mean(e ** 2))), float(np.median(np.abs(e)))


def find_markers(P, n, F, a, off_p, off_m, inside2d, exclude, attached):
    """Compact clusters beyond either face -> spheres (centre votes p - R0 n, mean shift, robust LSQ).
    inside2d(Q): near the board outline; exclude: points not to use (the crossing board's strip);
    attached(c, r): the ball touches the board outline (in-plane distance of the centre to the outline <= r + 2 mm)."""
    d = P @ a
    beyond = ((d > off_p + MOFF) | (d < off_m - MOFF)) & inside2d(P) & ~exclude
    A = np.nonzero(beyond)[0]
    out = []
    if len(A) < MIN_MPTS:
        return out, 0
    vox = 0.003
    lo = P[A].min(0)
    idx = np.floor((P[A] - lo) / vox).astype(int)
    occ = np.zeros(idx.max(0) + 1, bool); occ[tuple(idx.T)] = True
    lab, nl = ndimage.label(occ, structure=np.ones((3, 3, 3)))
    L = lab[tuple(idx.T)]
    tree = cKDTree(P)
    onface = (np.abs(n @ a) > COS_FACE) & ((np.abs(d - off_p) < 0.002) | (np.abs(d - off_m) < 0.002))
    mid, half = 0.5 * (off_p + off_m), 0.5 * (off_p - off_m)
    for q in range(1, nl + 1):
        m = A[L == q]
        if len(m) < MIN_MPTS or len(np.unique(F[m])) < MIN_MFRAMES:
            continue
        Q = P[m]
        ext = Q.max(0) - Q.min(0)
        if np.max(ext) > 0.030:
            continue
        side = 1 if np.median(d[m]) > mid else -1
        nb = np.array(tree.query_ball_point(Q.mean(0), 0.016), int)
        nb = np.union1d(nb[~onface[nb] & ~exclude[nb]], m)
        votes = P[nb] - R0 * n[nb]
        c = np.median(P[m] - R0 * n[m], axis=0)
        for _ in range(10):                                     # mean shift on the centre votes, 3 mm kernel
            w = np.exp(-0.5 * (np.linalg.norm(votes - c, axis=1) / 0.003) ** 2)
            c = (votes * w[:, None]).sum(0) / max(w.sum(), 1e-9)
        r, rms = R0, None
        for _ in range(3):
            e = np.abs(np.linalg.norm(P[nb] - c, axis=1) - r)
            inl = nb[e < 0.0025]
            if len(inl) < MIN_MPTS:
                break
            c, r, rms, mad = fit_sphere(P[inl], n[inl])
        if rms is None:
            continue
        hc = c @ a
        h_mid = (hc - mid) * side                       # centre height above the mid-plane, on its side
        ok = (0.004 <= r <= 0.011) and rms <= 0.0016 and h_mid <= half + 0.016 and h_mid + r >= half + MOFF
        ok = ok and (attached is None or attached(c, r))
        rec = dict(c=c.tolist(), r=r, rms_mm=rms * 1e3, n=int(len(inl)), n_core=int(len(m)), side=side,
                   h_face_mm=(h_mid - half) * 1e3, ok=bool(ok), frames=int(len(np.unique(F[m]))))
        if ok:
            # stem: points between the face and the ball bottom, within 4 mm of the ball axis
            fo = off_p if side > 0 else off_m
            gap_lo, gap_hi = sorted([fo + side * 0.001, hc - side * r * 0.8])
            X = P - c; radial = np.linalg.norm(X - np.outer(X @ a, a), axis=1)
            st = (radial < 0.004) & (d > gap_lo) & (d < gap_hi)
            rec['stem_pts'] = int(st.sum())
            rec['stem'] = bool((h_mid - half) > r + 0.001 and st.sum() >= STEM_MIN)
            if rec['stem']:
                rec['stem_r'] = float(np.clip(np.percentile(radial[st], 75), 0.0015, 0.004))
        out.append(rec)
    # merge duplicates (two clusters on one ball): keep the one with more inliers
    keep = []
    for rec in sorted(out, key=lambda x: -x['n']):
        if rec['ok'] and any(k['ok'] and np.linalg.norm(np.subtract(k['c'], rec['c'])) < 0.008 for k in keep):
            rec['ok'] = False; rec['dup'] = True
        keep.append(rec)
    return keep, int(len(A))


# ------------------------------------------------------------------------------------------------ outline
def occupancy(U, V, lo, shape, w=None):
    iu = np.floor((U - lo[0]) / GRID).astype(int); iv = np.floor((V - lo[1]) / GRID).astype(int)
    ok = (iu >= 0) & (iu < shape[0]) & (iv >= 0) & (iv < shape[1])
    img = np.zeros(shape, np.float32)
    np.add.at(img, (iu[ok], iv[ok]), 1.0 if w is None else w[ok])
    return img


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r + 0.5


def _close(M, r):
    return ndimage.binary_closing(np.pad(M, r + 2), structure=disk(r))[r + 2:-r - 2, r + 2:-r - 2]


def clean_mask(M0, close_px, open_px=3, min_frac=0.1, max_close_px=14):
    """Closing, hole filling, opening (removes spurs < ~2*open_px cells), significant components (>= MIN_FRAC of
    the largest); if several remain, the closing radius grows (<= MAX_CLOSE_PX) until they join."""
    r = close_px
    while True:
        M = ndimage.binary_fill_holes(_close(M0, r))
        M = ndimage.binary_opening(M, structure=disk(open_px))
        lab, nl = ndimage.label(M)
        if nl == 0:
            return M, r
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1))
        keep = [i + 1 for i in range(nl) if sizes[i] >= min_frac * sizes.max()]
        if len(keep) == 1 or r >= max_close_px:
            return np.isin(lab, keep), r
        r += 2


def mask_polygon(M, lo, eps=EPS):
    """Largest outer contour of the mask -> simplified polygon in (u, v) metres (counter-clockwise)."""
    # smooth the binary edge (Gaussian, sigma SMOOTH_PX, threshold 0.5) at 4x resolution, then contour + simplify
    up = 4
    g = cv2.resize(M.T.astype(np.float32), None, fx=up, fy=up, interpolation=cv2.INTER_NEAREST)
    g = cv2.GaussianBlur(g, (0, 0), SMOOTH_PX * up)
    img = (g > 0.5).astype(np.uint8)       # rows = v, cols = u
    cs, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, eps / GRID * up, True)[:, 0, :].astype(float) / up
    poly = np.stack([lo[0] + c[:, 0] * GRID + 0.5 * GRID / up, lo[1] + c[:, 1] * GRID + 0.5 * GRID / up], 1)
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    if area < 0:
        poly = poly[::-1]
    return poly


def slot_from_crossing(cb, Uc, Vc, M, lo):
    """Slot polygon (u, v) from the crossing board: it runs along the crossing line from the board's mid-width to
    beyond the long edge on the side where the crossing board's points are denser (that board slides in through
    our slot's opening, so partly inserted frames only show it on that side). Width = the crossing board's
    thickness (P10-P90 of its points across the line), clipped to [W_MIN, W_MAX].
    Uc, Vc: in-plane coordinates of the crossing-board inlier points."""
    if cb is None or cb['angle_deg'] > 15:
        return None
    cols = np.nonzero(M.any(0))[0]
    vmid = lo[1] + 0.5 * (cols[0] + cols[-1] + 1) * GRID          # board mid-width (v)
    dl = cb['d'] if cb['d'][1] > 0 else -cb['d']                  # line direction with +v component
    # point of the line at the mid-width
    k = (vmid - cb['c'][1]) / dl[1]
    m = cb['c'] + k * dl
    along = (np.stack([Uc, Vc], 1) - m) @ dl
    npos, nneg = int((along > 0.005).sum()), int((along < -0.005).sum())
    if max(npos, nneg) < 1.5 * max(1, min(npos, nneg)):
        return dict(decided=False, npos=npos, nneg=nneg)
    side = 1 if npos > nneg else -1
    w = float(np.clip(cb['tb'], W_MIN, W_MAX))
    nl = np.array([-dl[1], dl[0]])
    e = side * dl
    poly = np.array([m - nl * w / 2, m + e * 0.2 - nl * w / 2, m + e * 0.2 + nl * w / 2, m + nl * w / 2])
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    if area < 0:
        poly = poly[::-1]
    return dict(decided=True, side=side, width=w, u_mid=float(m[0]), v_mid=float(m[1]), npos=npos, nneg=nneg,
                poly=poly.tolist())


def slot_from_grid(Z, a, o, e1, e2, mid, t, M, lo, width, cb=None):
    """Slot from obs_points' voxel HIT grid (4 mm; it counts every observed surface, the other board included):
    in assembled frames the other board's faces pass through OUR slab only inside our slot, so the slot shows as a
    line of hit voxels inside the slab interior, perpendicular to the long axis, from one long edge to about
    mid-width, on one side only (the other half is solid board and its interior sees no surface).
    Per slice dz inside the slab and per half: hit coverage of a 6 mm band minus that of the 8-20 mm flanks;
    accepted if the best contrast >= 0.35 and the other half's <= 0.15 at the same u. If the crossing board was
    found in the points (cb), the search is limited to within 10 mm of its line."""
    hits, lo3, vox = Z['hits'], Z['lo'], float(Z['vox'])
    g = 0.001
    Mi = cv2.resize(M.T.astype(np.uint8), None, fx=GRID / g, fy=GRID / g, interpolation=cv2.INTER_NEAREST).T > 0
    nu, nv = Mi.shape
    U = lo[0] + (np.arange(nu) + 0.5) * g; V = lo[1] + (np.arange(nv) + 0.5) * g
    interior = ndimage.binary_erosion(Mi, structure=disk(6))
    cols = np.nonzero(Mi.any(0))[0]
    v_mid = lo[1] + 0.5 * (cols[0] + cols[-1] + 1) * g
    W = (cols[-1] - cols[0] + 1) * g
    UU, VV = np.meshgrid(U, V, indexing='ij')
    o_perp = o - (o @ a) * a
    best = None
    half_t = 0.5 * t
    for dz in np.linspace(-half_t + 0.0015, half_t - 0.0015, 5) if half_t > 0.0015 else [0.0]:
        Pp = o_perp + UU[..., None] * e1 + VV[..., None] * e2 + (mid + dz) * a
        idx = np.floor((Pp - lo3) / vox).astype(int)
        ok = np.all((idx >= 0) & (idx < np.array(hits.shape)), axis=-1)
        idx = np.clip(idx, 0, np.array(hits.shape) - 1)
        H = np.where(ok, hits[idx[..., 0], idx[..., 1], idx[..., 2]], 0)
        B = (H >= 2) & interior
        prof = {}
        for half in (-1, 1):
            hm = ((VV - v_mid) * half > 0.003) & interior
            num = (B & hm).sum(1).astype(float); den = hm.sum(1).astype(float)
            k_band = np.ones(7); k_fl = np.r_[np.ones(12), np.zeros(15), np.ones(12)]
            band = np.convolve(num, k_band, 'same') / np.maximum(np.convolve(den, k_band, 'same'), 1)
            fl = np.convolve(num, k_fl, 'same') / np.maximum(np.convolve(den, k_fl, 'same'), 1)
            okc = np.convolve(den, k_band, 'same') > 7 * 0.02 / g
            prof[half] = np.where(okc, band - fl, np.nan)
        for half in (-1, 1):
            c, other = prof[half], prof[-half]
            valid = np.isfinite(c) & np.isfinite(other) & (other <= 0.15)
            valid &= (U > U[Mi.any(1)].min() + 0.02) & (U < U[Mi.any(1)].max() - 0.02)
            if cb is not None:
                valid &= np.abs(U - cb['c'][0]) < 0.010
            if not valid.any():
                continue
            j = int(np.nanargmax(np.where(valid, c, -np.inf)))
            if c[j] >= 0.35 and (best is None or c[j] - max(other[j], 0) > best['contrast']):
                # depth: extent of hit cells along the band on that half, from the edge
                band_cells = B[max(0, j - 3):j + 4] & (((VV[max(0, j - 3):j + 4] - v_mid) * half) > 0.003)
                vv = VV[max(0, j - 3):j + 4][band_cells]
                depth_end = float(np.percentile((vv - v_mid) * half, 5)) if len(vv) else 0.0
                best = dict(contrast=float(c[j] - max(other[j], 0)), cov=float(c[j]), other=float(other[j]),
                            u=float(U[j]), half=half, dz_mm=float(dz * 1e3), depth_end_from_mid_mm=depth_end * 1e3)
    if best is None:
        return dict(decided=False, src='grid')
    side = best['half']
    end = v_mid + side * float(np.clip(best['depth_end_from_mid_mm'] * 1e-3, -0.2 * W, 0.2 * W))
    u0, w = best['u'], width
    poly = np.array([[u0 - w / 2, end], [u0 + w / 2, end], [u0 + w / 2, end + side * 0.2], [u0 - w / 2, end + side * 0.2]])
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    if area < 0:
        poly = poly[::-1]
    best.update(decided=True, src='grid', side=side, width=w, u_mid=u0, v_end=end, poly=poly.tolist())
    return best


def rect_polygon(M, lo):
    img = M.T.astype(np.uint8)
    cs, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = np.vstack(cs)                                   # all significant components (a partly seen board)
    box = cv2.boxPoints(cv2.minAreaRect(c))
    poly = np.stack([lo[0] + (box[:, 0] + 0.5) * GRID, lo[1] + (box[:, 1] + 0.5) * GRID], 1)
    area = 0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    return poly[::-1] if area < 0 else poly


# ------------------------------------------------------------------------------------------------ mesh
def to_trimesh(man):
    mm = man.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=True)


def build_mesh(poly, slot, t, off_m, frame, markers, with_markers=True):
    import manifold3d as m3
    o, e1, e2, a = frame
    cs = m3.CrossSection([poly])
    if slot is not None and slot.get('decided'):
        cs = cs - m3.CrossSection([np.asarray(slot['poly'], float)])
    slab = m3.Manifold.extrude(cs, t).translate([0, 0, off_m])
    parts = slab
    R = np.stack([e1, e2, a], 1)            # local (u, v, d) -> object frame: p = R @ [u, v, d] + o
    if with_markers:
        for mk in markers:
            if not mk['ok']:
                continue
            c = np.asarray(mk['c']) - o
            cl = np.array([c @ e1, c @ e2, np.asarray(mk['c']) @ a])      # local (u, v, absolute offset along a)
            sph = m3.Manifold.sphere(mk['r'], 48).translate(cl.tolist())
            parts = parts + sph
            if mk.get('stem'):
                fo = off_m + t if mk['side'] > 0 else off_m
                z0, z1 = sorted([fo - mk['side'] * 0.001, cl[2]])
                cyl = m3.Manifold.cylinder(z1 - z0, mk['stem_r'], mk['stem_r'], 24).translate([cl[0], cl[1], z0])
                parts = parts + cyl
    mesh = to_trimesh(parts)
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = o - (o @ a) * a       # local d is the absolute offset along a
    mesh.apply_transform(T)
    return mesh


# ------------------------------------------------------------------------------------------------ main fit
def fit(obs_path, t_default=None, close_mm=(3,), dump=None):
    rng = np.random.default_rng(0)
    P, C, F = load_obs(obs_path)
    n, planar = normals(P, C, k=24)
    a, info = fit_plane(P, C, n, planar)
    d = P @ a; cn = n @ a
    op, om = info['off_p'], info['off_m']
    info['off_p_obs'], info['off_m_obs'] = op, om
    two = info['n_face_p'] >= NFACE and info['n_face_m'] >= NFACE
    if two and 0.003 <= op - om <= 0.025:
        t = op - om; t_src = 'two_faces'
    else:
        t = t_default if t_default else 0.008
        t_src = 'default'
        if info['n_face_p'] >= info['n_face_m']:
            om = op - t
        else:
            op = om + t
    info.update(t_mm=t * 1e3, t_src=t_src, off_p=op, off_m=om, n_pts=int(len(P)))
    slab = (d >= om - SLAB_M) & (d <= op + SLAB_M)
    info['frac_slab'] = float(slab.mean())
    o, e1, e2 = inplane_frame(P, a, slab)
    X = P - o; U = X @ e1; V = X @ e2
    # crossing board (the other board through the slot): in-plane-normal points beyond the slab, on one line
    outside = ((d > op + 0.004) | (d < om - 0.004)) & (np.abs(cn) < 0.35)
    cb = crossing_board(U[outside], V[outside], rng)
    use = slab.copy()
    excl = np.zeros(len(P), bool)
    if cb is not None:
        s_ = (np.stack([U, V], 1) - cb['c']) @ cb['n']
        strip = np.abs(s_) < cb['tb'] / 2 + 0.0015
        drop = slab & strip & (np.abs(cn) < 0.5)
        use &= ~drop
        excl = np.abs(s_) < cb['tb'] / 2 + 0.004
        oi = np.nonzero(outside)[0][cb['inl']]
        info['crossing'] = dict(n_in=cb['n_in'], tb_mm=cb['tb'] * 1e3, angle_deg=cb['angle_deg'],
                                dropped=int(drop.sum()), frames=int(len(np.unique(F[oi]))),
                                first_frame=int(F[oi].min()), u=float(cb['c'][0]))
    else:
        info['crossing'] = None
    lo = np.array([U[use].min(), V[use].min()]) - 0.02
    shape = (int(math.ceil((U[use].max() - lo[0] + 0.02) / GRID)) + 1,
             int(math.ceil((V[use].max() - lo[1] + 0.02) / GRID)) + 1)
    img = occupancy(U[use], V[use], lo, shape)
    M0 = img >= 1
    res = dict(info=info, a=a, o=o, e1=e1, e2=e2, t=t, off_m=om, off_p=op, lo=lo, shape=shape, img=img)
    masks = {}
    masks['occ'], r_used = clean_mask(M0, max(1, int(round(close_mm[0] * 1e-3 / GRID))))
    info['close_used_mm'] = r_used * GRID * 1e3
    masks['d2'], _ = clean_mask(img >= 2, max(1, int(round(close_mm[0] * 1e-3 / GRID))))
    # body for the rectangle: opening with an 8 mm disk drops tabs, spurs and stray blobs (< ~16 mm wide)
    body = ndimage.binary_opening(masks['occ'], structure=disk(int(round(0.008 / GRID))))
    lab_, nl_ = ndimage.label(body)
    if nl_:
        sz = ndimage.sum(np.ones_like(lab_), lab_, range(1, nl_ + 1))
        body = np.isin(lab_, [i + 1 for i in range(nl_) if sz[i] >= 0.1 * sz.max()])
    masks['body'] = body if body.any() else masks['occ']
    M = masks['occ']
    res['masks'] = masks
    cbp = cb if (cb is not None and cb['angle_deg'] <= 15) else None    # a crossing perpendicular to the long axis
    slot_w = float(np.clip(cbp['tb'] if cbp is not None else (t_default or t), W_MIN, W_MAX))
    slot = slot_from_grid(np.load(obs_path), a, o, e1, e2, 0.5 * (op + om), t, M, lo, slot_w, cbp)
    if cbp is not None:
        oi = np.nonzero(outside)[0][cb['inl']]
        xs = slot_from_crossing(cb, U[oi], V[oi], M, lo)
        slot['crossing_side_by_density'] = xs.get('side') if xs else None
    res['slot'] = slot
    iu_ = np.nonzero(M.any(1))[0]; iv_ = np.nonzero(M.any(0))[0]
    info.update(length_mm=(iu_[-1] - iu_[0] + 1) * GRID * 1e3, width_mm=(iv_[-1] - iv_[0] + 1) * GRID * 1e3,
                area_cm2=float(M.sum() * GRID * GRID * 1e4), slot=slot,
                n_components_raw=int(ndimage.label(_close(M0, 2))[1]))
    # one-board check: share of points far from the slab/outline (another board, a mis-tracked copy, clutter)
    iu = np.clip(np.floor((U - lo[0]) / GRID).astype(int), 0, shape[0] - 1)
    iv = np.clip(np.floor((V - lo[1]) / GRID).astype(int), 0, shape[1] - 1)
    Mdil = ndimage.binary_dilation(M, structure=disk(int(0.015 / GRID)))
    far = ~Mdil[iu, iv] | (np.abs(d - 0.5 * (op + om)) > 0.04)
    info['frac_far_from_board'] = float(np.mean(far & ~excl))

    def inside2d(Q):
        Xq = Q - o
        ju = np.clip(np.floor((Xq @ e1 - lo[0]) / GRID).astype(int), 0, shape[0] - 1)
        jv = np.clip(np.floor((Xq @ e2 - lo[1]) / GRID).astype(int), 0, shape[1] - 1)
        return Mdil[ju, jv]
    dist_out = ndimage.distance_transform_edt(~M) * GRID           # in-plane distance to the outline (m)

    def attached(c, r):
        Xc = c - o
        ju = int(np.clip((Xc @ e1 - lo[0]) // GRID, 0, shape[0] - 1)); jv = int(np.clip((Xc @ e2 - lo[1]) // GRID, 0, shape[1] - 1))
        return bool(dist_out[ju, jv] <= r + 0.002)
    markers, n_beyond = find_markers(P, n, F, a, op, om, inside2d, excl, attached)
    info['n_beyond'] = n_beyond
    info['markers'] = markers
    res['markers'] = markers
    if dump:
        save_debug(res, dump)
    return res


def save_debug(res, path):
    img = res['img']; M = res['masks']['occ']
    g = np.clip(np.log1p(img) / np.log1p(max(1, np.percentile(img[img > 0], 99))), 0, 1)
    rgb = (np.stack([g, g, g], -1) * 200).transpose(1, 0, 2).copy()          # rows = v, cols = u
    Mt = M.T
    rgb[Mt ^ ndimage.binary_erosion(Mt)] = [255, 80, 0]
    lo = res['lo']
    big = cv2.resize(rgb.astype(np.uint8), None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    big = np.ascontiguousarray(big)
    px = lambda u, v: (int((u - lo[0]) / GRID * 3), int((v - lo[1]) / GRID * 3))
    s = res['slot']
    if s is not None and s.get('decided'):
        pts = np.array([px(*q) for q in s['poly']], np.int32)
        cv2.polylines(big, [pts], True, (0, 255, 0), 1)
    o, e1, e2 = res['o'], res['e1'], res['e2']
    for mk in res['markers']:
        c = np.asarray(mk['c']) - o
        cv2.circle(big, px(c @ e1, c @ e2), int(mk['r'] / GRID * 3), (0, 0, 255) if mk['ok'] else (0, 160, 255), 1)
    cv2.imwrite(path, big[:, :, ::-1])


def build(obs_path, prefix, variants, t_default=None, dump=True):
    res = fit(obs_path, t_default=t_default, dump=(prefix + '_occ.png') if dump else None)
    frame = (res['o'], res['e1'], res['e2'], res['a'])
    out = {}
    for var in variants:
        if var in ('occ', 'occ_nm'):
            poly = mask_polygon(res['masks']['occ'], res['lo'])
        elif var == 'occ_d2':
            poly = mask_polygon(res['masks']['d2'], res['lo'])
        elif var == 'rect':
            poly = rect_polygon(res['masks']['body'], res['lo'])
        else:
            raise SystemExit(f'unknown variant {var}')
        mesh = build_mesh(poly, res['slot'], res['t'], res['off_m'], frame, res['markers'],
                          with_markers=(var != 'occ_nm'))
        f = f'{prefix}_{var}.glb'
        mesh.export(f)
        out[var] = dict(path=f, faces=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                        poly_vertices=int(len(poly)), slot_carved=bool(res['slot'] and res['slot'].get('decided')))
    rep = dict(obs=obs_path, info=res['info'], variants=out, a=res['a'].tolist(), o=res['o'].tolist(),
               e1=res['e1'].tolist(), e2=res['e2'].tolist())
    json.dump(rep, open(prefix + '.json', 'w'), indent=1, default=float)
    return rep


def run(obs_dir, out_dir, objects, episodes, variants):
    """Family driver: pass 1 fits every (object, episode) to get the family thickness default (median two-face
    t), pass 2 builds every (episode x variant) candidate, then GT-free selection per object = lowest
    obs_fidelity sum_mm against the observed points of ALL that object's episodes. Writes candidates.jsonl,
    selection.json and manifest_all.tsv (for mesh_metric.py) in OUT_DIR."""
    import subprocess
    os.makedirs(out_dir, exist_ok=True)
    jobs = [(ob, ep, f'{obs_dir}/ep{ep}_{ob}.npz') for ob in objects for ep in episodes
            if os.path.exists(f'{obs_dir}/ep{ep}_{ob}.npz')]
    ts = []
    for ob, ep, f in jobs:
        r = fit(f)
        if r['info']['t_src'] == 'two_faces':
            ts.append(r['t'])
    t_def = float(np.median(ts)) if ts else 0.008
    print(json.dumps(dict(pass1_two_face_t_mm=[round(t * 1e3, 2) for t in ts], t_default_mm=round(t_def * 1e3, 2))),
          flush=True)
    cands = []
    for ob, ep, f in jobs:
        prefix = f'{out_dir}/{ob}/ep{ep}'
        os.makedirs(os.path.dirname(prefix), exist_ok=True)
        rep = build(f, prefix, variants, t_default=t_def)
        inf = rep['info']
        for var, v in rep['variants'].items():
            cands.append(dict(object=ob, episode=ep, variant=var, path=os.path.abspath(v['path']), faces=v['faces'],
                              watertight=v['watertight'], t_mm=inf['t_mm'], t_src=inf['t_src'],
                              markers=int(sum(m['ok'] for m in inf['markers'])), slot=bool(v['slot_carved']),
                              L_mm=inf['length_mm'], W_mm=inf['width_mm'], far=inf['frac_far_from_board']))
    sel = {}
    for ob in objects:
        obs = ','.join(f for o2, ep, f in jobs if o2 == ob)
        cs = [c for c in cands if c['object'] == ob]
        if not cs:
            continue
        outp = subprocess.run([sys.executable, f'{HERE}/obs_fidelity.py', obs] + [c['path'] for c in cs],
                              capture_output=True, text=True, check=True).stdout
        fid = {}
        for line in outp.splitlines():
            if line.startswith('{'):
                j = json.loads(line); fid[j['mesh']] = j
        for c in cs:
            j = fid[c['path'].split('/')[-1]] if c['path'].split('/')[-1] in fid else None
            # obs_fidelity keys by basename; basenames are unique per object only with the episode in them
            c.update(fid_obs_to_mesh_mm=j['obs_to_mesh_mm'], fid_mesh_to_obs_mm=j['mesh_to_obs_mm'], fid_sum_mm=j['sum_mm'])
        best = min(cs, key=lambda c: c['fid_sum_mm'])
        sel[ob] = dict(episode=best['episode'], variant=best['variant'], path=best['path'], fid_sum_mm=best['fid_sum_mm'],
                       obs=obs)
    with open(f'{out_dir}/candidates.jsonl', 'w') as fh:
        for c in cands:
            fh.write(json.dumps(c) + '\n')
    json.dump(dict(t_default_mm=t_def * 1e3, selection=sel), open(f'{out_dir}/selection.json', 'w'), indent=1)
    with open(f'{out_dir}/manifest_all.tsv', 'w') as fh:
        for c in cands:
            tag = 'selected' if sel.get(c['object'], {}).get('path') == c['path'] else 'candidate'
            fh.write(f"boards/{c['object']}/ep{c['episode']}_{c['variant']}\t{c['object']}\t{c['path']}\t{tag}\n")
    for c in cands:
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if k != 'path'}))
    print(json.dumps(dict(selection={k: (v['episode'], v['variant'], v['fid_sum_mm']) for k, v in sel.items()})))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('obs'); b.add_argument('prefix')
    b.add_argument('--variants', default='occ,occ_d2,rect,occ_nm')
    b.add_argument('--t_default', type=float, default=None)
    b.add_argument('--dump', type=int, default=1)
    r = sub.add_parser('run')
    r.add_argument('--obs_dir', required=True); r.add_argument('--out', required=True)
    r.add_argument('--objects', default='wooden_piece_1,wooden_piece_2'); r.add_argument('--episodes', default='23,24')
    r.add_argument('--variants', default='occ,occ_d2,rect,occ_nm')
    a = p.parse_args()
    if a.cmd == 'run':
        run(a.obs_dir, a.out, a.objects.split(','), a.episodes.split(','), a.variants.split(','))
    elif a.cmd == 'build':
        rep = build(a.obs, a.prefix, a.variants.split(','), a.t_default, bool(a.dump))
        inf = rep['info']
        sl = inf['slot']
        print(json.dumps(dict(obs=a.obs.split('/')[-1], t_mm=round(inf['t_mm'], 2), t_src=inf['t_src'],
                              L=round(inf['length_mm'], 1), W=round(inf['width_mm'], 1),
                              slot=None if sl is None else {k: (round(v, 4) if isinstance(v, float) else v)
                                                            for k, v in sl.items() if k != 'poly'},
                              far=round(inf['frac_far_from_board'], 3),
                              markers=sum(m['ok'] for m in inf['markers']), crossing=inf['crossing'],
                              faces={k: v['faces'] for k, v in rep['variants'].items()})))


if __name__ == '__main__':
    main()
