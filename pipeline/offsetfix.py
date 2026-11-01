"""Refine step S11 (31 Oct 2026, perception sprint "offset") [H until its public gate]: a GT-free correction of the
constant per-object pose offset by robust, occluder-masked depth registration of our mesh. GROUND-TRUTH-FREE: it reads
only our track, our stereo depth (frame 0 and, for mode mf, a fixed grid of frames of the depth cache), our frame-0
masks (det_f0.npz), our hands (hands_refined.npz) and our meshes, all through refine's checked inputs.

Hypothesis [H-OFF]: our tracks carry a constant per-object pose offset (Phase 1: three quarters of the tracker loss
with true templates is one constant body offset per object) because FoundationPose registers on contaminated or
partial masks and depth; a robust re-fit with the occluders removed measures that offset, and one constant body-frame
correction removes it.
Pre-registration and results: docs/research/work/perception-sprint-20261031/offset/README.md.

Per object j and used frame t (camera c_t = world_T_cam[t], half resolution, K/2):
  render      every roster object at its tracked pose (z-buffered splats of surface samples): label and depth maps.
  occluders   pixels whose front-most rendered object is another object; our hands (valid joints of hands_refined.npz:
              convex hull of the 21 projected joints plus a forearm strip, dilated by HAND_CM at the hand's depth);
              points within TABLE_CM above our frame-0 table plane (det_rules.table_plane, as S6).
  pixels      mode f0: the chosen frame-0 mask of det_f0.npz (SAM), minus the occluders;
              mode mf: our predicted visible silhouette of j (label == j), dilated by DIL px, minus the occluders.
              Valid depth only; points farther than BAND cm from our posed mesh are dropped (background bleed and
              unmodelled occluders in front).
  fit         point-to-plane ICP of the camera-facing surface samples of our mesh onto the back-projected points, from
              the tracked pose; each iteration keeps the TRIM closest pairs; <= ITERS iterations. Axisymmetric objects
              (--s6_axisym, the cups) get no update about their own axis (spin is free and unscored).
  accept      >= MIN_PTS points, the trimmed residual drops, the change is <= MAX_CM (centroid) and <= MAX_DEG.
              C_t = inv(T_t) T_icp is the per-frame body-frame correction.
  consensus   mode f0: C = C_0. mode mf: over the accepted frames among the object's NON-MOVING frames (refine labels)
              of the depth grid: rotation = chordal mean (members > 2.5 x the median deviation, min 2 deg, dropped),
              centroid shift = per-axis median (body frame); needs >= MIN_FRAMES frames, a centroid-shift spread
              (median absolute deviation from the consensus) <= SPREAD_CM and a rotation spread <= SPREAD_DEG.
  apply       whole   O'(t) = O(t) C on every frame (one constant body offset: the form the Phase-1 trk ceiling measures);
              prefix  only the frames before the object's perceived onset (> 1 cm or > 5 deg from frame 0), as F1.
"""
import os

import numpy as np

GRID = 48   # frames of the depth grid: unique(round(linspace(0, T - 1, 48))) (offset/scripts/fetch_depth.py)
MODEL_MAX = 60000   # camera-facing model samples used per ICP association (strided subsample)


def _rot():
    from scipy.spatial.transform import Rotation
    return Rotation


# ------------------------------------------------------------------ inputs
class DepthSource:
    """Half-resolution depth by frame: an npz {frames, depth (n, H/2, W/2)} (the grid fetched by range reads) or a full
    (T, H, W) depths_fs0.5.npy (memory-mapped; the same grid of frames is used)."""

    def __init__(self, path, T, depth0=None):
        self.path, self.T, self.d = path, T, {}
        self.frames, self.kind = [], 'none'
        if path and path.endswith('.npz'):
            z = np.load(path)
            fr = [int(x) for x in z['frames']]
            for k, f in enumerate(fr):
                self.d[f] = None
            self._z, self._fr = z, fr
            self.frames = fr
            self.kind = 'grid npz'
        elif path:
            self._m = np.load(path, mmap_mode='r')
            if self._m.shape[0] != T:
                raise SystemExit(f'S11: depth cache has {self._m.shape[0]} frames, the track {T}')
            self.frames = sorted(set(int(x) for x in np.round(np.linspace(0, T - 1, GRID))))
            self.kind = 'full cache'
        if not self.frames and depth0 is not None:
            self.kind = 'frame-0 depth only'
        if depth0 is not None and 0 not in self.frames:
            self.frames = [0] + list(self.frames)
        self.depth0 = depth0

    def get(self, t):
        if t == 0 and self.depth0 is not None:
            return np.asarray(self.depth0, np.float32)[::2, ::2]
        if hasattr(self, '_z'):
            return np.asarray(self._z['depth'][self._fr.index(t)], np.float32)
        return np.asarray(self._m[t], np.float32)[::2, ::2]


