"""Joint extraction of every tracked object of one episode (module M2 of SPEC section 7; build step B4).

  extract_episode(split, ep, depth, poses, calib, hands, objects, out_dir, *, vox=0.004, cube=0.30, stride=2,
                  seed_masks=None, aux_dir=None, log=print) -> bundle_dir

GT-free. Inputs (all through the guard): our FoundationStereo depth (role depth), our tracks cam_T_<obj> and VO
world_T_cam (role tracks), the calibration (role calib), M1's MediaPipe hands (role own, written by this run), the
frame-0 det dump (role det, mask keys only: masks, mask_shape, frame) and the roster (object names in slot order).
Nothing else: no mesh, no library ROI, no --others.

Per sample (one valid depth pixel of an extraction frame) the rules of scripts/obs_points.py are kept: depth-edge
filter (dilate - erode > 2 cm), z in (0.05, 1.5) m, the per-frame refit of the frame-0 RANSAC table plane
(pipeline/recon_mesh.table_plane) and its 8 mm band, MediaPipe hand capsules (hand 30 mm, forearm 45 mm x 0.15 m), the
voxel-centric vote (a voxel 'hits' in a frame if its centre lies within 4 mm of the depth at its pixel and that pixel's
sample survived the filters; it is 'free' if the depth there lies more than 10 mm behind it; every valid depth ray
carves) and the keep rule (hits >= 3, ratio >= 0.5). The passes of SPEC section 7 (M2):

  pass 0  persistence: hits_o, free_o on the +-CUBE cube around each track origin (lattice: the origin at a voxel
          corner), from all samples; each sample gets r_o = hits/(hits+free) at its voxel in every object's frame
  pass 1  provisional owners: the object with the highest r_o among objects whose keep rule passes at the sample;
          a tie within 2 binomial standard errors (Agresti-Caffo, see DEVIATIONS) is provisionally shared;
          contact census (M4) on the provisional owned points
  pass 2  seeds and seeded components (8 mm connectivity) with the 1.5 x seed-box guard; without a 3-D-separated
          frame, the exclusive frame-0 proposal, else no seed (DEVIATIONS 101)
  pass 3  final owners among the objects whose seeded component holds the sample; ties: co-moving tie-break
          (a) exclusive frame-0 det proposal, (b) nearest seed (< 0.5 x the other), (c) shared
  pass 4  final census (both saved; census_unstable if > 10 % of a pair's separated frames change), grids on the
          final crop box (hits from owned samples only, free from all rays, shared, pocc), sigma, jitter j, table

Outputs: the bundle of SPEC section 6 (episode.json and <obj>.npz) and, with aux_dir, owners.npz: the final owner of
every in-cube sample (frame, pixel, code: object index, SHARED -2 or NONE -1), for the ROI-swap validation (PREREG
B.3, a dev process).
"""
from __future__ import annotations

import json
import os
import sys
import time

import cv2
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from gmg import guard, contact as CT, bundle as BU, hands_cpu

IMG_W, IMG_H = CT.IMG_W, CT.IMG_H
SHARED = -2
NONE = -1


def _pipeline():
    pp = os.path.join(guard.CFG['repo'], 'pipeline')
    if pp not in sys.path:
        sys.path.insert(0, pp)
    import recon_mesh
    return recon_mesh


def consts(vox, cube, stride):
    g = guard.constant
    return dict(
        vox=g('vote_voxel_m', vox, 'generic:PREREG A.6 vote voxel 4 mm'),
        cube=g('crop_cube_half_m', cube, 'generic:PREREG A.6 crop +-0.30 m cube'),
        stride=g('extraction_stride', stride, 'generic:SPEC section 7 M2 stride 2'),
        band=g('table_band_m', 0.008, 'generic:PREREG A.6 crop / SPEC M2 table band 8 mm (obs_points.py)'),
        edge=g('depth_edge_thr_m', 0.02, 'generic:obs_points.py / recon_mesh depth-edge filter'),
        zmin=g('depth_zmin_m', 0.05, 'generic:obs_points.py'),
        zmax=g('depth_zmax_m', 1.5, 'generic:obs_points.py'),
        hand_r=g('hand_capsule_r_m', 0.03, 'generic:SPEC section 7 M2 hand radius 30 mm (obs_points.py)'),
        arm_r=g('forearm_capsule_r_m', 0.045, 'generic:SPEC section 7 M2 forearm 45 mm (obs_points.py)'),
        arm_len=g('forearm_len_m', 0.15, 'generic:obs_points.py forearm segment length'),
        hit=g('vote_hit_m', 0.004, 'generic:obs_points.py hit band (|sdf| < 4 mm)'),
        free=g('free_margin_m', 0.010, 'generic:PREREG A.6 free carving up to 10 mm before the sample'),
        min_hits=g('observed_min_hits', 3, 'generic:PREREG A.6 keep / OBSERVED (obs_points.py default)'),
        min_ratio=g('observed_min_ratio', 0.5, 'generic:PREREG A.6 keep / OBSERVED'),
        tie_se=g('ownership_tie_se', 2.0, 'generic:PREREG A.6 ownership tie 2 binomial SE'),
        connect=g('seed_component_connect_m', 0.008, 'generic:PREREG A.6 seeded component at 8 mm'),
        seed_r=g('seed_radius_m', 0.30, 'generic:SPEC section 7 M2 seed points within 0.30 m of the track origin'),
        guard_k=g('crop_guard_factor', 1.5, 'generic:PREREG A.6 guard 1.5 x seed box'),
        guard_min=g('crop_guard_margin_min_m', 0.02, 'generic:PREREG A.6 seed box + max(2 cm, 25 %)'),
        guard_frac=g('crop_guard_margin_frac', 0.25, 'generic:PREREG A.6 seed box + max(2 cm, 25 %)'),
        grid_margin=g('grid_box_margin_m', 0.02, 'generic:obs_points.py ROI margin 2 cm around the crop'),
        near_seed=g('comoving_nearest_seed_ratio', 0.5, 'generic:PREREG A.6 co-moving nearest seed < 0.5 x other'),
        comoving=g('comoving_flag_frac', 0.5, 'generic:PREREG A.6 co-moving flag > 50 % tied'),
        unstable=g('census_unstable_frac', 0.10, 'generic:PREREG A.6 census_unstable > 10 %'),
    )


