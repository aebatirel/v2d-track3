"""Generator inputs (module M9 of SPEC section 7; CPU part, build step B2): contact-aware views and Phase-1 exclusive
masks (SPEC section 4, mechanism 2; PREREG A.6 row 'generator views'; PREREG B.11).

GT-free: our tracks (cam_T_<obj>, world_T_cam), our owned points (bundle), our FoundationStereo depth, MediaPipe hands,
the calibration and the colour video. No library mesh anywhere in the mask chain (the old scripts/crops.py seeded its
masks with library_v3 renders; nothing of it is used here except the camera chain). File access goes through the
guard (roles calib, depth, video, dev_hands); the caller passes arrays.

  camera_geometry(calib_path) -> Geo       rectified-left camera -> ego_cam_a (colour) chain, cam_a intrinsics
  hand_capsules(hands, poses, k) -> (A, B, r)   MediaPipe capsules of frame k in the rectified-left camera (SPEC M2:
                                           hand radius 30 mm, forearm 45 mm, 0.15 m long, as in obs_points.py)
  frame_layers(bundle, k, geo, hands, depth) -> Layers   per frame: every tracked object's projected footprint in
                                           cam_a (closed, filled) with its front depth, the hand pixels with their
                                           near depth, the valid-depth map (depth of frame k reprojected into cam_a)
  exclusive(layers, obj) -> (mask, parts)  exclusive mask = footprint - every partner footprint dilated by the A.6
                                           10 px (scaled to the cam_a focal) - hand pixels in front of the target
  frame_table(bundle, obj, geo, hands, depth, frames=None) -> [row]   per-frame statistics of one target
  choose_views(bundle, obj, census, n_max=6, *, table) -> (views, report)
                                           qualifying = separated from every partner (census), hands <= 25 % of the
                                           mask, visible area >= 0.6 x the episode maximum, valid depth >= 0.6 of the
                                           mask; farthest-point sampling on the view direction, >= 8 deg apart, <= 6
                                           views; one view (x seeds) if fewer than 2; mv_skipped if fewer than 3;
                                           contact mode (no separated frame): the same filters without separation,
                                           least partner overlap first
  masks(view, bundle, image, *, geo, hands, depth, refine=None) -> (mask, info)
                                           the exclusive mask of VIEW; optional refinement (SAM2 point prompts: target
                                           positives, partner negatives); a refined mask that gains any partner pixel
                                           is cut back to the projected mask; hands and partners are removed again
  partner_pixel_test(mask, bundle, obj, k, geo) -> dict   PREREG B.11: every partner owned point projected one by one
                                           and every partner footprint pixel must lie outside MASK
  inpaint_partners(image, mask, layers, obj, box) -> image   contact mode: partner pixels -> local background

Frames: k = track / stereo frame; the colour frame is j = k + a_offset (pipeline/hands_mp.py, a_offset 1).
"""
from __future__ import annotations

import dataclasses
import json
import math

import numpy as np

from gmg import guard, contact as CT

BONES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20))  # recon_mesh
Z_MIN = 0.05                        # points nearer than 5 cm to a camera are not projected (obs_points.py, contact.py)


def consts():
    c = dict(
        hands_max=guard.constant('genview_hands_max_share', 0.25, 'generic:PREREG A.6 generator views, hands <= 25 % '
                                                                   'of the mask'),
        vis_min=guard.constant('genview_visible_min_share', 0.6, 'generic:PREREG A.6 generator views, visible >= 0.6 '
                                                                 'x episode max'),
        depth_min=guard.constant('genview_depth_min_share', 0.6, 'generic:PREREG A.6 generator views, valid depth '
                                                                 '>= 0.6 of the mask'),
        n_max=guard.constant('genview_n_max', 6, 'generic:PREREG A.6 generator views, <= 6 views'),
        min_deg=guard.constant('genview_min_sep_deg', 8.0, 'generic:PREREG A.6 generator views, >= 8 deg apart'),
        mv_min=guard.constant('genview_mv_min_views', 3, 'generic:PREREG A.6 Pixal3D-MV only with >= 3 views'),
        partner_px=guard.constant('genmask_partner_dilate_px_rect', 10, 'generic:PREREG A.6 / SPEC section 4: '
                                                                        'partner pixels dilated by 10 px (10 px ~ '
                                                                        '10 mm at 0.5-0.6 m, focal 600 px)'),
        hand_r=guard.constant('hand_capsule_r_m', 0.03, 'generic:SPEC section 7 M2 hand radius 30 mm '
                                                       '(obs_points.py)'),
        arm_r=guard.constant('forearm_capsule_r_m', 0.045, 'generic:SPEC section 7 M2 forearm radius 45 mm '
                                                          '(obs_points.py)'),
        arm_len=guard.constant('forearm_capsule_len_m', 0.15, 'generic:obs_points.py forearm length 0.15 m'),
        zmax=guard.constant('depth_valid_zmax_m', 1.5, 'generic:obs_points.py zmax'),
        edge=guard.constant('depth_edge_thr_m', 0.02, 'generic:obs_points.py edge filter (5x5 range > 2 cm)'),
    )
    return c