def mesh_model(o, seed=11):
    """Dense surface samples + normals of our mesh (count by area: ~one sample per 1.5 mm2, 30k-400k)."""
    import trimesh
    if getattr(o, '_s11', None) is not None:
        return o._s11
    n = int(np.clip(o.mesh.area / 1.5e-6, 30000, 400000))
    p, fi = trimesh.sample.sample_surface(o.mesh, n, seed=seed)
    o._s11 = (np.asarray(p, float), np.asarray(o.mesh.face_normals[fi], float))
    return o._s11


def body_axis(o):
    """Symmetry axis of our mesh (body frame): the covariance eigenvector with the most distinct eigenvalue."""
    P = mesh_model(o)[0]
    w, U = np.linalg.eigh(np.cov((P - P.mean(0)).T))
    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
    return U[:, k]


# ------------------------------------------------------------------ rendering and masks
def render(items, K2, shape):
    """items: [(label, 4x4 camera pose, samples)]; 2x2 splats, z-buffer. Returns (z, label)."""
    Hh, Ww = shape
    zb = np.full((Hh, Ww), np.inf)
    lab = np.full((Hh, Ww), -1)
    for s, T, P in items:
        X = P @ T[:3, :3].T + T[:3, 3]
        z = X[:, 2]
        ok = z > 0.05
        X, z = X[ok], z[ok]
        u = np.floor(X[:, 0] / z * K2[0, 0] + K2[0, 2]).astype(int)
        v = np.floor(X[:, 1] / z * K2[1, 1] + K2[1, 2]).astype(int)
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = u + du, v + dv
                m = (uu >= 0) & (uu < Ww) & (vv >= 0) & (vv < Hh)
                uu, vv, zz = uu[m], vv[m], z[m]
                o = np.argsort(-zz)
                uu, vv, zz = uu[o], vv[o], zz[o]
                upd = zz < zb[vv, uu]
                zb[vv[upd], uu[upd]] = zz[upd]
                lab[vv[upd], uu[upd]] = s
    return zb, lab


def hand_mask(H, t, Wt_inv, K2, shape, hand_cm):
    """Image region of our hands at frame t (valid joints): convex hull of the 21 joints + a forearm strip, dilated."""
    import cv2
    Hh, Ww = shape
    m = np.zeros((Hh, Ww), np.uint8)
    if H is None:
        return m.astype(bool)
    for s in ('left', 'right'):
        if f'joints_{s}' not in H.files:
            continue
        ok = H[f'valid_{s}'] if f'valid_{s}' in H.files else H[f'measured_{s}']
        if t >= len(ok) or not bool(ok[t]):
            continue
        J = np.asarray(H[f'joints_{s}'][t], float)
        if not np.isfinite(J).all():
            continue
        Xc = J @ Wt_inv[:3, :3].T + Wt_inv[:3, 3]
        if (Xc[:, 2] <= 0.05).any():
            continue
        zc = float(np.median(Xc[:, 2]))
        uv = np.c_[Xc[:, 0] / Xc[:, 2] * K2[0, 0] + K2[0, 2], Xc[:, 1] / Xc[:, 2] * K2[1, 1] + K2[1, 2]]
        hull = cv2.convexHull(np.round(uv).astype(np.int32))
        cv2.fillConvexPoly(m, hull, 1)
        a = J[0] - J[9]                                               # forearm: from the wrist away from the middle finger
        a = a / max(np.linalg.norm(a), 1e-9)
        E = J[0] + 0.25 * a
        Ec = Wt_inv[:3, :3] @ E + Wt_inv[:3, 3]
        if Ec[2] > 0.05:
            p0 = tuple(int(x) for x in np.round(uv[0]))
            p1 = tuple(int(x) for x in np.round([Ec[0] / Ec[2] * K2[0, 0] + K2[0, 2], Ec[1] / Ec[2] * K2[1, 1] + K2[1, 2]]))
            cv2.line(m, p0, p1, 1, thickness=max(3, int(0.06 * K2[0, 0] / zc)))
        r = max(2, int(round(hand_cm / 100 * K2[0, 0] / zc)))
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return m.astype(bool)