# ------------------------------------------------------------------------------------------------ per-frame samples
K5 = np.ones((5, 5), np.uint8)


def filtered_depth(Draw, edge):
    """obs_points.py / recon_mesh depth-edge filter: NaN where dilate - erode (5 x 5) exceeds EDGE."""
    Dt = np.array(Draw, dtype=np.float32)
    Dz = np.where(np.isfinite(Dt), Dt, 0).astype(np.float32)
    Dt[(cv2.dilate(Dz, K5) - cv2.erode(Dz, K5)) > edge] = np.nan
    return Dt


class Frames:
    """Per extraction frame: the edge-filtered depth, the refit table plane (camera frame), the valid-sample image and
    the samples inside at least one object's cube (pixel index, camera-frame point, cube voxel index per object)."""

    def __init__(self, D, poses, objs, K, segs, table_w, c):
        self.D, self.poses, self.objs, self.K, self.segs, self.c = D, poses, objs, K, segs, c
        self.nw, self.cw = np.asarray(table_w[0], np.float64), float(table_w[1])
        self.W_C = poses['world_T_cam'].astype(np.float64)
        self.T_co = {o: poses[f'cam_T_{o}'].astype(np.float64) for o in objs}
        cb = c['cube']
        self.corners = np.array([[x, y, z] for x in (-cb, cb) for y in (-cb, cb) for z in (-cb, cb)])
        self.n_side = int(round(2 * cb / c['vox']))
        self.k5 = np.ones((5, 5), np.uint8)
        H, W = D.shape[1:]
        self.H, self.W = H, W

    def depth(self, t):
        return filtered_depth(self.D[t], self.c['edge'])

    def table(self, t, Pc):
        """obs_points.py: the frame-0 plane moved by VO, refit to nearby samples (<= 10 deg correction)."""
        C_W = np.linalg.inv(self.W_C[t])
        nc = C_W[:3, :3] @ self.nw
        cc = self.cw - nc @ C_W[:3, 3]
        for thr in (0.03, 0.012):
            hgt = Pc @ nc + cc
            sel = np.abs(hgt) < thr
            if sel.sum() < 500:
                break
            Q = Pc[sel][:: max(1, int(sel.sum()) // 20000)]
            q0 = Q.mean(0)
            nn = np.linalg.svd(Q - q0, full_matrices=False)[2][2]
            if nn @ nc < 0:
                nn = -nn
            if nn @ nc > np.cos(np.radians(10)):
                nc, cc = nn, -nn @ q0
        return nc, float(cc)

    def bbox(self, t):
        """Pixel box holding every object's cube at frame t (whole image if a cube corner is behind the camera)."""
        K = self.K
        u0, u1, v0, v1 = self.W, -1, self.H, -1
        for o in self.objs:
            T = self.T_co[o][t]
            Cc = self.corners @ T[:3, :3].T + T[:3, 3]
            if (Cc[:, 2] < self.c['zmin']).any():
                return 0, self.W - 1, 0, self.H - 1
            u = K[0, 0] * Cc[:, 0] / Cc[:, 2] + K[0, 2]
            v = K[1, 1] * Cc[:, 1] / Cc[:, 2] + K[1, 2]
            u0, u1 = min(u0, int(np.floor(u.min()))), max(u1, int(np.ceil(u.max())))
            v0, v1 = min(v0, int(np.floor(v.min()))), max(v1, int(np.ceil(v.max())))
        return max(0, u0), min(self.W - 1, u1), max(0, v0), min(self.H - 1, v1)

    def samples(self, t):
        """Returns dict(Dt, okimg (H,W) bool valid-sample image, nc, cc, pix (n,) int32, P (n,3) float32 camera frame,
        lin [per object (n,) int32 cube voxel index or -1])."""
        c, K = self.c, self.K
        Dt = self.depth(t)
        u0, u1, v0, v1 = self.bbox(t)
        okimg = np.zeros((self.H, self.W), bool)
        empty = dict(Dt=Dt, okimg=okimg, nc=None, cc=None, pix=np.zeros(0, np.int32), P=np.zeros((0, 3), np.float32),
                     lin=[np.zeros(0, np.int32) for _ in self.objs])
        if u1 <= u0 or v1 <= v0:
            return empty
        vv, uu = np.mgrid[v0:v1 + 1, u0:u1 + 1]
        d = Dt[vv, uu]
        ok = np.isfinite(d) & (d > c['zmin']) & (d < c['zmax'])
        uu, vv, d = uu[ok], vv[ok], d[ok]
        Pc = np.stack([(uu - K[0, 2]) * d / K[0, 0], (vv - K[1, 2]) * d / K[1, 1], d], 1).astype(np.float64)
        nc, cc = self.table(t, Pc)
        bad = (Pc @ nc + cc) <= c['band']
        if self.segs is not None and len(self.segs[t][0]):
            A0, B0, rad = self.segs[t]
            lo = np.minimum(A0, B0).min(0) - rad.max()
            hi = np.maximum(A0, B0).max(0) + rad.max()
            near = np.nonzero(np.all((Pc >= lo) & (Pc <= hi), axis=1))[0]
            if len(near):
                Q = Pc[near]
                hb = np.zeros(len(near), bool)
                for s in range(len(A0)):
                    ab = B0[s] - A0[s]
                    ap = Q - A0[s]
                    h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                    hb |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
                bad[near[hb]] = True
        keep = ~bad
        uu, vv, Pc = uu[keep], vv[keep], Pc[keep]
        okimg[vv, uu] = True
        lin, anyc = [], np.zeros(len(Pc), bool)
        n = self.n_side
        for o in self.objs:
            Ti = np.linalg.inv(self.T_co[o][t])
            Po = Pc @ Ti[:3, :3].T + Ti[:3, 3]
            vi = np.floor((Po + c['cube']) / c['vox']).astype(np.int64)
            inc = np.all((vi >= 0) & (vi < n), axis=1)
            li = np.full(len(Pc), -1, np.int64)
            li[inc] = (vi[inc, 0] * n + vi[inc, 1]) * n + vi[inc, 2]
            lin.append(li)
            anyc |= inc
        pix = (vv * self.W + uu)[anyc].astype(np.int32)
        return dict(Dt=Dt, okimg=okimg, nc=nc, cc=cc, pix=pix, P=Pc[anyc].astype(np.float32),
                    lin=[li[anyc].astype(np.int32) for li in lin])


def vote(Dt, label, T, axes, K, c, nlab=1):
    """Voxel-centric votes of one frame on a lattice (axes: three 1-D arrays of voxel-centre coordinates in the object
    frame; T = cam_T_obj). Returns (free_lin, [hit_lin for label 1..nlab]): linear indices (C order) of the voxels that
    are free (depth more than c['free'] behind the centre) and that hit (|sdf| < c['hit']) at a pixel with that label
    (label: (H, W) int8/bool image; 0 = no valid sample)."""
    ax, ay, az = (np.asarray(a, np.float32) for a in axes)
    R = T[:3, :3].astype(np.float32)
    t = T[:3, 3].astype(np.float32)
    X = (R[0, 0] * ax)[:, None, None] + (R[0, 1] * ay)[None, :, None] + (R[0, 2] * az)[None, None, :] + t[0]
    Y = (R[1, 0] * ax)[:, None, None] + (R[1, 1] * ay)[None, :, None] + (R[1, 2] * az)[None, None, :] + t[1]
    Z = (R[2, 0] * ax)[:, None, None] + (R[2, 1] * ay)[None, :, None] + (R[2, 2] * az)[None, None, :] + t[2]
    X, Y, Z = X.ravel(), Y.ravel(), Z.ravel()
    H, W = Dt.shape
    idx = np.nonzero(Z > c['zmin'])[0]
    z = Z[idx]
    pu = np.rint(K[0, 0] * X[idx] / z + K[0, 2]).astype(np.int32)
    pv = np.rint(K[1, 1] * Y[idx] / z + K[1, 2]).astype(np.int32)
    ins = (pu >= 0) & (pu < W) & (pv >= 0) & (pv < H)
    idx, z, pu, pv = idx[ins], z[ins], pu[ins], pv[ins]
    dv = Dt[pv, pu]
    good = np.isfinite(dv) & (dv > c['zmin'])
    idx, z, pu, pv, dv = idx[good], z[good], pu[good], pv[good], dv[good]
    sdf = dv - z
    free_lin = idx[sdf > c['free']]
    near = np.abs(sdf) < c['hit']
    lab = label[pv[near], pu[near]]
    hl = idx[near]
    hits = [hl[lab == k] for k in range(1, nlab + 1)]
    return free_lin, hits


def vote_points(Dt, label, T, X, K, c):
    """vote() on an arbitrary list of voxel centres X (n,3) float32 (object frame): (free_idx, hit_idx) indices into X
    with the same rule (hit only at a pixel whose label is set)."""
    R = T[:3, :3].astype(np.float32)
    t = T[:3, 3].astype(np.float32)
    Xc = X @ R.T + t
    H, W = Dt.shape
    idx = np.nonzero(Xc[:, 2] > c['zmin'])[0]
    z = Xc[idx, 2]
    pu = np.rint(K[0, 0] * Xc[idx, 0] / z + K[0, 2]).astype(np.int32)
    pv = np.rint(K[1, 1] * Xc[idx, 1] / z + K[1, 2]).astype(np.int32)
    ins = (pu >= 0) & (pu < W) & (pv >= 0) & (pv < H)
    idx, z, pu, pv = idx[ins], z[ins], pu[ins], pv[ins]
    dv = Dt[pv, pu]
    good = np.isfinite(dv) & (dv > c['zmin'])
    idx, z, pu, pv, dv = idx[good], z[good], pu[good], pv[good], dv[good]
    sdf = dv - z
    near = np.abs(sdf) < c['hit']
    return idx[sdf > c['free']], idx[near][label[pv[near], pu[near]] > 0]


def _cube_axes(c):
    n = int(round(2 * c['cube'] / c['vox']))
    a = -c['cube'] + (np.arange(n) + 0.5) * c['vox']
    return (a, a, a), n


def _ratio(h, f, c):
    """(r, keep, se2) of hit/free counts (Agresti-Caffo adjusted binomial SE, so a ratio of 0 or 1 is not certain)."""
    h = h.astype(np.float64)
    f = f.astype(np.float64)
    n = h + f
    r = np.where(n > 0, h / np.maximum(n, 1), 0.0)
    keep = (h >= c['min_hits']) & (h >= c['min_ratio'] * n)
    pt = (h + 1) / (n + 2)
    se2 = pt * (1 - pt) / (n + 2)
    return r, keep, se2


def owners(lins, grids, c, allow=None):
    """Owner of each sample among the objects whose keep rule passes at its voxel (and, if allow is given, whose
    allow mask holds its voxel): the highest ratio; objects within c['tie_se'] standard errors of the best (SE of the
    difference) are tied with it. Returns (owner (n,) int8: object index, NONE or SHARED; tied (n,) uint8 bitmask of
    the tied objects (best included) when SHARED, else 0; best (n,) int8)."""
    n = len(lins[0])
    m = len(lins)
    R = np.full((n, m), -1.0)
    S2 = np.zeros((n, m))
    for k in range(m):
        li = lins[k]
        ok = li >= 0
        if allow is not None:
            ok &= np.where(ok, allow[k].ravel()[np.maximum(li, 0)], False)
        idx = np.nonzero(ok)[0]
        if not len(idx):
            continue
        h = grids[k]['hits'].ravel()[li[idx]]
        f = grids[k]['free'].ravel()[li[idx]]
        r, keep, se2 = _ratio(h, f, c)
        R[idx[keep], k] = r[keep]
        S2[idx[keep], k] = se2[keep]
    best = np.argmax(R, axis=1)
    rb = R[np.arange(n), best]
    sb = S2[np.arange(n), best]
    tied = np.zeros(n, np.uint8)
    cnt = np.zeros(n, np.int64)
    for k in range(m):
        tk = (R[:, k] >= 0) & ((best == k) | (rb - R[:, k] <= c['tie_se'] * np.sqrt(sb + S2[:, k])))
        tied[tk] |= np.uint8(1 << k)
        cnt += tk
    own = np.where(rb >= 0, best, NONE).astype(np.int8)
    own[cnt >= 2] = SHARED
    tied[cnt < 2] = 0
    return own, tied, best.astype(np.int8)


def _det_proposals(det_path):
    """Frame-0 SAM2 proposals of the det dump (mask keys only): (masks bool (n, h, w), scale to full resolution)."""
    d = guard.load_npz(det_path, 'det', keys=['masks', 'mask_shape', 'frame'])
    if int(np.asarray(d['frame'])) != 0:
        return None, None
    shp = tuple(int(x) for x in np.asarray(d['mask_shape']))
    m = np.unpackbits(np.asarray(d['masks']), axis=-1)[..., :shp[2]].astype(bool)
    return m, IMG_W / shp[2]


def _components(lin_set, n):
    """Connected components of a set of cube voxels (linear indices) under 8 mm connectivity (centre distance <= 2
    voxels). Returns labels (len(lin_set),)."""
    if len(lin_set) == 0:
        return np.zeros(0, np.int64)
    ijk = np.stack(np.unravel_index(lin_set, (n, n, n)), 1).astype(np.float64)
    pairs = cKDTree(ijk).query_pairs(r=2.0 + 1e-6, output_type='ndarray')
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(lin_set), len(lin_set)))
    return connected_components(g, directed=False)[1]