# ------------------------------------------------------------------------------------------------ camera chain
@dataclasses.dataclass
class Geo:
    Ka: np.ndarray                  # cam_a intrinsics (distorted image)
    Da: np.ndarray                  # cam_a distortion (OpenCV, 14 coefficients)
    T_a_rect: np.ndarray            # 4x4: rectified-left camera -> cam_a
    W: int
    H: int
    K_rect: np.ndarray              # rectified-left camera matrix (1600 x 1000)
    a_offset: int = 1

    @property
    def f_ratio(self):
        return float(self.Ka[0, 0] / self.K_rect[0, 0])


def camera_geometry(calib_path, a_offset=1):
    """Rectified-left -> ego_cam_a, the chain of pipeline/hands_mp.py geometry() (also scripts/crops.py)."""
    import cv2
    rp = guard.open_input(calib_path, 'calib')
    with open(rp) as f:
        C = json.load(f)
    cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()
    R1, _, P1, _, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                              (1280, 800), R_lr, T_lr.reshape(3, 1), alpha=0,
                                              newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float)
    R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    T = np.eye(4)
    T[:3, :3] = R_ab.T @ R_lr @ R1.T
    T[:3, 3] = R_ab.T @ (T_lr - t_ab)
    res = cam['ego_cam_a'].get('resolution')
    if isinstance(res, dict):
        W, H = int(res['width']), int(res['height'])
    else:
        W, H = int(res[0]), int(res[1])
    return Geo(Ka=K_('ego_cam_a'), Da=D_('ego_cam_a'), T_a_rect=T, W=W, H=H, K_rect=np.asarray(P1[:3, :3], float),
               a_offset=int(a_offset))


def to_a(Xr, geo):
    """Rectified-left camera points -> cam_a camera points."""
    return Xr @ geo.T_a_rect[:3, :3].T + geo.T_a_rect[:3, 3]


def project_a(Xa, geo):
    """cam_a camera points -> (uv (n,2) float, z (n,), ok (n,) bool: z > Z_MIN and inside the image)."""
    import cv2
    Xa = np.asarray(Xa, np.float64).reshape(-1, 3)
    z = Xa[:, 2]
    uv = np.full((len(Xa), 2), np.nan)
    front = z > Z_MIN
    if front.any():
        p, _ = cv2.projectPoints(Xa[front].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), geo.Ka, geo.Da)
        uv[front] = p.reshape(-1, 2)
    ok = front & (uv[:, 0] >= 0) & (uv[:, 0] < geo.W) & (uv[:, 1] >= 0) & (uv[:, 1] < geo.H)
    ok &= np.isfinite(uv).all(1)
    return uv, z, ok


def view_dir(poses, obj, k, geo):
    """Unit direction from the object origin to the cam_a centre, in the object frame."""
    T = geo.T_a_rect @ poses[f'cam_T_{obj}'][k].astype(np.float64)
    c = np.linalg.inv(T)[:3, 3]
    return c / max(np.linalg.norm(c), 1e-12)


