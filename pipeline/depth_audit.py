#!/usr/bin/env python3
"""GT-free depth audit of our object poses against the stored stereo depth (2026-10-30). Inference side.

Renders our meshes at OUR per-frame object poses into the rectified left camera and compares the rendered surface
with the stored FoundationStereo depth of the same frame (perc2.py:96-139: depths_fs0.5.npy, (N,1000,1600) float32
metres, 0 = invalid, full rectified resolution with the full-resolution KR; FS_SCALE 0.5 only blurs detail). Depth
frame i, poses frame i and hands frame i are the same video frame (perc2.py:84-90, 461, 473), so no time shift.

Two modes:
  perception  --poses poses.npz                        cam_T_<obj>[t] = template frame -> rectified camera t
  reference   --ref REF.parquet --table table_frame.npz --poses poses.npz
              object poses from a FlashCHORD reference (table frame, w-first quaternions), mapped back with
              cam_T(t) = inv(world_T_cam[t]) @ inv(T_table_from_world) @ OBJ_ref(t) (world_T_cam from --poses).
Per frame t and object b (all thresholds fixed on 2026-10-30 before any ground truth was read; see PREREG.md in
docs/research/work/depth-audit-20261030/):
  render     Embree ray cast per object over the bounding box of its projected vertices -> z_b (rendered alone);
             z-buffer = min over objects, id = front-most object.
  hand mask  our MediaPipe joints (hands_refined.npz, world frame) on frames with valid_<side>, mapped with
             inv(world_T_cam[t]), bones drawn as capsules of radius --hand_r (1.2 cm), palm polygon filled.
  sel        pixels where b is front-most, eroded --erode (4) px (3x3 cross, as scipy binary_erosion), with valid depth
             and outside the hand mask. r = observed - rendered.
  behind     PRIMARY score: fraction of sel with r > +tau (1.5 cm): free space where our surface should be.
  front      exploratory: fraction of sel with r < -tau (an unmasked occluder, or our surface too far).
  med_r_cm   exploratory: signed median of r over sel (cm).
  vis_frac   (front-most & valid & not r < -tau, not eroded) / (pixels rendered alone). hidden = vis_frac < 0.2.
  valid      not hidden and n_sel >= --min_px (50). behind/front/med_r are NaN when not valid.
  *_any      exploratory: behind_any / front_any, the same fractions on every frame with n_sel >= min_px, hidden
             or not (an object pushed AWAY from the camera by > tau reads as occluded, hence hidden: self-test).
  rest_h_cm  only on frames our own track labels as resting (refine.moving_labels on world poses: < 0.5 cm and
             < 2 deg per frame, 3-frame means; rest runs >= 5 frames) and for objects not on or over another object
             (refine.support_relation on each rest frame, global table plane from mkref.fit_table on
             depth frame 0). Plane: RANSAC (200 hypotheses, 6 mm) on depth in a ring 8..40 px around the object's
             rendered-alone silhouette, other objects' silhouettes (+8 px) and the hand mask excluded; kept if the
             inlier share >= 0.5, its normal is within 25 deg of the global plane normal and it lies within 5 cm of
             the global plane (v2, 07:10 UTC: v1 picked the floor 60 cm below on eps 21/22/26/27). Value: signed distance
             (cm) of our mesh's lowest vertex to that plane (n toward the camera; > 0 floats, < 0 sinks).

Inputs are refused if they are, or may hold, ground truth (refine.assert_inference_input: 'observation', '.parquet',
'score_registered', 'per_frame', 'quarantine_gt', a 'baseline' directory, result.json/summary.json/log.txt). The
one exception is --ref: a parquet under a refs/<variant>/ directory whose schema has object_body_position and no
observation.* column (our own reference, built by mkref from our perception).

Outputs (--out DIR, new): audit.npz (per (T,B): behind, front, behind_any, front_any, med_r_cm, vis_frac, hidden, valid, n_sel, n_front,
n_alone, hand_frac, rest_h_cm, rest_mask, rest_inl, moving; plus names, frames), audit.json (inputs with sha256,
code version, parameters, self-test, per-object summaries, timing).

Usage:
  python -I pipeline/depth_audit.py --poses IN/poses.npz --depth depths_fs0.5.npy --hands IN/hands_refined.npz
      --meshes meshes/library_v3 --out OUT [--stride 1] [--frames 0,10] [--pylib DIR_WITH_EMBREEX] [--selftest F]
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import refine  # noqa: E402  (assert_inference_input, sha256, code_version, moving_labels, runs, Obj, support_relation)

T0 = time.time()
# MediaPipe hand topology (21 joints)
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
PALM = [0, 1, 5, 9, 13, 17]


def log(*a):
    print(f'[depth_audit {time.time() - T0:7.1f}s] ' + ' '.join(str(x) for x in a), flush=True)


# ======================================================================== guards
def assert_ref_parquet(path):
    """The one parquet allowance: our own FlashCHORD reference under refs/<variant>/, never a dataset parquet."""
    import pyarrow.parquet as pq
    for p in {str(path), os.path.realpath(str(path))}:
        low = p.lower().replace('\\', '/')
        parts = low.split('/')
        bad = [s for s in ('observation', 'score_registered', 'per_frame', 'quarantine_gt') if s in low]
        if 'baseline' in parts:
            bad.append('baseline/')
        if 'refs' not in parts[:-1]:
            bad.append('not under refs/<variant>/')
        if bad:
            raise AssertionError(f'depth_audit: refusing reference {path!r} ({p!r}; {bad})')
    cols = pq.read_schema(path).names
    if 'object_body_position' not in cols or 'object_body_wxyz' not in cols:
        raise AssertionError(f'depth_audit: {path!r} has no object_body_position/wxyz: not a FlashCHORD reference')
    if any(c.startswith('observation') for c in cols):
        raise AssertionError(f'depth_audit: {path!r} has observation.* columns (dataset ground truth): refused')
    return path


def checked(path):
    refine.assert_inference_input(path)
    return path


# ======================================================================== inputs
def load_ref(path, tab_path, W_C, names):
    import pyarrow.parquet as pq
    from scipy.spatial.transform import Rotation as Rot
    t = pq.read_table(assert_ref_parquet(path), columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    rn = [str(n) for n in t.column('object_body_names')[0].as_py()]
    pos = np.array(t.column('object_body_position')[0].as_py(), float)
    q = np.array(t.column('object_body_wxyz')[0].as_py(), float)
    T = len(pos) // (3 * len(rn)) if pos.ndim == 1 else len(pos)
    pos = pos.reshape(T, len(rn), 3)
    q = q.reshape(T, len(rn), 4)
    Z = np.load(checked(tab_path), allow_pickle=False)
    A_inv = np.linalg.inv(np.asarray(Z['T_table_from_world'], float))
    if sorted(rn) != sorted(names):
        raise SystemExit(f'reference objects {rn} != perception roster {names}')
    if T != len(W_C):
        raise SystemExit(f'reference T={T} != world_T_cam T={len(W_C)}')
    Winv = np.linalg.inv(W_C)
    camT = {}
    for n in names:
        i = rn.index(n)
        M = np.tile(np.eye(4), (T, 1, 1))
        M[:, :3, :3] = Rot.from_quat(q[:, i][:, [1, 2, 3, 0]]).as_matrix()
        M[:, :3, 3] = pos[:, i]
        camT[n] = Winv @ (A_inv @ M)
    return camT


def load_hands(path, T):
    if path is None:
        return {}
    Hh = np.load(checked(path), allow_pickle=False)
    out = {}
    for s in ('left', 'right'):
        if f'joints_{s}' in Hh.files:
            J = np.asarray(Hh[f'joints_{s}'], float)
            v = np.asarray(Hh[f'valid_{s}'], bool) if f'valid_{s}' in Hh.files else np.ones(len(J), bool)
            if len(J) != T:
                raise SystemExit(f'hands T={len(J)} != poses T={T}')
            out[s] = (J, v)
    return out


# ======================================================================== geometry
class Renderer:
    def __init__(self, mesh, K, H, W):
        from trimesh.ray.ray_pyembree import RayMeshIntersector
        self.V = np.asarray(mesh.vertices, float)
        self.isect = RayMeshIntersector(mesh)              # BVH once, in the body frame; rays are moved instead
        self.K, self.H, self.W = K, H, W

    def render(self, M, pad=2):
        """M: body -> camera. Returns (u0, v0, z) with z (h, w) camera depth (inf where no hit), or None."""
        K = self.K
        R, t = M[:3, :3], M[:3, 3]
        X = self.V @ R.T + t
        X = X[X[:, 2] > 0.05]
        if len(X) < 3:
            return None
        u = K[0, 0] * X[:, 0] / X[:, 2] + K[0, 2]
        v = K[1, 1] * X[:, 1] / X[:, 2] + K[1, 2]
        u0, u1 = int(np.floor(u.min())) - pad, int(np.ceil(u.max())) + pad
        v0, v1 = int(np.floor(v.min())) - pad, int(np.ceil(v.max())) + pad
        u0, v0, u1, v1 = max(u0, 0), max(v0, 0), min(u1, self.W - 1), min(v1, self.H - 1)
        if u1 <= u0 or v1 <= v0:
            return None
        uu, vv = np.meshgrid(np.arange(u0, u1 + 1), np.arange(v0, v1 + 1))
        dc = np.stack([(uu.ravel() - K[0, 2]) / K[0, 0], (vv.ravel() - K[1, 2]) / K[1, 1], np.ones(uu.size)], 1)
        db = dc @ R                                        # R^T d, row form
        ob = np.broadcast_to(-R.T @ t, db.shape).copy()
        loc, ir, _ = self.isect.intersects_location(ob, db, multiple_hits=False)
        z = np.full(uu.size, np.inf)
        if len(ir):
            z[ir] = (loc @ R.T + t)[:, 2]
        return u0, v0, z.reshape(uu.shape)


def hand_mask(hands, t, Winv_t, K, H, W, r_m):
    import cv2
    m = np.zeros((H, W), np.uint8)
    for s, (J, v) in hands.items():
        if not v[t]:
            continue
        X = J[t] @ Winv_t[:3, :3].T + Winv_t[:3, 3]
        if (X[:, 2] < 0.05).any() or not np.isfinite(X).all():
            continue
        uv = np.stack([K[0, 0] * X[:, 0] / X[:, 2] + K[0, 2], K[1, 1] * X[:, 1] / X[:, 2] + K[1, 2]], 1)
        if (np.abs(uv) > 1e5).any():
            continue
        rp = K[0, 0] * r_m / X[:, 2]
        p = np.round(uv).astype(np.int32)
        for i, j in BONES:
            th = int(max(1, round(rp[i] + rp[j])))         # thickness = 2 * mean radius
            cv2.line(m, tuple(p[i]), tuple(p[j]), 1, th)
        for i in range(21):
            cv2.circle(m, tuple(p[i]), int(max(1, round(rp[i]))), 1, -1)
        cv2.fillConvexPoly(m, cv2.convexHull(p[PALM]), 1)
    return m.astype(bool)


def erode(mask, it):
    import cv2
    if it <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    return cv2.erode(mask.astype(np.uint8), k, iterations=it, borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0


def dilate(mask, r):
    import cv2
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(mask.astype(np.uint8), k) > 0


def ransac_plane(P, rng, iters=200, thr=0.006):
    n_pts = len(P)
    idx = rng.integers(0, n_pts, size=(iters, 3))
    a, b, c = P[idx[:, 0]], P[idx[:, 1]], P[idx[:, 2]]
    N = np.cross(b - a, c - a)
    nn = np.linalg.norm(N, axis=1)
    ok = nn > 1e-9
    if not ok.any():
        return None
    N = N[ok] / nn[ok, None]
    d = -(N * a[ok]).sum(1)
    cnt = (np.abs(P @ N.T + d) < thr).sum(0)
    k = int(np.argmax(cnt))
    n, dd = N[k], d[k]
    inl = np.abs(P @ n + dd) < thr
    for _ in range(3):
        if inl.sum() < 3:
            return None
        c0 = P[inl].mean(0)
        n = np.linalg.svd(P[inl] - c0, full_matrices=False)[2][2]
        dd = -n @ c0
        inl = np.abs(P @ n + dd) < thr
    if dd < 0:                                             # camera (origin) on the positive side
        n, dd = -n, -dd
    return n, dd, float(inl.mean())


# ======================================================================== main
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--poses', required=True, help='perception poses.npz (world_T_cam, cam_T_<obj>)')
    p.add_argument('--ref', default=None, help='reference mode: our FlashCHORD reference parquet (refs/<variant>/...)')
    p.add_argument('--table', default=None, help='reference mode: mkref table_frame.npz')
    p.add_argument('--depth', required=True, help='depths_fs0.5.npy (N,1000,1600) float32 m, 0 invalid')
    p.add_argument('--hands', required=True, help='hands_refined.npz (KR, joints_<side>, valid_<side>)')
    p.add_argument('--meshes', default=os.path.join(REPO, 'meshes', 'library_v3'))
    p.add_argument('--out', required=True)
    p.add_argument('--stride', type=int, default=1)
    p.add_argument('--frames', default=None, help='comma list of frames (overrides --stride)')
    p.add_argument('--pylib', default=os.environ.get('DEPTH_AUDIT_PYLIB'), help='extra sys.path entry with embreex')
    p.add_argument('--tau', type=float, default=0.015)
    p.add_argument('--erode', type=int, default=4)
    p.add_argument('--hand_r', type=float, default=0.012)
    p.add_argument('--hidden_vis', type=float, default=0.20)
    p.add_argument('--min_px', type=int, default=50)
    p.add_argument('--ring_in', type=int, default=8)
    p.add_argument('--ring_out', type=int, default=40)
    p.add_argument('--rest_min', type=int, default=5)
    p.add_argument('--rest_inl', type=float, default=0.5)
    p.add_argument('--rest_tilt', type=float, default=25.0)
    p.add_argument('--rest_dmax', type=float, default=0.05, help='local plane offset from the global table plane (m)')
    p.add_argument('--no_rest', action='store_true', help='skip the rest-height metric')
    p.add_argument('--selftest', type=int, default=None, help='frame for the identity and planted-shift checks')
    p.add_argument('--force', action='store_true')
    return p.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    for pth in (a.poses, a.depth, a.hands, a.meshes, a.table):
        checked(pth)
    if a.ref:
        assert_ref_parquet(a.ref)
        if not a.table:
            raise SystemExit('--ref needs --table')
    if a.pylib:
        sys.path.insert(0, a.pylib)
    if os.path.exists(os.path.join(a.out, 'audit.npz')) and not a.force:
        raise SystemExit(f'{a.out}/audit.npz exists (new --out or --force)')
    os.makedirs(a.out, exist_ok=True)
    import trimesh
    import embreex  # noqa: F401  (fail early: the pure-python ray fallback is ~100x slower)

    P = np.load(a.poses, allow_pickle=False)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    W_C = np.asarray(P['world_T_cam'], float)
    T = len(W_C)
    if a.ref:
        camT = load_ref(a.ref, a.table, W_C, names)
        mode = 'reference'
    else:
        camT = {n: np.asarray(P[f'cam_T_{n}'], float) for n in names}
        mode = 'perception'
    D = np.load(a.depth, mmap_mode='r', allow_pickle=False)
    if D.ndim != 3 or D.dtype != np.float32:
        raise SystemExit(f'unexpected depth array {D.shape} {D.dtype}')
    N, H, W = D.shape
    if N != T:
        raise SystemExit(f'depth N={N} != poses T={T} (frame indexing would be ambiguous)')
    Hh = np.load(a.hands, allow_pickle=False)
    K = np.asarray(Hh['KR'], float)
    hands = load_hands(a.hands, T)
    B = len(names)
    log(f'mode {mode}, T={T}, objects {names}, depth {D.shape}, K fx={K[0, 0]:.2f} cx={K[0, 2]:.2f} cy={K[1, 2]:.2f}')

    objs = [refine.Obj(n, checked(os.path.join(a.meshes, f'{n}.glb'))) for n in names]
    rends = [Renderer(trimesh.load(o.path, force='mesh'), K, H, W) for o in objs]
    Vb = [r.V for r in rends]

    # --- labels from our own track (no ground truth)
    Ow = [W_C @ camT[n] for n in names]
    moving = np.stack([refine.moving_labels(Ow[b], objs[b].com) for b in range(B)], 1)
    rest_mask = np.zeros((T, B), bool)
    plane_info = None
    if not a.no_rest:
        ns = argparse.Namespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03)
        try:
            gn, gd, plane_info = refine.fit_plane(ns, np.asarray(D[0], np.float32), K, W_C[0],
                                                  {n: camT[n][0] for n in names}, objs)
        except SystemExit as e:
            log('global plane fit failed:', e)
            gn = None
        if gn is not None:
            for b in range(B):
                for s, e in refine.runs(~moving[:, b]):
                    if e - s < a.rest_min:
                        continue
                    for m in range(s, e):                  # support tested on every rest frame
                        _, rel = refine.support_relation(objs, [Ow[k][m] for k in range(B)], gn, gd)
                        rest_mask[m, b] = not (rel[b]['on_other'] or rel[b]['over_other'])
    frames = (np.array([int(x) for x in a.frames.split(',')]) if a.frames else np.arange(0, T, a.stride))
    F = len(frames)
    f32 = lambda: np.full((F, B), np.nan, np.float32)  # noqa: E731
    R = dict(behind=f32(), front=f32(), behind_any=f32(), front_any=f32(), med_r_cm=f32(), vis_frac=f32(),
             hand_frac=f32(), rest_h_cm=f32(),
             rest_inl=f32(), n_sel=np.zeros((F, B), np.int32), n_front=np.zeros((F, B), np.int32),
             n_alone=np.zeros((F, B), np.int32), hidden=np.ones((F, B), bool), valid=np.zeros((F, B), bool))
    Winv = np.linalg.inv(W_C)
    rng = np.random.default_rng(0)
    selftest = None

    def frame_metrics(d, Ms, hm, want_rest, fi=None, rec=None):
        rs = [rends[b].render(Ms[b]) for b in range(B)]
        zbuf = np.full((H, W), np.inf)
        idb = np.full((H, W), -1, np.int16)
        alone = []
        for b, r in enumerate(rs):
            if r is None:
                alone.append(None)
                continue
            u0, v0, z = r
            h, w = z.shape
            sl = (slice(v0, v0 + h), slice(u0, u0 + w))
            closer = z < zbuf[sl]
            zbuf[sl][closer] = z[closer]
            idb[sl][closer] = b
            alone.append((sl, np.isfinite(z)))
        out = []
        for b in range(B):
            row = dict(n_alone=0, n_front=0, n_sel=0, vis=np.nan, hidden=True, valid=False, behind=np.nan,
                       front=np.nan, med=np.nan, hand=np.nan, rest_h=np.nan, rest_inl=np.nan, behind_any=np.nan,
                       front_any=np.nan)
            if alone[b] is None or not alone[b][1].any():
                out.append(row)
                continue
            sl0, al = alone[b]
            # crop with a margin so erosion sees the image border as background
            v0, v1 = max(sl0[0].start - 6, 0), min(sl0[0].stop + 6, H)
            u0, u1 = max(sl0[1].start - 6, 0), min(sl0[1].stop + 6, W)
            sl = (slice(v0, v1), slice(u0, u1))
            fm = idb[sl] == b
            dd = d[sl]
            zz = zbuf[sl]
            ok = dd > 0
            r = np.where(fm & ok, dd - np.where(np.isfinite(zz), zz, 0), np.nan)
            occl = r < -a.tau
            row['n_alone'] = int(al.sum())
            row['n_front'] = int(fm.sum())
            row['vis'] = float((fm & ok & ~occl).sum() / max(al.sum(), 1))
            row['hidden'] = bool(row['vis'] < a.hidden_vis)
            hmc = hm[sl]
            row['hand'] = float((fm & hmc).sum() / max(fm.sum(), 1))
            sel = erode(fm, a.erode) & ok & ~hmc
            rv = r[sel]
            row['n_sel'] = int(sel.sum())
            row['valid'] = bool(not row['hidden'] and row['n_sel'] >= a.min_px)
            if row['n_sel'] >= a.min_px:                   # exploratory: also on hidden frames
                row['behind_any'] = float((rv > a.tau).mean())
                row['front_any'] = float((rv < -a.tau).mean())
            if row['valid']:
                row['behind'] = float((rv > a.tau).mean())
                row['front'] = float((rv < -a.tau).mean())
                row['med'] = float(np.median(rv) * 100)
            if want_rest[b] is not None:
                # ring around the rendered-alone silhouette in a crop with room for the ring
                rv0, rv1 = max(sl0[0].start - a.ring_out - 2, 0), min(sl0[0].stop + a.ring_out + 2, H)
                ru0, ru1 = max(sl0[1].start - a.ring_out - 2, 0), min(sl0[1].stop + a.ring_out + 2, W)
                slr = (slice(rv0, rv1), slice(ru0, ru1))
                me = np.zeros((rv1 - rv0, ru1 - ru0), bool)
                me[sl0[0].start - rv0:sl0[0].stop - rv0, sl0[1].start - ru0:sl0[1].stop - ru0] = al
                others = np.zeros_like(me)
                for k in range(B):
                    if k == b or alone[k] is None:
                        continue
                    slk, alk = alone[k]
                    gv0, gv1 = max(slk[0].start, rv0), min(slk[0].stop, rv1)
                    gu0, gu1 = max(slk[1].start, ru0), min(slk[1].stop, ru1)
                    if gv1 > gv0 and gu1 > gu0:
                        others[gv0 - rv0:gv1 - rv0, gu0 - ru0:gu1 - ru0] |= \
                            alk[gv0 - slk[0].start:gv1 - slk[0].start, gu0 - slk[1].start:gu1 - slk[1].start]
                ring = dilate(me, a.ring_out) & ~dilate(me, a.ring_in) & ~dilate(others, a.ring_in) & ~hm[slr]
                dr = d[slr]
                ring &= dr > 0
                vv, uu = np.nonzero(ring)
                if len(vv) >= 300:
                    if len(vv) > 4000:
                        pick = rng.choice(len(vv), 4000, replace=False)
                        vv, uu = vv[pick], uu[pick]
                    z = dr[vv, uu].astype(float)
                    uu, vv = uu + ru0, vv + rv0
                    Pc = np.stack([(uu - K[0, 2]) * z / K[0, 0], (vv - K[1, 2]) * z / K[1, 1], z], 1)
                    pl = ransac_plane(Pc, rng)
                    if pl is not None:
                        n_c, d_c, inl = pl
                        row['rest_inl'] = inl
                        gnc, gdc = want_rest[b]
                        tilt = np.degrees(np.arccos(np.clip(abs(n_c @ gnc), -1, 1)))
                        if inl >= a.rest_inl and tilt <= a.rest_tilt and abs(d_c - gdc) <= a.rest_dmax:
                            Xc = Vb[b] @ Ms[b][:3, :3].T + Ms[b][:3, 3]
                            row['rest_h'] = float((Xc @ n_c + d_c).min() * 100)
            out.append(row)
        return out, zbuf, idb

    for fi, t in enumerate(frames):
        d = np.asarray(D[t], np.float32)
        Ms = [camT[n][t] for n in names]
        hm = hand_mask(hands, t, Winv[t], K, H, W, a.hand_r)
        want = [None] * B
        if plane_info is not None:
            n_cam = Winv[t][:3, :3] @ gn                   # global plane in camera t: n_c = R^T n, d_c = n.t + d
            d_cam = float(gn @ W_C[t][:3, 3] + gd)
            want = [(n_cam, d_cam) if rest_mask[t, b] else None for b in range(B)]
        rows, zbuf, idb = frame_metrics(d, Ms, hm, want)
        for b, row in enumerate(rows):
            R['behind'][fi, b], R['front'][fi, b], R['med_r_cm'][fi, b] = row['behind'], row['front'], row['med']
            R['behind_any'][fi, b], R['front_any'][fi, b] = row['behind_any'], row['front_any']
            R['vis_frac'][fi, b], R['hand_frac'][fi, b] = row['vis'], row['hand']
            R['rest_h_cm'][fi, b], R['rest_inl'][fi, b] = row['rest_h'], row['rest_inl']
            R['n_sel'][fi, b], R['n_front'][fi, b], R['n_alone'][fi, b] = row['n_sel'], row['n_front'], row['n_alone']
            R['hidden'][fi, b], R['valid'][fi, b] = row['hidden'], row['valid']
        if a.selftest is not None and t == a.selftest:
            # (i) identity: observed := rendered where any object renders -> behind = front = 0, med = 0
            d_id = np.where(np.isfinite(zbuf), zbuf, d).astype(np.float32)
            r_id, _, _ = frame_metrics(d_id, Ms, np.zeros_like(hm), [None] * B)
            # (ii) planted 3 cm shift of each object in turn, along the optical axis (away) and sideways (+x)
            planted = {}
            for b in range(B):
                for tag, dv in (('away_z+3cm', [0, 0, 0.03]), ('toward_z-3cm', [0, 0, -0.03]), ('side_x+3cm', [0.03, 0, 0])):
                    Mp = [M.copy() for M in Ms]
                    Mp[b][:3, 3] += dv
                    r_p, _, _ = frame_metrics(d_id, Mp, np.zeros_like(hm), [None] * B)
                    planted[f'{names[b]}:{tag}'] = dict(behind=r_p[b]['behind'], front=r_p[b]['front'],
                                                        med_r_cm=r_p[b]['med'])
            selftest = dict(frame=int(t), identity={names[b]: dict(behind=r_id[b]['behind'], front=r_id[b]['front'],
                                                                   med_r_cm=r_id[b]['med']) for b in range(B)},
                            planted=planted)
            log('selftest', json.dumps(selftest))
        if fi % 25 == 0 or fi == F - 1:
            log(f'frame {t} ({fi + 1}/{F}) ' + ' '.join(
                f'{names[b]}: behind={R["behind"][fi, b]:.3f} front={R["front"][fi, b]:.3f} vis={R["vis_frac"][fi, b]:.2f}'
                f' rest_h={R["rest_h_cm"][fi, b]:.2f}' for b in range(B)))

    R['rest_mask'] = rest_mask[frames]
    R['moving'] = moving[frames]
    np.savez(os.path.join(a.out, 'audit.npz'), names=np.array(names), frames=frames, **R)

    def q(x, ps=(10, 50, 90)):
        x = x[np.isfinite(x)]
        return [round(float(v), 4) for v in np.percentile(x, ps)] if len(x) else None

    summ = {}
    for b, n in enumerate(names):
        v = R['valid'][:, b]
        summ[n] = dict(frames=int(F), valid=int(v.sum()), hidden=int(R['hidden'][:, b].sum()),
                       behind_p10_p50_p90=q(R['behind'][:, b]), behind_mean=round(float(np.nanmean(R['behind'][:, b])), 4) if v.any() else None,
                       share_behind_gt_0p2=round(float((R['behind'][v, b] > 0.2).mean()), 4) if v.any() else None,
                       front_p10_p50_p90=q(R['front'][:, b]), med_r_cm_p10_p50_p90=q(R['med_r_cm'][:, b]),
                       vis_frac_p10_p50_p90=q(R['vis_frac'][:, b]), hand_frac_mean=round(float(np.nanmean(R['hand_frac'][:, b])), 4),
                       rest_frames=int(R['rest_mask'][:, b].sum()), rest_h_measured=int(np.isfinite(R['rest_h_cm'][:, b]).sum()),
                       rest_h_cm_p10_p50_p90=q(R['rest_h_cm'][:, b]), moving_frames=int(R['moving'][:, b].sum()))
    inputs = {k: dict(path=os.path.abspath(v), sha256=refine.sha256(v)) for k, v in
              (('poses', a.poses), ('depth', a.depth), ('hands', a.hands), ('ref', a.ref), ('table', a.table)) if v}
    inputs['meshes'] = {n: dict(path=o.path, sha256=refine.sha256(o.path)) for n, o in zip(names, objs)}
    rec = dict(tool='pipeline/depth_audit.py', argv=sys.argv if argv is None else ['depth_audit.py'] + list(argv),
               time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), mode=mode,
               code=dict(refine.code_version(), depth_audit_sha256=refine.sha256(os.path.abspath(__file__))),
               inputs=inputs, objects=names, T=int(T), frames_audited=int(F), K=K.tolist(), depth_shape=list(D.shape),
               params={k: getattr(a, k) for k in ('tau', 'erode', 'hand_r', 'hidden_vis', 'min_px', 'ring_in',
                                                  'ring_out', 'rest_min', 'rest_inl', 'rest_tilt', 'rest_dmax', 'stride')},
               global_plane=None if plane_info is None else dict(plane_info, n=np.round(gn, 5).tolist(), d=round(float(gd), 5)),
               selftest=selftest, summary=summ, seconds=round(time.time() - T0, 1))
    json.dump(rec, open(os.path.join(a.out, 'audit.json'), 'w'), indent=1, default=float)
    log('wrote', a.out, json.dumps(summ))


if __name__ == '__main__':
    main()