def backproject(mask, dep, K2):
    v, u = np.nonzero(mask & (dep > 0) & np.isfinite(dep))
    z = dep[v, u].astype(float)
    return np.c_[(u - K2[0, 2]) * z / K2[0, 0], (v - K2[1, 2]) * z / K2[1, 1], z]


# ------------------------------------------------------------------ fit
def icp(T0, cloud, model, iters, trim, axis_body=None):
    """Point-to-plane ICP of the camera-facing model samples onto CLOUD (camera frame), from T0. Returns
    (T, residual_start, residual_end) with trimmed mean |point-to-plane| residuals (m); (T0, None, None) on failure."""
    from scipy.spatial import cKDTree
    Rot = _rot()
    P, Nn = model
    T = T0.copy()
    r0 = None

    def assoc(T):
        Xw = P @ T[:3, :3].T + T[:3, 3]
        Nw = Nn @ T[:3, :3].T
        vis = np.nonzero((Xw * Nw).sum(1) < 0)[0]
        if len(vis) < 100:
            return None
        vis = vis[::max(1, len(vis) // MODEL_MAX)]                    # <= ~MODEL_MAX model points per association
        d, i = cKDTree(Xw[vis]).query(cloud)
        keep = d <= np.quantile(d, trim)
        return cloud[keep], Xw[vis][i[keep]], Nw[vis][i[keep]]

    for _ in range(iters):
        r = assoc(T)
        if r is None:
            return T0, None, None
        q, p, n = r
        b = ((q - p) * n).sum(1)
        res = float(np.abs(b).mean())
        if r0 is None:
            r0 = res
        Arot = np.cross(p, n)
        if axis_body is not None:                                    # no update about the object's own axis
            ax = T[:3, :3] @ axis_body
            e1 = np.cross(ax, [1.0, 0, 0] if abs(ax[0]) < 0.9 else [0, 1.0, 0])
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(ax, e1)
            B = np.c_[e1, e2]
            y = np.linalg.lstsq(np.c_[Arot @ B, n], b, rcond=None)[0]
            x = np.r_[B @ y[:2], y[2:]]
        else:
            x = np.linalg.lstsq(np.c_[Arot, n], b, rcond=None)[0]
        G = np.eye(4)
        G[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix()
        G[:3, 3] = x[3:]
        T = G @ T
        if np.linalg.norm(x) < 1e-6:
            break
    r = assoc(T)
    if r is None:
        return T0, None, None
    q, p, n = r
    return T, r0, float(np.abs(((q - p) * n).sum(1)).mean())


def frame_context(t, objs, O, Wt, shape, K2, H, a):
    """Per-frame render (label map) of every roster object at its tracked pose, and our hand mask."""
    Wi = np.linalg.inv(Wt)
    Tc = [Wi @ O[k][t] for k in range(len(objs))]
    _, lab = render([(k, Tc[k], mesh_model(objs[k])[0]) for k in range(len(objs))], K2, shape)
    return dict(Wi=Wi, Tc=Tc, lab=lab, hm=hand_mask(H, t, Wi, K2, shape, a.s11_hand_cm))


def frame_fit(j, t, objs, O, Wt, dep, K2, H, plane_w, a, det_mask=None, ctx=None):
    """Occluder-masked robust fit of object j at frame t. Returns (C_t or None, info)."""
    import cv2
    from scipy.spatial import cKDTree
    shape = dep.shape
    if ctx is None:
        ctx = frame_context(t, objs, O, Wt, shape, K2, H, a)
    Tc, lab, hm = ctx['Tc'], ctx['lab'], ctx['hm']
    models = [mesh_model(o) for o in objs]
    other = (lab >= 0) & (lab != j)
    if det_mask is not None:
        pix = det_mask & ~other & ~hm
        src = 'det_f0 mask'
    else:
        own = (lab == j).astype(np.uint8)
        if a.s11_dil > 0:
            own = cv2.dilate(own, np.ones((2 * a.s11_dil + 1, 2 * a.s11_dil + 1), np.uint8))
        pix = own.astype(bool) & ~other & ~hm
        src = 'predicted silhouette'
    info = dict(pixels=int(pix.sum()), hand_px=int((hm & (lab == j)).sum()), src=src)
    cloud = backproject(pix, dep, K2)
    if plane_w is not None and len(cloud):                           # drop the table (and points just above it)
        n_w, d_w = plane_w
        Xw = cloud @ Wt[:3, :3].T + Wt[:3, 3]
        cloud = cloud[(Xw @ n_w + d_w) > a.s11_table_cm / 100]
    P = models[j][0]
    Xm = P[::max(1, len(P) // 100000)] @ Tc[j][:3, :3].T + Tc[j][:3, 3]   # <= ~100k samples for the band test
    if len(cloud):
        dd = cKDTree(Xm).query(cloud)[0]
        cloud = cloud[dd < a.s11_band_cm / 100]
    info['points'] = int(len(cloud))
    if len(cloud) < a.s11_min_pts:
        info['reject'] = 'few points'
        return None, info
    axis = objs[j]._s11_axis if objs[j].name in a._s11_axisym else None
    Ti, r0, r1 = icp(Tc[j], cloud, models[j], a.s11_iters, a.s11_trim, axis)
    if r0 is None:
        info['reject'] = 'icp failed'
        return None, info
    C = np.linalg.inv(Tc[j]) @ Ti
    c = objs[j].V.mean(0)
    sh = float(np.linalg.norm(C[:3, :3] @ c + C[:3, 3] - c) * 100)
    rd = float(np.degrees(_rot().from_matrix(C[:3, :3]).magnitude()))
    info.update(shift_cm=round(sh, 3), rot_deg=round(rd, 3), res0_mm=round(r0 * 1000, 3), res1_mm=round(r1 * 1000, 3))
    if not r1 < r0:
        info['reject'] = 'residual did not drop'
        return None, info
    if sh > a.s11_max_cm or rd > a.s11_max_deg:
        info['reject'] = f'change {sh:.2f} cm / {rd:.1f} deg over the cap'
        return None, info
    return C, info


def consensus(Cs, c, a):
    """Robust mean of body corrections: chordal mean rotation (outliers dropped), per-axis median centroid shift."""
    Rot = _rot()
    R = Rot.from_matrix(np.stack([C[:3, :3] for C in Cs]))
    m = R.mean()
    dev = np.degrees((R * m.inv()).magnitude())
    keep = dev <= max(2.0, 2.5 * float(np.median(dev)))
    if keep.sum() >= max(2, len(Cs) // 2):
        m = R[keep].mean()
    dev = np.degrees((R * m.inv()).magnitude())
    sh = np.stack([C[:3, :3] @ c + C[:3, 3] - c for C in Cs])          # centroid shift, body frame
    med = np.median(sh, 0)
    spread_cm = float(np.median(np.linalg.norm(sh - med, axis=1)) * 100)
    Rm = m.as_matrix()
    C = np.eye(4)
    C[:3, :3] = Rm
    C[:3, 3] = c + med - Rm @ c
    return C, dict(n=len(Cs), rot_kept=int(keep.sum()), spread_cm=round(spread_cm, 3),
                   spread_deg=round(float(np.median(dev)), 3), shift_cm=round(float(np.linalg.norm(med) * 100), 3),
                   rot_deg=round(float(np.degrees(m.magnitude())), 3))


def onset_frame(Oj, c):
    Rot = _rot()
    cc = Oj[:, :3, :3] @ c + Oj[:, :3, 3]
    mv = (np.linalg.norm(cc - cc[0], axis=1) > 0.01) | \
         (np.degrees(Rot.from_matrix(np.einsum('nij,kj->nik', Oj[:, :3, :3], Oj[0, :3, :3])).magnitude()) > 5)
    return int(np.argmax(mv)) if mv.any() else len(Oj)


# ------------------------------------------------------------------ the step
def step_S11(a, objs, O, W_C, KR, H, lab, depth_src, det, plane_w, log):
    """O: list of (T,4,4) world poses (modified in place). Returns the pose_opt record."""
    T = len(O[0])
    K2 = np.diag([0.5, 0.5, 1.0]) @ np.asarray(KR, float)
    a._s11_axisym = {s.strip() for s in a.s6_axisym.split(',') if s.strip()}
    for o in objs:
        mesh_model(o)
        o._s11_axis = body_axis(o)
    rec = dict(mode=a.s11_mode, apply=a.s11_apply, depth=dict(source=depth_src.kind, path=depth_src.path,
                                                               frames=len(depth_src.frames)),
               det=None if det is None else 'det_f0.npz', table_plane=plane_w is not None, objects={}, corrected=[])
    masks = names_det = None
    if det is not None:
        names_det = [str(x) for x in det['names']]
        masks = np.unpackbits(det['masks'], axis=-1)[:, :, :int(det['mask_shape'][2])].astype(bool)
    C_all = {}
    cache = {}                                                        # frame -> (depth, render + hand mask): input poses
    for j, o in enumerate(objs):
        r = dict()
        c = o.V.mean(0)
        if a.s11_mode == 'f0':
            dm = None
            if masks is not None and o.name in names_det and int(det['chosen'][names_det.index(o.name)]) >= 0:
                dm = masks[int(det['chosen'][names_det.index(o.name)])]
            else:
                r['note'] = 'no det_f0 mask: predicted silhouette used'
            C, inf = frame_fit(j, 0, objs, O, W_C[0].astype(float), depth_src.get(0), K2, H, plane_w, a, dm)
            r['frames'] = {0: inf}
            if C is None:
                r['applied'] = False
                r['reason'] = inf.get('reject')
            else:
                r['applied'] = True
                C_all[j] = C
                r['correction'] = dict(shift_cm=inf['shift_cm'], rot_deg=inf['rot_deg'])
        else:
            mv = lab[j]['moving']
            fr = [t for t in depth_src.frames if t < T and not bool(mv[t])][:a.s11_frames]
            Cs, finfo = [], {}
            for t in fr:
                if t not in cache:
                    dep = depth_src.get(t)
                    cache[t] = (dep, frame_context(t, objs, O, W_C[t].astype(float), dep.shape, K2, H, a))
                dep, ctx = cache[t]
                C, inf = frame_fit(j, t, objs, O, W_C[t].astype(float), dep, K2, H, plane_w, a, None, ctx)
                finfo[t] = inf
                if C is not None:
                    Cs.append(C)
            r['frames_tried'] = len(fr)
            r['frames_accepted'] = len(Cs)
            r['frames'] = finfo
            if len(Cs) < a.s11_min_frames:
                r['applied'] = False
                r['reason'] = f'{len(Cs)} accepted frames < {a.s11_min_frames}'
            else:
                C, cs = consensus(Cs, c, a)
                r['consensus'] = cs
                why = []
                if cs['spread_cm'] > a.s11_spread_cm:
                    why.append(f'shift spread {cs["spread_cm"]:.2f} cm > {a.s11_spread_cm:g}')
                if cs['spread_deg'] > a.s11_spread_deg:
                    why.append(f'rotation spread {cs["spread_deg"]:.1f} deg > {a.s11_spread_deg:g}')
                if cs['shift_cm'] > a.s11_max_cm or cs['rot_deg'] > a.s11_max_deg:
                    why.append('consensus over the cap')
                r['applied'] = not why
                if why:
                    r['reason'] = '; '.join(why)
                else:
                    C_all[j] = C
                    r['correction'] = dict(shift_cm=cs['shift_cm'], rot_deg=cs['rot_deg'])
        if j in C_all:
            r['C_body'] = np.round(C_all[j], 8).tolist()
        r['onset'] = onset_frame(O[j], c)
        rec['objects'][o.name] = r
        log(f'S11 {o.name}: ' + (f'applied ({a.s11_apply}) {r["correction"]["shift_cm"]:.2f} cm / '
                                 f'{r["correction"]["rot_deg"]:.2f} deg' if r['applied'] else f'kept ({r.get("reason")})')
            + (f'; frames {r["frames_accepted"]}/{r["frames_tried"]}' if 'frames_tried' in r else ''))
    for j, C in C_all.items():                                        # apply after every fit (fits see the input poses)
        if a.s11_apply == 'whole':
            O[j] = O[j] @ C
        else:
            on = rec['objects'][objs[j].name]['onset']
            O[j][:on] = O[j][:on] @ C
        rec['corrected'].append(objs[j].name)
    for r in rec['objects'].values():                                 # keep pose_opt.json small: per-frame only in aux
        if 'frames' in r and len(r['frames']) > 3:
            fr = r.pop('frames')
            r['frames_summary'] = {k: v for k, v in list(fr.items())[:3]}
            r['frames_rejects'] = {}
            for v in fr.values():
                if 'reject' in v:
                    r['frames_rejects'][v['reject'].split(' ')[0]] = r['frames_rejects'].get(v['reject'].split(' ')[0], 0) + 1
    return rec