# ------------------------------------------------------------------------------------------------ footprints
def footprint(Xa, geo, spacing=CT.CEN_VOX):
    """Projected footprint of cam_a points (2 mm centroids): pixels hit, dilated by the point spacing at the points'
    median depth, closed (3x3), holes filled. Returns (mask HxW bool, zfront HxW float32 (min z of the points, spread
    by the same dilation; inf where no point), n_in, n_all)."""
    import cv2
    from scipy.ndimage import binary_fill_holes
    m = np.zeros((geo.H, geo.W), bool)
    zf = np.full((geo.H, geo.W), np.inf, np.float32)
    uv, z, ok = project_a(Xa, geo)
    n_all = int(len(Xa))
    if not ok.any():
        return m, zf, 0, n_all
    r = int(math.ceil(geo.Ka[0, 0] * spacing / max(float(np.median(z[ok])), Z_MIN)))
    ui, vi, zz = uv[ok, 0].astype(np.int64), uv[ok, 1].astype(np.int64), z[ok].astype(np.float32)
    order = np.argsort(-zz)                                  # far first: the nearest point wins its pixel
    zf[vi[order], ui[order]] = zz[order]
    x0, y0 = max(int(ui.min()) - r - 3, 0), max(int(vi.min()) - r - 3, 0)
    x1, y1 = min(int(ui.max()) + r + 4, geo.W), min(int(vi.max()) + r + 4, geo.H)
    sub = np.isfinite(zf[y0:y1, x0:x1]).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    sub = cv2.dilate(sub, ker)
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    sub = binary_fill_holes(sub.astype(bool))
    m[y0:y1, x0:x1] = sub
    zs = zf[y0:y1, x0:x1]
    zs = cv2.erode(np.where(np.isfinite(zs), zs, 1e6).astype(np.float32), ker)   # min filter = front depth spread
    zs[zs >= 1e6] = np.inf
    zf[y0:y1, x0:x1] = np.where(sub, zs, np.inf)
    return m, zf, int(ok.sum()), n_all


def hand_capsules(hands, poses, k, c=None):
    """Capsules (A (n,3), B (n,3), r (n,)) of frame k in the rectified-left camera: MediaPipe bones at the hand radius
    plus a forearm from the wrist away from the middle-finger knuckle (pipeline/recon_mesh.hand_segments)."""
    c = c or consts()
    A, B, r = [], [], []
    if hands is None:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0)
    C_W = np.linalg.inv(poses['world_T_cam'][k].astype(np.float64))
    for side in ('left', 'right'):
        v = hands.get(f'valid_{side}')
        if v is None or k >= len(v) or not v[k]:
            continue
        J = hands[f'joints_{side}'][k].astype(np.float64) @ C_W[:3, :3].T + C_W[:3, 3]
        if not np.all(np.isfinite(J)):
            continue
        for i, j in BONES:
            A.append(J[i]); B.append(J[j]); r.append(c['hand_r'])
        d = J[0] - J[9]
        d /= max(np.linalg.norm(d), 1e-9)
        A.append(J[0]); B.append(J[0] + c['arm_len'] * d); r.append(c['arm_r'])
    return np.array(A).reshape(-1, 3), np.array(B).reshape(-1, 3), np.array(r, float)


def hand_layer(caps, geo):
    """Render capsules into cam_a: (mask HxW bool, znear HxW float32 = smallest z - r over the capsules covering the
    pixel). Each capsule is drawn as discs of radius f r / z at samples spaced <= r / 2 along its axis."""
    import cv2
    A, B, R = caps
    zn = np.full((geo.H, geo.W), np.inf, np.float32)
    if len(A) == 0:
        return np.zeros((geo.H, geo.W), bool), zn
    for a, b, r in zip(to_a(A, geo), to_a(B, geo), R):
        n = int(math.ceil(np.linalg.norm(b - a) / (r / 2))) + 1
        S = a[None] + np.linspace(0, 1, n)[:, None] * (b - a)[None]
        uv, z, _ = project_a(S, geo)
        for (u, v), zz in zip(uv, z):
            if not (zz > Z_MIN and np.isfinite(u) and np.isfinite(v)):
                continue
            rp = int(math.ceil(geo.Ka[0, 0] * r / zz))
            x0, x1 = int(u) - rp, int(u) + rp + 1
            y0, y1 = int(v) - rp, int(v) + rp + 1
            if x1 <= 0 or y1 <= 0 or x0 >= geo.W or y0 >= geo.H:
                continue
            disc = np.zeros((y1 - y0, x1 - x0), np.uint8)
            cv2.circle(disc, (int(u) - x0, int(v) - y0), rp, 1, -1)
            cx0, cy0 = max(x0, 0), max(y0, 0)
            cx1, cy1 = min(x1, geo.W), min(y1, geo.H)
            d = disc[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0].astype(bool)
            sl = zn[cy0:cy1, cx0:cx1]
            sl[d] = np.minimum(sl[d], np.float32(zz - r))
    return np.isfinite(zn), zn