def _box(P):
    return P.min(0), P.max(0)


# ------------------------------------------------------------------------------------------------ main entry
def extract_episode(split, ep, depth, poses, calib, hands, objects, out_dir, *, vox=0.004, cube=0.30, stride=2,
                    seed_masks=None, aux_dir=None, log=print, roster=None):
    t_start = time.time()
    c = consts(vox, cube, stride)
    timing = {}
    objs = list(objects)
    m = len(objs)
    if m > 8:
        raise ValueError('at most 8 tracked objects (uint8 tie bitmask)')
    rm = _pipeline()
    K = rm.rectified_K(guard.open_input(calib, 'calib'))
    tp = guard.open_input(poses, 'tracks')
    P = guard.load_npz(tp, 'tracks')
    for o in objs:
        if f'cam_T_{o}' not in P:
            raise ValueError(f'ep{ep}: tracks lack {o}')
    dp = guard.open_input(depth, 'depth')
    D = np.load(dp, mmap_mode='r')
    if tuple(D.shape[1:]) != (IMG_H, IMG_W):
        raise ValueError(f'depth shape {D.shape}')
    T = int(min(len(D), len(P['world_T_cam']), *[len(P[f'cam_T_{o}']) for o in objs]))
    frames = list(range(0, T, c['stride']))
    W_C = P['world_T_cam'].astype(np.float64)
    segs = hands_cpu.segments(hands, W_C[:T], c['hand_r'], c['arm_r'], c['arm_len']) if hands else None
    # frame-0 table plane (world = frame-0 camera), RANSAC under the first object whose origin admits a plane
    t0_ = time.time()
    D0 = np.array(D[0], np.float32)
    table, tab_obj = None, None
    for o in objs:
        o0 = (W_C[0] @ P[f'cam_T_{o}'][0].astype(np.float64))[:3, 3]
        try:
            n0, c0, frac = rm.table_plane(D0, K, o0)
        except SystemExit:
            continue
        table, tab_obj = (np.asarray(n0, np.float64), float(c0), float(frac)), o
        break
    if table is None:
        raise RuntimeError(f'ep{ep}: no table plane under any tracked object')
    timing['table_s'] = round(time.time() - t0_, 1)
    FR = Frames(D, P, objs, K, segs, table, c)
    axes, n = _cube_axes(c)

    # ---------------- pass 0: per-frame samples, then persistence votes on each object's cube. The votes are counted
    # only at the cube voxels that hold a sample (the only voxels pass 1-3 look up); the counts there are the dense
    # vote's. The final grids' free counts are voted in pass 4 on the final box (same rule).
    t0_ = time.time()
    S = {}
    okbits = {}
    tables = {}
    for t in frames:
        s = FR.samples(t)
        if s['nc'] is not None:
            tables[t] = (s['nc'].tolist(), s['cc'])
        okbits[t] = np.packbits(s['okimg'])
        S[t] = dict(pix=s['pix'], P=s['P'], lin=s['lin'])
    timing['pass0_samples_s'] = round(time.time() - t0_, 1)
    t1_ = time.time()
    U, XU = [], []
    for k in range(m):
        li = np.concatenate([S[t]['lin'][k] for t in frames]) if frames else np.zeros(0, np.int32)
        u = np.unique(li[li >= 0]).astype(np.int64)
        U.append(u)
        ijk = np.stack(np.unravel_index(u, (n, n, n)), 1)
        XU.append((-c['cube'] + (ijk + 0.5) * c['vox']).astype(np.float32))
    hu = [np.zeros(len(u), np.int32) for u in U]
    fu = [np.zeros(len(u), np.int32) for u in U]
    for t in frames:
        Dt = FR.depth(t)
        okimg = np.unpackbits(okbits[t], count=IMG_H * IMG_W).reshape(IMG_H, IMG_W)
        for k, o in enumerate(objs):
            if len(U[k]):
                fi, hi = vote_points(Dt, okimg, FR.T_co[o][t], XU[k], K, c)
                fu[k][fi] += 1
                hu[k][hi] += 1
    del okbits
    grids = []
    for k in range(m):
        g = dict(hits=np.zeros(n ** 3, np.int32), free=np.zeros(n ** 3, np.int32))
        g['hits'][U[k]] = hu[k]
        g['free'][U[k]] = fu[k]
        g['hits'] = g['hits'].reshape(n, n, n)
        g['free'] = g['free'].reshape(n, n, n)
        grids.append(g)
    timing['pass0_votes_s'] = round(time.time() - t1_, 1)
    timing['pass0_s'] = round(time.time() - t0_, 1)
    timing['pass0_voxels'] = [int(len(u)) for u in U]
    n_samples = int(sum(len(S[t]['pix']) for t in frames))
    log(f'ep{ep} pass 0: {len(frames)} frames, {n_samples} samples, voxels {timing["pass0_voxels"]}, '
        f'{timing["pass0_s"]} s')

    # ---------------- pass 1: provisional owners + census
    t0_ = time.time()
    for t in frames:
        own, tied, _ = owners(S[t]['lin'], grids, c)
        S[t]['own1'], S[t]['tied1'] = own, tied

    def obj_points(k, key, shared_too=False, frames_sel=None):
        out = []
        for t in (frames if frames_sel is None else frames_sel):
            s = S[t]
            sel = s[key] == k
            if shared_too:
                sel |= (s[key] == SHARED) & ((s['tied1' if key == 'own1' else 'tied3'] >> k) & 1).astype(bool)
            if sel.any():
                Ti = np.linalg.inv(FR.T_co[objs[k]][t])
                out.append(s['P'][sel].astype(np.float64) @ Ti[:3, :3].T + Ti[:3, 3])
        return np.concatenate(out) if out else np.zeros((0, 3))

    cen1 = {o: CT.centroids(obj_points(k, 'own1')) for k, o in enumerate(objs)}
    census1 = CT.census(cen1, P, frames, K) if m > 1 else {}
    timing['pass1_s'] = round(time.time() - t0_, 1)

    def sep3d_all(cen_rec, o):
        sets = [set(cen_rec[f'{o}|{p}']['sep3d']) for p in objs if p != o]
        return sorted(set.intersection(*sets)) if sets else list(frames)

    # ---------------- pass 2: seeds + seeded components
    t0_ = time.time()
    props, pscale = (None, None)
    if seed_masks:
        props, pscale = _det_proposals(seed_masks)
    org0 = {}
    for o in objs:
        oc = P[f'cam_T_{o}'][0].astype(np.float64)[:3, 3]
        org0[o] = (K[0, 0] * oc[0] / oc[2] + K[0, 2], K[1, 1] * oc[1] / oc[2] + K[1, 2]) if oc[2] > 0.05 else None
    comp_mask, seeds, seed_info = [], [], {}
    for k, o in enumerate(objs):
        info = {}
        sep3 = sep3d_all(census1, o)
        info['sep3d_frames_pass1'] = len(sep3)
        seed = None

        def det_seed(tag):
            """The frame-0 SAM2 proposal holding o's projected origin, exclusively (proposals holding another tracked
            object's projected origin are not used): o's provisional (owned or o-tied) frame-0 samples inside it."""
            if props is None or 0 not in S or org0[o] is None:
                return None
            hh, ww = props.shape[1:]

            def px(uv):
                return int(np.floor(uv[1] / pscale)), int(np.floor(uv[0] / pscale))
            oi, oj = px(org0[o])
            if not (0 <= oi < hh and 0 <= oj < ww):
                return None
            cand = np.nonzero(props[:, oi, oj])[0].tolist()
            for q in objs:
                if q == o or org0[q] is None:
                    continue
                qi, qj = px(org0[q])
                if 0 <= qi < hh and 0 <= qj < ww:
                    cand = [i for i in cand if not props[i, qi, qj]]
            s0 = S[0]
            mine = (s0['own1'] == k) | ((s0['own1'] == SHARED) & ((s0['tied1'] >> k) & 1).astype(bool))
            pv, pu = np.divmod(s0['pix'].astype(np.int64), IMG_W)
            hi_ = np.minimum((pv / pscale).astype(np.int64), hh - 1)
            hj_ = np.minimum((pu / pscale).astype(np.int64), ww - 1)
            foot = np.zeros((hh, ww), bool)
            foot[hi_[mine], hj_[mine]] = True
            best, bi = 0.0, None
            for i in cand:
                inter = int((props[i] & foot).sum())
                iou = inter / max(int((props[i] | foot).sum()), 1)
                if iou > best:
                    best, bi = iou, i
            info.update(det_candidates=len(cand), det_iou=round(best, 4), det_index=bi)
            if bi is None:
                return None
            insel = mine & props[bi][hi_, hj_]
            if not insel.any():
                return None
            Ti = np.linalg.inv(FR.T_co[o][0])
            info.update(seed=tag, det_mask=int(bi))
            return s0['P'][insel].astype(np.float64) @ Ti[:3, :3].T + Ti[:3, 3]

        # (B) the frame-0 proposal, if frame 0 is 3-D-separated for o
        if 0 in sep3:
            seed = det_seed('det_f0')
        if seed is None:
            # (A) provisional owned points of o's 3-D-separated frames within 0.30 m of the track origin
            pts = obj_points(k, 'own1', frames_sel=[t for t in sep3 if t in S])
            seed = pts[np.linalg.norm(pts, axis=1) <= c['seed_r']] if len(pts) else pts
            info['seed'] = 'sep3d_points'
        if not len(seed):
            # DEVIATIONS 101: neither seed of SPEC section 7 exists (no 3-D-separated frame in the pass-1 census, or
            # no provisional point of o in those frames). The exclusive frame-0 proposal is used without the frame-0
            # separation test (its exclusivity rule keeps a two-object proposal out); without one, o has no seed and
            # no seeded-component restriction (flag no_seed)
            sd = det_seed('det_f0_fallback') if 0 not in sep3 else None
            if sd is not None:
                seed = sd
            else:
                info['seed'] = 'none'
        info['seed_points'] = int(len(seed))
        # component voxel set: cube voxels holding provisional o-owned or o-tied samples
        cnt = np.zeros(n ** 3, np.int32)
        for t in frames:
            s = S[t]
            sel = (s['own1'] == k) | ((s['own1'] == SHARED) & ((s['tied1'] >> k) & 1).astype(bool))
            li = s['lin'][k][sel]
            li = li[li >= 0]
            if len(li):
                np.add.at(cnt, li, 1)
        vset = np.nonzero(cnt)[0]
        lab = _components(vset, n)
        cm = np.zeros(n ** 3, bool)
        if len(seed) and len(vset):
            sv = np.floor((seed + c['cube']) / c['vox']).astype(np.int64)
            ok = np.all((sv >= 0) & (sv < n), axis=1)
            sl = (sv[ok, 0] * n + sv[ok, 1]) * n + sv[ok, 2]
            pos = np.searchsorted(vset, sl)
            pos = np.clip(pos, 0, len(vset) - 1)
            hit = vset[pos] == sl
            labs = np.unique(lab[pos[hit]])
            cm[vset[np.isin(lab, labs)]] = True
            info['components_total'] = int(lab.max() + 1) if len(lab) else 0
            info['components_seeded'] = int(len(labs))
        elif len(vset):
            cm[vset] = True              # no seed (DEVIATIONS 101): no seeded-component restriction, no guard
            info['no_seed'] = True
        nv = int(cm.sum())
        info['component_voxels'] = nv
        info['guard'] = False
        if nv and len(seed):
            ijk = np.stack(np.unravel_index(np.nonzero(cm)[0], (n, n, n)), 1)
            ctr = -c['cube'] + (ijk + 0.5) * c['vox']
            clo, chi = ctr.min(0) - c['vox'] / 2, ctr.max(0) + c['vox'] / 2
            slo, shi = _box(seed)
            sext, cext = shi - slo, chi - clo
            info.update(seed_box_mm=np.round(sext * 1e3, 1).tolist(), comp_box_mm=np.round(cext * 1e3, 1).tolist())
            if np.any(cext > c['guard_k'] * sext):
                mg = np.maximum(c['guard_min'], c['guard_frac'] * sext)
                glo, ghi = slo - mg, shi + mg
                inb = np.all((ctr >= glo) & (ctr <= ghi), axis=1)
                cm[np.nonzero(cm)[0][~inb]] = False
                info.update(guard=True, guard_box_lo=glo.tolist(), guard_box_hi=ghi.tolist(),
                            component_voxels_after_guard=int(cm.sum()))
                box = (glo, ghi)
            else:
                box = (clo - c['grid_margin'], chi + c['grid_margin'])
        elif nv:
            ijk = np.stack(np.unravel_index(np.nonzero(cm)[0], (n, n, n)), 1)
            ctr = -c['cube'] + (ijk + 0.5) * c['vox']
            clo, chi = ctr.min(0) - c['vox'] / 2, ctr.max(0) + c['vox'] / 2
            info.update(comp_box_mm=np.round((chi - clo) * 1e3, 1).tolist())
            box = (clo - c['grid_margin'], chi + c['grid_margin'])
        else:
            box = None
        info['box'] = None if box is None else [np.round(box[0], 4).tolist(), np.round(box[1], 4).tolist()]
        comp_mask.append(cm.reshape(n, n, n))
        seeds.append(CT.centroids(seed) if len(seed) else np.zeros((0, 3)))
        seed_info[o] = info
        seed_info[o]['_box'] = box
    timing['pass2_s'] = round(time.time() - t0_, 1)

    # ---------------- pass 3: final owners + co-moving tie-break
    t0_ = time.time()
    trees = [cKDTree(sd) if len(sd) else None for sd in seeds]
    tb_counts = {}           # (k, q) -> counts of tie decisions
    det_chosen = {objs[k]: seed_info[objs[k]].get('det_mask') for k in range(m)}
    for t in frames:
        s = S[t]
        own, tied, _ = owners(s['lin'], grids, c, allow=comp_mask)
        sh = np.nonzero(own == SHARED)[0]
        how = np.zeros(len(own), np.int8)          # 1 mask, 2 seed, 3 shared (c)
        if len(sh):
            # (a) exclusive frame-0 proposals (Phase 1: frame 0 only)
            if t == 0 and props is not None:
                pv, pu = np.divmod(s['pix'][sh].astype(np.int64), IMG_W)
                hh, ww = props.shape[1:]
                hi_ = np.minimum((pv / pscale).astype(np.int64), hh - 1)
                hj_ = np.minimum((pu / pscale).astype(np.int64), ww - 1)
                inm = np.zeros((len(sh), m), bool)
                for k, o in enumerate(objs):
                    bi = det_chosen[o]
                    if bi is not None:
                        inm[:, k] = props[bi][hi_, hj_] & ((tied[sh] >> k) & 1).astype(bool)
                one = inm.sum(1) == 1
                if one.any():
                    own[sh[one]] = np.argmax(inm[one], 1)
                    how[sh[one]] = 1
                sh = sh[~one]
            # (b) nearest seed
            if len(sh):
                dist = np.full((len(sh), m), np.inf)
                for k, o in enumerate(objs):
                    tk = ((tied[sh] >> k) & 1).astype(bool)
                    if trees[k] is None or not tk.any():
                        continue
                    Ti = np.linalg.inv(FR.T_co[o][t])
                    Po = s['P'][sh[tk]].astype(np.float64) @ Ti[:3, :3].T + Ti[:3, 3]
                    dist[np.nonzero(tk)[0], k] = trees[k].query(Po, k=1)[0]
                order = np.sort(dist, 1)
                # the nearer seed must be below half the farther; a tied object without a seed (DEVIATIONS 101)
                # gives no distance, so its samples stay shared (c)
                win = np.isfinite(order[:, 1]) & (order[:, 0] < c['near_seed'] * order[:, 1])
                if win.any():
                    own[sh[win]] = np.argmin(dist[win], 1)
                    how[sh[win]] = 2
                how[sh[~win]] = 3
        tied3 = np.where(own == SHARED, tied, 0).astype(np.uint8)
        s['own3'], s['tied3'], s['how3'] = own, tied3, how
    timing['pass3_s'] = round(time.time() - t0_, 1)

    # pair statistics of the tie-break (pass 1 ties, how pass 3 resolved them)
    pair_tie = {}
    for k in range(m):
        for q in range(m):
            if q == k:
                continue
            n_mine = n_tied = 0
            hw = np.zeros(4, np.int64)
            for t in frames:
                s = S[t]
                mine = (s['own1'] == k) | ((s['own1'] == SHARED) & ((s['tied1'] >> k) & 1).astype(bool))
                tq = mine & (s['own1'] == SHARED) & ((s['tied1'] >> q) & 1).astype(bool)
                n_mine += int(mine.sum())
                n_tied += int(tq.sum())
                hw += np.bincount(s['how3'][tq], minlength=4)[:4]
            pair_tie[(k, q)] = dict(n=n_mine, tied1=n_tied, tied1_frac=round(n_tied / max(n_mine, 1), 4),
                                    pass3=dict(decided_by_ratio_or_component=int(hw[0]), mask=int(hw[1]),
                                               seed=int(hw[2]), shared=int(hw[3])))

    # ---------------- pass 4: final census, grids, pocc, sigma, jitter, table
    t0_ = time.time()
    cen4 = {o: CT.centroids(obj_points(k, 'own3')) for k, o in enumerate(objs)}
    census4 = CT.census(cen4, P, frames, K) if m > 1 else {}
    census_change = {}
    for key, rec in census4.items():
        a, b = set(census1[key]['separated']), set(rec['separated'])
        census_change[key] = round(len(a ^ b) / max(len(frames), 1), 4)
    # final grids on each object's crop box (a sub-lattice of the cube)
    sub = {}
    for k, o in enumerate(objs):
        box = seed_info[o]['_box']
        if box is None:
            i0 = np.zeros(3, np.int64); i1 = np.zeros(3, np.int64)
        else:
            i0 = np.clip(np.floor((np.asarray(box[0]) + c['cube']) / c['vox']).astype(np.int64), 0, n)
            i1 = np.clip(np.ceil((np.asarray(box[1]) + c['cube']) / c['vox']).astype(np.int64), 0, n)
        shp = tuple(int(x) for x in np.maximum(i1 - i0, 0))
        sub[o] = dict(i0=i0, i1=i1, shape=shp, lo=-c['cube'] + i0 * c['vox'],
                      axes=tuple(-c['cube'] + (np.arange(i0[d], i1[d]) + 0.5) * c['vox'] for d in range(3)),
                      hits=np.zeros(int(np.prod(shp)), np.int32), shared=np.zeros(int(np.prod(shp)), np.int32),
                      free=np.zeros(int(np.prod(shp)), np.int32))
    for t in frames:
        Dt = FR.depth(t)
        s = S[t]
        pv, pu = np.divmod(s['pix'].astype(np.int64), IMG_W)
        for k, o in enumerate(objs):
            sb = sub[o]
            if 0 in sb['shape']:
                continue
            lab = np.zeros((IMG_H, IMG_W), np.int8)
            ow = s['own3'] == k
            shd = (s['own3'] == SHARED) & ((s['tied3'] >> k) & 1).astype(bool)
            lab[pv[ow], pu[ow]] = 1
            lab[pv[shd], pu[shd]] = 2
            fl, (h1, h2) = vote(Dt, lab, FR.T_co[o][t], sb['axes'], K, c, nlab=2)
            sb['free'][fl] += 1
            sb['hits'][h1] += 1
            sb['shared'][h2] += 1
    obs = {}
    for k, o in enumerate(objs):
        sb = sub[o]
        shp = sb['shape']
        i0, i1 = sb['i0'], sb['i1']
        hits = np.clip(sb['hits'].reshape(shp), 0, 65535).astype(np.uint16)
        free = np.clip(sb['free'].reshape(shp), 0, 65535).astype(np.uint16)
        pts, cam, fr, ow = [], [], [], []
        for t in frames:
            s = S[t]
            mine = s['own3'] == k
            shd = (s['own3'] == SHARED) & ((s['tied3'] >> k) & 1).astype(bool)
            sel = mine | shd
            if not sel.any():
                continue
            Ti = np.linalg.inv(FR.T_co[o][t])
            pts.append((s['P'][sel].astype(np.float64) @ Ti[:3, :3].T + Ti[:3, 3]).astype(np.float32))
            cam.append(np.repeat(Ti[:3, 3][None].astype(np.float32), int(sel.sum()), 0))
            fr.append(np.full(int(sel.sum()), t, np.int32))
            ow.append(np.where(mine[sel], 0, 1).astype(np.uint8))
        cat = (lambda L, sh, dt: np.concatenate(L) if L else np.zeros(sh, dt))
        obs[o] = dict(pts=cat(pts, (0, 3), np.float32), cam=cat(cam, (0, 3), np.float32),
                      frame=cat(fr, (0,), np.int32), own=cat(ow, (0,), np.uint8),
                      lo=np.asarray(sb['lo'], np.float64), hi=np.asarray(sb['lo'] + np.asarray(shp) * c['vox'],
                                                                         np.float64),
                      vox=float(c['vox']), hits=hits, free=free,
                      shared=np.clip(sb['shared'].reshape(shp), 0, 65535).astype(np.uint16))
        obs[o]['state'] = BU.state_grid(hits, free)
    timing['pass4_grids_s'] = round(time.time() - t0_, 1)

    # ---------------- bundle meta
    roster_rec = None
    if roster:
        rp = os.path.realpath(roster)
        roster_rec = dict(path=roster, sha256=guard._INPUTS[rp]['sha256']) if rp in guard._INPUTS else None
    meta = dict(schema='gmg-episode/1', split=split, ep=int(ep), objects=objs, tier='P1',
                source='clean: gmg.extract_joint (passes 0-4, SPEC section 7 M2)', roster=roster_rec,
                T=T, stride=c['stride'], vox=c['vox'],
                tracks=dict(path=tp, sha256=guard._INPUTS[os.path.realpath(tp)]['sha256']),
                depth=dict(path=dp, sha256=guard._INPUTS[os.path.realpath(dp)]['sha256']),
                K=K.tolist(), table_band_m=c['band'],
                table=dict(n=table[0].tolist(), d=table[1], inlier_frac=round(table[2], 4), obj_pos=tab_obj,
                           source='frame-0 depth (full resolution), recon_mesh.table_plane RANSAC; per-frame refits '
                                  'in table_frames (camera frame, obs_points.py rule)'),
                table_frames={str(t): v for t, v in tables.items()},
                crop={o: {kk: vv for kk, vv in seed_info[o].items() if not kk.startswith('_')} for o in objs},
                census_pass1=census1, census_change=census_change,
                ownership={f'{objs[k]}|{objs[q]}': v for (k, q), v in pair_tie.items()},
                timing=timing, n_samples_pass0=n_samples)
    b = BU.Bundle(meta, obs, P)
    # contact (pass 4 census) + flags, sigma, jitter, band
    meta['contact'] = census4
    meta['sigma_mm'], meta['sigma_info'] = {}, {}
    t0_ = time.time()
    for o in objs:
        sg, inf = BU._sigma(obs[o], frames)
        meta['sigma_mm'][o] = round(sg * 1e3, 4)
        meta['sigma_info'][o] = inf
    timing['sigma_s'] = round(time.time() - t0_, 1)
    flags = []
    for o in objs:
        if seed_info[o].get('seed') == 'none':
            flags.append(f'no_seed:{o}')
        elif seed_info[o].get('seed') == 'det_f0_fallback':
            flags.append(f'seed_fallback:{o}')
    for k, o in enumerate(objs):
        for q, p in enumerate(objs):
            if q == k:
                continue
            rec = census4[f'{o}|{p}']
            Xp = b.samples(p)[0]
            j, npairs = CT.jitter(P, o, p, Xp, rec['contact'], c['stride'])
            pt = pair_tie[(k, q)]
            co_moving = pt['tied1_frac'] > c['comoving']
            p3 = pt['pass3']
            nres = p3['mask'] + p3['seed'] + p3['shared']
            unresolved = co_moving and p3['shared'] > 0.5 * max(pt['tied1'], 1)
            if p3['mask'] + p3['seed'] == 0:
                tbk = 'none'
            else:
                tbk = 'mask' if p3['mask'] >= p3['seed'] else 'seed'
            rec.update(j_mm=round(j * 1e3, 4), j_pairs=npairs, co_moving=bool(co_moving),
                       co_moving_unresolved=bool(unresolved), tie_break=tbk, tie_resolved=int(nres))
            rec['band_mm'] = round(b.band(o, p) * 1e3, 4)
            if census_change[f'{o}|{p}'] > c['unstable']:
                rec['census_unstable'] = True
                flags.append(f'census_unstable:{o}|{p}')
            if co_moving:
                flags.append(f'co_moving:{o}|{p}')
            if unresolved:
                flags.append(f'co_moving_unresolved:{o}|{p}')
    # pocc: partner surface samples (one per partner-OBSERVED voxel) moved into o's frame at each contact frame
    for o in objs:
        ob = obs[o]
        pocc = np.zeros(ob['hits'].shape, np.uint16)
        for p in b.partners(o):
            X, _, fid, _ = CT.partner_samples(b, o, p, meta['contact'][f'{o}|{p}']['contact'])
            if len(X) and pocc.size:
                vi, ok = CT._vox_index(X, ob['lo'], ob['vox'], pocc.shape)
                if ok.any():
                    key = np.unique(np.stack([np.ravel_multi_index(vi[ok].T, pocc.shape), fid[ok]], 1), axis=0)
                    np.add.at(pocc.reshape(-1), key[:, 0], 1)
        ob['pocc'] = pocc
        ob['args'] = json.dumps(dict(source='gmg.extract_joint', constants={kk: vv for kk, vv in c.items()},
                                     crop=meta['crop'][o]))
    meta['flags'] = flags
    timing['total_s'] = round(time.time() - t_start, 1)
    if aux_dir:
        os.makedirs(aux_dir, exist_ok=True)
        fr_l, pix_l, code_l, tied_l = [], [], [], []
        for t in frames:
            # every in-cube sample of the frame (the unowned ones with code NONE), so the B.3 diagnostic can tell
            # where an old hit went (DEVIATIONS 100)
            s = S[t]
            fr_l.append(np.full(len(s['pix']), t, np.int16))
            pix_l.append(s['pix'])
            code_l.append(s['own3'])
            tied_l.append(s['tied3'])
        np.savez_compressed(os.path.join(aux_dir, 'owners.npz'), frame=np.concatenate(fr_l),
                            pix=np.concatenate(pix_l), code=np.concatenate(code_l), tied=np.concatenate(tied_l),
                            objects=np.array(objs), W=IMG_W, H=IMG_H)
    return b