def depth_layer(D, geo, roi_rect, c=None):
    """Valid-depth map in cam_a (HxW bool) and its z-buffer (HxW float32) from the rectified-left depth D of one frame:
    obs_points.py validity (finite, 0.05 m < z < zmax, 5x5 dilate - erode <= edge threshold) inside ROI_RECT
    (x0, y0, x1, y1 on the rectified image), back-projected, moved into cam_a, projected with its distortion, and
    splatted with a 3x3 closing (one rectified pixel covers about f_a / f_rect = 1.9 cam_a pixels)."""
    import cv2
    c = c or consts()
    x0, y0, x1, y1 = roi_rect
    pad = 2
    xa, ya = max(x0 - pad, 0), max(y0 - pad, 0)
    xb, yb = min(x1 + pad, D.shape[1]), min(y1 + pad, D.shape[0])
    Dt = np.array(D[ya:yb, xa:xb], dtype=np.float32)
    Dz = np.where(np.isfinite(Dt), Dt, 0).astype(np.float32)
    k5 = np.ones((5, 5), np.uint8)
    edge = (cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > c['edge']
    ok = np.isfinite(Dt) & (Dt > Z_MIN) & (Dt < c['zmax']) & ~edge
    vv, uu = np.nonzero(ok)
    d = Dt[vv, uu].astype(np.float64)
    uu = uu + xa; vv = vv + ya
    K = geo.K_rect
    Pr = np.stack([(uu - K[0, 2]) * d / K[0, 0], (vv - K[1, 2]) * d / K[1, 1], d], 1)
    uv, z, inn = project_a(to_a(Pr, geo), geo)
    zb = np.full((geo.H, geo.W), np.inf, np.float32)
    if inn.any():
        ui, vi, zz = uv[inn, 0].astype(np.int64), uv[inn, 1].astype(np.int64), z[inn].astype(np.float32)
        order = np.argsort(-zz)
        zb[vi[order], ui[order]] = zz[order]
        bx0, by0 = max(int(ui.min()) - 2, 0), max(int(vi.min()) - 2, 0)
        bx1, by1 = min(int(ui.max()) + 3, geo.W), min(int(vi.max()) + 3, geo.H)
        sub = zb[by0:by1, bx0:bx1]
        fill = cv2.erode(np.where(np.isfinite(sub), sub, 1e6).astype(np.float32), np.ones((3, 3), np.uint8))
        sub2 = np.where(np.isfinite(sub), sub, fill)
        sub2[sub2 >= 1e6] = np.inf
        zb[by0:by1, bx0:bx1] = sub2
    return np.isfinite(zb), zb


# ------------------------------------------------------------------------------------------------ per-frame layers
@dataclasses.dataclass
class Layers:
    k: int
    fp: dict                        # obj -> footprint mask (HxW bool), closed and filled
    zf: dict                        # obj -> front depth (HxW float32)
    n_in: dict                      # obj -> centroids inside the image
    n_all: dict                     # obj -> centroids
    hand: np.ndarray                # hand pixels (HxW bool)
    hand_z: np.ndarray              # near depth of the hand capsules (HxW float32)
    valid: np.ndarray               # valid reprojected depth (HxW bool) or None
    depth_z: np.ndarray             # its z-buffer or None
    partner_px: int                 # partner dilation in cam_a pixels


def partner_dilate_px(geo, c=None):
    """A.6 / SPEC section 4: partner pixels dilated by 10 px, a constant stated on the rectified image (focal 600 px,
    10 px ~ 10 mm at 0.5-0.6 m); on cam_a (focal 1150 px) the same 10 mm is round(10 x f_a / f_rect) = 19 px."""
    c = c or consts()
    return int(round(c['partner_px'] * geo.f_ratio))


def _rect_roi(cen_by_obj, poses, k, geo, margin=40):
    """Bounding box on the rectified image of every object's projected centroids, grown by MARGIN pixels."""
    K = geo.K_rect
    us, vs = [], []
    for o, X in cen_by_obj.items():
        if not len(X):
            continue
        T = poses[f'cam_T_{o}'][k].astype(np.float64)
        P = X @ T[:3, :3].T + T[:3, 3]
        P = P[P[:, 2] > Z_MIN]
        if not len(P):
            continue
        us.append(K[0, 0] * P[:, 0] / P[:, 2] + K[0, 2]); vs.append(K[1, 1] * P[:, 1] / P[:, 2] + K[1, 2])
    if not us:
        return None
    u, v = np.concatenate(us), np.concatenate(vs)
    return (int(max(np.floor(u.min()) - margin, 0)), int(max(np.floor(v.min()) - margin, 0)),
            int(min(np.ceil(u.max()) + margin, 1600)), int(min(np.ceil(v.max()) + margin, 1000)))


def centroids_by_obj(bundle):
    """2 mm centroids of every object's owned points (object frame), cached on the bundle."""
    cache = getattr(bundle, '_gen_cen', None)
    if cache is None:
        cache = {}
        for o in bundle.objects:
            ob = bundle.obs(o)
            own = np.asarray(ob.get('own', np.zeros(len(ob['pts']), np.uint8)))
            cache[o] = CT.centroids(np.asarray(ob['pts'], np.float64)[own == 0])
        bundle._gen_cen = cache
    return cache


def frame_layers(bundle, k, geo, hands=None, depth=None, c=None):
    c = c or consts()
    cen = centroids_by_obj(bundle)
    fp, zf, n_in, n_all = {}, {}, {}, {}
    for o in bundle.objects:
        T = geo.T_a_rect @ bundle.poses[f'cam_T_{o}'][k].astype(np.float64)
        Xa = cen[o] @ T[:3, :3].T + T[:3, 3]
        fp[o], zf[o], n_in[o], n_all[o] = footprint(Xa, geo)
    hm, hz = hand_layer(hand_capsules(hands, bundle.poses, k, c), geo)
    valid = dz = None
    if depth is not None and k < len(depth):
        roi = _rect_roi(cen, bundle.poses, k, geo)
        if roi is not None:
            valid, dz = depth_layer(depth[k], geo, roi, c)
    return Layers(k=k, fp=fp, zf=zf, n_in=n_in, n_all=n_all, hand=hm, hand_z=hz, valid=valid, depth_z=dz,
                  partner_px=partner_dilate_px(geo, c))


def _dilate(m, px):
    import cv2
    if px <= 0 or not m.any():
        return m.copy()
    ys, xs = np.nonzero(m)
    y0, x0 = max(ys.min() - px - 1, 0), max(xs.min() - px - 1, 0)
    y1, x1 = min(ys.max() + px + 2, m.shape[0]), min(xs.max() + px + 2, m.shape[1])
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    out = np.zeros_like(m)
    out[y0:y1, x0:x1] = cv2.dilate(m[y0:y1, x0:x1].astype(np.uint8), ker).astype(bool)
    return out


def partner_union(layers, obj, dilate=True):
    """Union of every other tracked object's footprint (dilated by the partner margin if DILATE)."""
    P = np.zeros_like(layers.fp[obj])
    for p, m in layers.fp.items():
        if p != obj:
            P |= m
    return _dilate(P, layers.partner_px) if dilate else P


def exclusive(layers, obj):
    """Exclusive mask of OBJ: its footprint minus every partner's footprint dilated by the partner margin minus hand
    pixels in front of it (capsule near depth <= the target's front depth; where the target has no front depth, a
    hand pixel always counts). Returns (mask, parts)."""
    S = layers.fp[obj]
    Pd = partner_union(layers, obj, dilate=True)
    Sp = S & ~Pd
    Hf = layers.hand & (layers.hand_z <= layers.zf[obj]) & Sp
    M = Sp & ~Hf
    return M, dict(S=S, Pd=Pd, Sp=Sp, H=Hf)


def frame_row(layers, bundle, obj, geo):
    M, q = exclusive(layers, obj)
    nS, nSp, nM = int(q['S'].sum()), int(q['Sp'].sum()), int(M.sum())
    row = dict(k=int(layers.k), j=int(layers.k) + int(geo.a_offset), area=nM, area_fp=nS,
               partner_share=round(float((q['S'] & q['Pd']).sum()) / max(nS, 1), 4),
               hand_share=round(float(q['H'].sum()) / max(nSp, 1), 4),
               in_image=round(layers.n_in[obj] / max(layers.n_all[obj], 1), 4))
    if layers.valid is not None:
        row['depth_share'] = round(float((M & layers.valid).sum()) / max(nM, 1), 4)
        agree = M & layers.valid & (np.abs(layers.depth_z - layers.zf[obj]) <= 0.03)
        row['depth_agree_share'] = round(float(agree.sum()) / max(nM, 1), 4)     # diagnostic only (not a filter)
    else:
        row['depth_share'] = None
    row['dir'] = [round(float(x), 6) for x in view_dir(bundle.poses, obj, layers.k, geo)]
    return row


def frame_table(bundle, obj, geo, hands=None, depth=None, frames=None, n_video=None, c=None, objs=None):
    """Per-frame rows of every target in OBJS (default [obj]) over FRAMES (default: the object's good frames that
    have a colour frame k + a_offset < n_video and a depth frame). Returns {obj: [row]}."""
    c = c or consts()
    objs = objs or [obj]
    fr = frames if frames is not None else sorted(set().union(*[bundle.good_frames(o) for o in objs]))
    if n_video is not None:
        fr = [k for k in fr if k + geo.a_offset < n_video]
    if depth is not None:
        fr = [k for k in fr if k < len(depth)]
    out = {o: [] for o in objs}
    good = {o: set(bundle.good_frames(o)) for o in objs}
    for k in fr:
        L = frame_layers(bundle, k, geo, hands, depth, c)
        for o in objs:
            if k in good[o]:
                out[o].append(frame_row(L, bundle, o, geo))
    return out


# ------------------------------------------------------------------------------------------------ view choice
@dataclasses.dataclass
class View:
    obj: str
    k: int                          # track / stereo frame
    j: int                          # colour frame (k + a_offset)
    mode: str                       # 'separated' | 'contact'
    dir: list
    area: int
    hand_share: float
    depth_share: float
    partner_share: float
    rank: int = 0                   # order of choice (0 = first, the largest visible area or least overlap)
    min_angle_deg: float = None     # angle to the nearest earlier view


def _angle(a, b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1.0, 1.0))))


def _span(D):
    if len(D) < 2:
        return 0.0
    G = np.clip(D @ D.T, -1, 1)
    return float(np.degrees(np.arccos(G.min())))


def _p90(D):
    if not len(D):
        return None
    m = D.mean(0)
    m /= max(np.linalg.norm(m), 1e-12)
    return float(np.percentile(np.degrees(np.arccos(np.clip(D @ m, -1, 1))), 90))


def separated_frames(census, obj, partners):
    """Frames in which OBJ is separated from every partner (SPEC section 4); None if OBJ has no partner (every frame
    then counts as separated)."""
    if not partners:
        return None
    return set(CT.separated_for(census, obj, partners))


def choose_views(bundle, obj, census, n_max=6, *, table, c=None):
    """SPEC section 4 mechanism 2. TABLE: frame rows of OBJ (frame_table). Returns (views, report).

    Separated mode (some frame is separated from every partner, or OBJ has no partner): a frame qualifies if it is
    separated, hands cover <= 25 % of its mask, its visible area (exclusive mask) is >= 0.6 x the episode maximum and
    >= 0.6 of its mask has valid depth. The first view is the qualifying frame with the largest visible area (ties:
    smaller hand share, then earlier frame); then farthest-point sampling on the view direction: the qualifying frame
    farthest (in angle) from the views chosen so far, while that angle is >= 8 deg, up to N_MAX views. One view means
    the generator gets that view times several seeds; fewer than 3 views mean Pixal3D-MV is skipped.
    Contact mode (no frame is separated): the same filters without separation; frames in order of least partner
    overlap (share of the target footprint under the dilated partner pixels; ties: larger area, earlier frame); a
    frame is taken if it is >= 8 deg from every view taken so far, up to N_MAX views.
    No qualifying frame: no view (flag no_qualifying_view; the generator is not run for this object)."""
    c = c or consts()
    n_max = int(min(n_max, c['n_max']))
    partners = bundle.partners(obj)
    sep = separated_frames(census, obj, partners)
    rows = [r for r in table if r['area'] > 0]
    amax = max([r['area'] for r in rows], default=0)
    flags = []

    def passes(r):
        return (r['hand_share'] <= c['hands_max'] and r['area'] >= c['vis_min'] * amax and
                r['depth_share'] is not None and r['depth_share'] >= c['depth_min'])

    contact_mode = sep is not None and len(sep) == 0
    if contact_mode:
        flags.append('contact_mode')
        pool = [r for r in rows if passes(r)]
    else:
        pool = [r for r in rows if (sep is None or r['k'] in sep) and passes(r)]
    D = np.array([r['dir'] for r in pool], float).reshape(-1, 3)
    chosen = []
    if pool:
        if not contact_mode:
            first = min(range(len(pool)), key=lambda i: (-pool[i]['area'], pool[i]['hand_share'], pool[i]['k']))
            chosen.append((first, None))
            while len(chosen) < n_max:
                C = D[[i for i, _ in chosen]]
                ang = np.degrees(np.arccos(np.clip(D @ C.T, -1, 1))).min(1)
                for i, _ in chosen:
                    ang[i] = -1
                best = float(ang.max())
                if best < c['min_deg']:
                    break
                cand = np.nonzero(ang == best)[0]
                i = min(cand, key=lambda i: (-pool[i]['area'], pool[i]['k']))
                chosen.append((int(i), best))
        else:
            order = sorted(range(len(pool)), key=lambda i: (pool[i]['partner_share'], -pool[i]['area'],
                                                            pool[i]['k']))
            for i in order:
                if len(chosen) >= n_max:
                    break
                if not chosen:
                    chosen.append((i, None))
                    continue
                a = min(_angle(D[i], D[j]) for j, _ in chosen)
                if a >= c['min_deg']:
                    chosen.append((i, a))
    else:
        flags.append('no_qualifying_view')
    views = []
    for rank, (i, a) in enumerate(chosen):
        r = pool[i]
        views.append(View(obj=obj, k=int(r['k']), j=int(r['j']), mode='contact' if contact_mode else 'separated', dir=r['dir'], area=int(r['area']),
                          hand_share=float(r['hand_share']), depth_share=float(r['depth_share']),
                          partner_share=float(r['partner_share']), rank=rank,
                          min_angle_deg=None if a is None else round(float(a), 2)))
    if len(views) == 1:
        flags.append('one_view')
    if 0 < len(views) < c['mv_min']:
        flags.append('mv_skipped')
    Dc = np.array([v.dir for v in views], float).reshape(-1, 3)
    n_rows = len(rows)
    rep = dict(obj=obj, partners=partners, mode='contact' if contact_mode else 'separated', flags=flags,
               frames=n_rows, separated=None if sep is None else len(sep),
               separated_in_table=None if sep is None else sum(r['k'] in sep for r in rows),
               area_max=amax, qualifying=len(pool),
               fail_counts=dict(hands=sum(r['hand_share'] > c['hands_max'] for r in rows),
                                area=sum(r['area'] < c['vis_min'] * amax for r in rows),
                                depth=sum(r['depth_share'] is None or r['depth_share'] < c['depth_min']
                                          for r in rows)),
               pool_span_deg=round(_span(D), 2), pool_p90_deg=None if not len(D) else round(_p90(D), 2),
               views=[dataclasses.asdict(v) for v in views], n_views=len(views),
               views_span_deg=round(_span(Dc), 2),
               view_angles_deg=[[round(_angle(a, b), 2) for b in Dc] for a in Dc])
    return views, rep


def colour_frame(view, geo):
    return int(view.k) + int(geo.a_offset)


# ------------------------------------------------------------------------------------------------ masks of a view
def _sample_in(mask, n, rng, erode_px=0):
    """N prompt points (x, y) spread over MASK (farthest-point sampling on its pixels, after an erosion if possible)."""
    import cv2
    m = mask
    if erode_px > 0:
        e = cv2.erode(mask.astype(np.uint8), np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)).astype(bool)
        if e.sum() >= n:
            m = e
    ys, xs = np.nonzero(m)
    if not len(xs):
        return np.zeros((0, 2), int)
    P = np.stack([xs, ys], 1).astype(float)
    if len(P) > 20000:
        P = P[rng.choice(len(P), 20000, replace=False)]
    c0 = P.mean(0)
    pts = [int(np.argmin(((P - c0) ** 2).sum(1)))]
    d = ((P - P[pts[0]]) ** 2).sum(1)
    while len(pts) < min(n, len(P)):
        i = int(np.argmax(d))
        pts.append(i)
        d = np.minimum(d, ((P - P[i]) ** 2).sum(1))
    return P[pts].astype(int)


def prompts(layers, obj, M, n_pos=5, n_neg=5, seed=0):
    """SPEC section 4: point prompts on the target (N_POS spread over its exclusive mask, eroded) and the partner's
    pixels as negatives (PREREG A.6: 5 points per partner, spread over its footprint)."""
    rng = np.random.default_rng(seed)
    pos = _sample_in(M, n_pos, rng, erode_px=6)
    neg = []
    for p, m in layers.fp.items():
        if p == obj:
            continue
        ys, xs = np.nonzero(m)
        if len(xs):
            neg.append(_sample_in(m, n_neg, rng, erode_px=6))
    neg = np.concatenate(neg) if neg else np.zeros((0, 2), int)
    return pos, neg


def masks(view, bundle, image=None, *, geo, hands=None, depth=None, refine=None, c=None):
    """Exclusive mask of VIEW (HxW bool) and info. REFINE: optional callable (image, pos_points, neg_points,
    projected_mask) -> refined HxW bool mask (SAM2). The refined mask is used only if it gains no partner pixel
    (dilated partner footprint); else it is cut back to the projected mask (flag refine_cut_back). Hand pixels and
    the dilated partner pixels are removed from the result in every case."""
    c = c or consts()
    L = frame_layers(bundle, view.k, geo, hands, depth, c)
    M, q = exclusive(L, view.obj)
    info = dict(k=view.k, j=colour_frame(view, geo), projected_area=int(M.sum()), refined=False, flags=[])
    F = M
    if refine is not None and image is not None:
        pos, neg = prompts(L, view.obj, M)
        R = np.asarray(refine(image, pos, neg, M), bool)
        info.update(refined=True, pos=pos.tolist(), neg=neg.tolist(), refined_area=int(R.sum()),
                    refined_gain_partner=int((R & q['Pd']).sum()),
                    refined_iou_projected=round(float((R & M).sum()) / max(float((R | M).sum()), 1), 4))
        if (R & q['Pd']).any():
            info['flags'].append('refine_cut_back')
            F = M
        else:
            F = R & ~q['Pd'] & ~(L.hand & (L.hand_z <= L.zf[view.obj]))
        info['final_area'] = int(F.sum())
    else:
        info['final_area'] = int(F.sum())
    return F, dict(info=info, layers=L, parts=q, projected=M)


def partner_pixel_test(mask, bundle, obj, k, geo, layers=None):
    """PREREG B.11: no partner pixel inside MASK. Partner pixels = (a) every owned point of every partner projected
    one by one into cam_a at frame k (no centroids, no dilation) and (b) every partner footprint pixel (closed,
    filled, not dilated). Returns counts and the smallest pixel distance from MASK to (b)."""
    import cv2
    res = dict(points_inside=0, points_projected=0, footprint_inside=0, min_dist_px=None)
    Pall = np.zeros_like(mask)
    L = layers if layers is not None else frame_layers(bundle, k, geo, None, None)
    for p in bundle.partners(obj):
        ob = bundle.obs(p)
        own = np.asarray(ob.get('own', np.zeros(len(ob['pts']), np.uint8)))
        X = np.asarray(ob['pts'], np.float64)[own == 0]
        T = geo.T_a_rect @ bundle.poses[f'cam_T_{p}'][k].astype(np.float64)
        uv, z, ok = project_a(X @ T[:3, :3].T + T[:3, 3], geo)
        ui, vi = uv[ok, 0].astype(np.int64), uv[ok, 1].astype(np.int64)
        res['points_projected'] += int(ok.sum())
        res['points_inside'] += int(mask[vi, ui].sum())
        Pall[vi, ui] = True
        Pall |= L.fp[p]
    res['footprint_inside'] = int((mask & Pall).sum())
    if mask.any() and Pall.any():
        dt = cv2.distanceTransform((~Pall).astype(np.uint8), cv2.DIST_L2, 5)
        res['min_dist_px'] = round(float(dt[mask].min()), 2)
    res['pass'] = res['points_inside'] == 0 and res['footprint_inside'] == 0
    return res


def inpaint_partners(image, M, layers, obj, box):
    """Contact mode (SPEC section 4): the partners' pixels (dilated footprint) outside the target mask are replaced by
    local background (OpenCV Telea inpainting) inside BOX (x0, y0, x1, y1). Returns a copy of IMAGE."""
    import cv2
    x0, y0, x1, y1 = box
    out = image.copy()
    P = partner_union(layers, obj, dilate=True) & ~M
    sub = P[y0:y1, x0:x1].astype(np.uint8)
    if sub.any():
        out[y0:y1, x0:x1] = cv2.inpaint(np.ascontiguousarray(image[y0:y1, x0:x1]), sub, 5, cv2.INPAINT_TELEA)
    return out


def crop_box(mask, geo, pad=0.25, min_side=64):
    """Square box around MASK grown by PAD of its larger side on each side, clipped to the image."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return 0, 0, geo.W, geo.H
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    s = max(xs.max() - xs.min(), ys.max() - ys.min(), min_side) * (1 + 2 * pad)
    x0, y0 = int(max(cx - s / 2, 0)), int(max(cy - s / 2, 0))
    x1, y1 = int(min(cx + s / 2, geo.W)), int(min(cy + s / 2, geo.H))
    return x0, y0, x1, y1
