#!/usr/bin/env python3
"""MediaPipe Hands on the colour ego_cam_a video -> metric 3-D hand joints in the episode world frame.

World frame = rectified-left (ego_cam_c) camera at frame 0, OpenCV axes (x right, y down, z forward); the same
frame as perception's poses.npz (world_T_cam[k] maps rectified-left camera k -> world).

Per stereo frame k (b/c timeline; colour frame j = k + A_OFFSET):
  1. MediaPipe Hands (tracking mode, <= 2 hands) on cam_a RGB -> 21 image landmarks, 21 metric world landmarks
     (hand-centred shape), handedness label + score.
  2. Depth: the rectified-left depth map of frame k (FoundationStereo cache) is back-projected (stride 2),
     transformed rect -> c -> b -> a and projected with K_a / D_a into a half-resolution cam_a z-buffer (min z).
  3. Landmark rays from cv2.undistortPoints; robust near-surface depth per landmark (window, nearest band).
  4. The world-landmark shape is fitted (rotation, translation, scale in [SCALE_MIN, SCALE_MAX]) to reprojection
     residuals (all 21) + depth residuals (landmarks with depth), Huber loss, PnP and RANSAC-similarity inits.
  5. Joints cam_a -> rectified-left camera k -> world (world_T_cam[k]).
Then: handedness fix (image-x statistic, chirality as a tie-breaker), per-side temporal linking, outlier
rejection, linear interpolation of gaps <= MAX_GAP frames, Savitzky-Golay smoothing, hold elsewhere.

Inference only: no ground-truth pose is read. Rolling shutter of cam_a is ignored.
Run in /content/mpvenv (mediapipe 0.10.14, opencv-python-headless, numpy, scipy):
  /content/mpvenv/bin/python hands_mp.py --ep 12
Outputs in OUT (default /content/refs/epN): hands.npz, hands_overlay.jpg, hands_log.json.
"""
import argparse
import json
import os
import time

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot

SIDES = ('right', 'left')
PALM = [0, 5, 9, 13, 17]
MCPS = [5, 9, 13, 17]
TIPS = [4, 8, 12, 16, 20]
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12),
         (0, 13), (13, 14), (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17)]
T_START = time.time()


def log(*a):
    print(f'[{time.time() - T_START:7.1f}s]', *a, flush=True)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--ep', type=int, required=True)
    p.add_argument('--t3', default='/content/t3')
    p.add_argument('--depth', default=None, help='default /content/perc/epN/depths_fs0.5.npy')
    p.add_argument('--poses', default=None, help='default /content/perc2/epN/poses.npz (world_T_cam only)')
    p.add_argument('--video_a', default=None, help='default T3/v/epN_a.mp4')
    p.add_argument('--out', default=None, help='default /content/refs/epN')
    p.add_argument('--a_offset', type=int, default=1, help='stereo frame k pairs with cam_a frame k + A_OFFSET')
    p.add_argument('--api', choices=['legacy', 'tasks'], default='legacy')
    p.add_argument('--task_model', default='/content/ckpt/hand_landmarker.task')
    p.add_argument('--model_complexity', type=int, default=1)
    p.add_argument('--min_det', type=float, default=0.3)
    p.add_argument('--min_track', type=float, default=0.3)
    p.add_argument('--swap', choices=['auto', 'yes', 'no'], default='auto',
                   help='swap MediaPipe Left/Right labels (MediaPipe assumes mirrored input)')
    p.add_argument('--wl_mirror', choices=['auto', 'yes', 'no'], default='auto',
                   help='mirror MediaPipe world landmarks (z -> -z) if the fit says their handedness convention differs')
    # depth / z-buffer
    p.add_argument('--depth_stride', type=int, default=2)
    p.add_argument('--zbuf_scale', type=float, default=0.5)
    p.add_argument('--win', type=int, default=3, help='z-buffer sampling half-window (z-buffer pixels)')
    p.add_argument('--min_samples', type=int, default=4)
    p.add_argument('--near_band', type=float, default=0.03, help='keep samples within this of the 10th percentile')
    p.add_argument('--depth_gate', type=float, default=0.15, help='reject landmark depths this far from the hand median')
    p.add_argument('--joint_depth_offset', type=float, default=0.008, help='skin surface -> joint centre (m)')
    # fit
    p.add_argument('--sigma_px', type=float, default=4.0, help='landmark noise in full-resolution cam_a pixels')
    p.add_argument('--sigma_z', type=float, default=0.012)
    p.add_argument('--scale_min', type=float, default=0.85)
    p.add_argument('--scale_max', type=float, default=1.15)
    p.add_argument('--ransac_iters', type=int, default=150)
    p.add_argument('--ransac_thr', type=float, default=0.02)
    p.add_argument('--max_rms_px', type=float, default=20.0)
    # temporal
    p.add_argument('--recent', type=int, default=5)
    p.add_argument('--dup_dist', type=float, default=0.03)
    p.add_argument('--swap_margin', type=float, default=0.10)
    p.add_argument('--reassign_near', type=float, default=0.06)
    p.add_argument('--reassign_far', type=float, default=0.15)
    p.add_argument('--max_jump', type=float, default=0.25)
    # Default greedy after the 2026-10-20 A/B (palm steps > 4 cm on ep31/39/22/18/24: greedy best or tied; Viterbi only
    # fixed the ep12 hand-over). Viterbi with w_arm 0.8 broke ep31 (left-forearm cue near-random; 0.3 fixes it), and it
    # still follows long spurious tracks on ep18/22/39; a cheaper w_unused (0.15) plus a jump gate was worse.
    p.add_argument('--linker', choices=['viterbi', 'greedy'], default='greedy')
    p.add_argument('--w_label', type=float, default=0.5, help='viterbi: cost of overriding the MediaPipe label (x score)')
    p.add_argument('--w_arm', type=float, default=0.3, help='viterbi: cost of a forearm pointing to the other side')
    p.add_argument('--w_imgx', type=float, default=0.2, help='viterbi: cost of a wrist on the other image half')
    p.add_argument('--w_unused', type=float, default=1.0, help='viterbi: cost of leaving a detection unassigned')
    p.add_argument('--w_motion', type=float, default=1.0, help='viterbi: cost per 5 cm of palm step beyond the free band')
    p.add_argument('--motion_free', type=float, default=0.03, help='viterbi: palm step per frame that costs nothing (m)')
    p.add_argument('--outlier_dist', type=float, default=0.06)
    p.add_argument('--max_gap', type=int, default=15)
    p.add_argument('--smooth_win', type=int, default=7)
    p.add_argument('--overlay_frames', type=int, default=6)
    a = p.parse_args()
    n = a.ep
    a.depth = a.depth or f'/content/perc/ep{n}/depths_fs0.5.npy'
    a.poses = a.poses or f'/content/perc2/ep{n}/poses.npz'
    a.video_a = a.video_a or f'{a.t3}/v/ep{n}_a.mp4'
    a.out = a.out or f'/content/refs/ep{n}'
    return a


# ---------------------------------------------------------------- geometry (copied from perc.py + cam_a chain)
def geometry(calib_path):
    C = json.load(open(calib_path))
    cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
    E = np.array(sp['left_to_right'], float)
    R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()                     # X_b = R_lr X_c + T_lr
    SZ, RSZ = (1280, 800), (1600, 1000)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R_lr, T_lr.reshape(3, 1), alpha=0,
                                                newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
    KR = P1[:3, :3].copy()                                               # X_rect = R1 X_c
    Ka, Da = K_('ego_cam_a'), D_('ego_cam_a')
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float)  # X_b = R_ab X_a + t_ab (maps a -> b)
    R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    # rect -> a:  X_a = R_ab^T (R_lr R1^T X_rect + T_lr - t_ab)
    T_a_rect = np.eye(4)
    T_a_rect[:3, :3] = R_ab.T @ R_lr @ R1.T
    T_a_rect[:3, 3] = R_ab.T @ (T_lr - t_ab)
    return dict(KR=KR, RSZ=RSZ, Ka=Ka, Da=Da, T_a_rect=T_a_rect, T_rect_a=np.linalg.inv(T_a_rect),
                fa=0.5 * (Ka[0, 0] + Ka[1, 1]), baseline=float(-P2[0, 3] / P2[0, 0]), t_ab=t_ab.tolist(),
                T_lr=T_lr.tolist())


def zbuffer_a(depth_rect, g, size_a, stride, scale):
    """Rectified-left depth -> cam_a z-buffer (z along cam_a optical axis) at `scale` x resolution."""
    KR = g['KR']
    D = np.asarray(depth_rect[::stride, ::stride], np.float32)
    vv, uu = np.nonzero(D > 0)
    z = D[vv, uu].astype(np.float64)
    u, v = uu * stride, vv * stride
    X = np.stack([(u - KR[0, 2]) * z / KR[0, 0], (v - KR[1, 2]) * z / KR[1, 1], z], 1)
    Xa = X @ g['T_a_rect'][:3, :3].T + g['T_a_rect'][:3, 3]
    Xa = Xa[Xa[:, 2] > 0.05]
    Wz, Hz = int(round(size_a[0] * scale)), int(round(size_a[1] * scale))
    zb = np.full(Hz * Wz, np.inf, np.float32)
    if len(Xa):
        pts, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), g['Ka'], g['Da'])
        pts = pts.reshape(-1, 2) * scale
        iu, iv = np.round(pts[:, 0]).astype(np.int64), np.round(pts[:, 1]).astype(np.int64)
        ok = (iu >= 0) & (iu < Wz) & (iv >= 0) & (iv < Hz) & np.isfinite(pts).all(1)
        np.minimum.at(zb, iv[ok] * Wz + iu[ok], Xa[ok, 2].astype(np.float32))
    zb[~np.isfinite(zb)] = 0.0
    return zb.reshape(Hz, Wz)


def sample_zbuf(zb, uvz, a):
    H, W = zb.shape
    r = a.win
    z = np.zeros(len(uvz))
    ok = np.zeros(len(uvz), bool)
    for i, (u, v) in enumerate(uvz):
        if not (np.isfinite(u) and np.isfinite(v)):
            continue
        x, y = int(round(u)), int(round(v))
        if x < 0 or y < 0 or x >= W or y >= H:
            continue
        patch = zb[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
        vals = patch[patch > 0]
        if vals.size < a.min_samples:
            continue
        near = vals[vals <= np.percentile(vals, 10) + a.near_band]
        z[i] = float(np.median(near))
        ok[i] = True
    return z, ok


# ---------------------------------------------------------------- hand shape fit
def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    A, B = src - ms, dst - md
    U, S, Vt = np.linalg.svd(B.T @ A / len(src))
    d = np.sign(np.linalg.det(U @ Vt)) or 1.0
    Dm = np.diag([1.0, 1.0, d])
    R = U @ Dm @ Vt
    s = float((S * np.diag(Dm)).sum() / max((A ** 2).sum() / len(src), 1e-12))
    return s, R, md - s * R @ ms


def chirality(J):
    """> 0 suggests a right hand, < 0 a left hand (meaningful only when fingers are somewhat flexed)."""
    n = np.cross(J[5] - J[17], J[0] - J[9])
    nn = np.linalg.norm(n)
    if nn < 1e-9:
        return 0.0
    return float(-np.dot(J[TIPS].mean(0) - J[MCPS].mean(0), n / nn))


def fit_hand(uv, wl, zb, g, a, mirror=False):
    """uv (21,2) cam_a pixels, wl (21,3) MediaPipe world landmarks -> dict with X (21,3) in cam_a, or None."""
    W0 = wl - wl.mean(0)
    if mirror:
        W0 = W0 * np.array([1.0, 1.0, -1.0])
    xn = cv2.undistortPoints(uv.reshape(-1, 1, 2).astype(np.float64), g['Ka'], g['Da']).reshape(-1, 2)
    z, ok = sample_zbuf(zb, uv * a.zbuf_scale, a) if zb is not None else (np.zeros(21), np.zeros(21, bool))
    if ok.sum() >= 3:
        ok &= np.abs(z - np.median(z[ok])) < a.depth_gate
    zc = z + a.joint_depth_offset
    L = np.c_[xn * zc[:, None], zc]
    depth_ok = ok.sum() >= 3
    lo = np.r_[np.full(6, -np.inf), np.log(a.scale_min)]
    hi = np.r_[np.full(6, np.inf), np.log(a.scale_max)]
    if not depth_ok:                                 # no metric depth: keep MediaPipe's own hand size
        lo[6], hi[6] = -1e-6, 1e-6
    inits = []
    try:
        okp, rv, tv = cv2.solvePnP(W0.astype(np.float64), xn.astype(np.float64), np.eye(3), None,
                                   flags=cv2.SOLVEPNP_SQPNP)
        if okp and tv[2, 0] > 0.05:
            inits.append(np.r_[rv.ravel(), tv.ravel(), 0.0])
    except cv2.error:
        pass
    idx = np.flatnonzero(ok)
    if len(idx) >= 4:
        rng = np.random.default_rng(0)
        best = None
        for _ in range(a.ransac_iters):
            smp = rng.choice(idx, 4, replace=False)
            s, R, t = umeyama(W0[smp], L[smp])
            s = float(np.clip(s, a.scale_min, a.scale_max))
            t = L[smp].mean(0) - s * R @ W0[smp].mean(0)
            err = np.linalg.norm(s * W0[idx] @ R.T + t - L[idx], axis=1)
            inl = idx[err < a.ransac_thr]
            if best is None or len(inl) > len(best):
                best = inl
        if best is not None and len(best) >= 4:
            s, R, t = umeyama(W0[best], L[best])
            s = float(np.clip(s, a.scale_min, a.scale_max))
            t = L[best].mean(0) - s * R @ W0[best].mean(0)
            inits.append(np.r_[Rot.from_matrix(R).as_rotvec(), t, np.log(s)])
    if not inits:
        return None
    k_px = g['fa'] / a.sigma_px

    def residual(p):
        R = Rot.from_rotvec(p[:3]).as_matrix()
        X = np.exp(p[6]) * W0 @ R.T + p[3:6]
        zz = np.maximum(X[:, 2], 1e-3)
        r1 = (X[:, :2] / zz[:, None] - xn).ravel() * k_px
        r2 = (X[ok, 2] - zc[ok]) / a.sigma_z
        return np.r_[r1, r2]

    sol = None
    for p0 in inits:
        p0 = p0.copy()
        p0[6] = np.clip(p0[6], lo[6] + 1e-9, hi[6] - 1e-9)
        try:
            s_ = least_squares(residual, p0, bounds=(lo, hi), loss='huber', f_scale=1.0, max_nfev=300)
        except ValueError:
            continue
        if sol is None or s_.cost < sol.cost:
            sol = s_
    if sol is None:
        return None
    p = sol.x
    X = np.exp(p[6]) * W0 @ Rot.from_rotvec(p[:3]).as_matrix().T + p[3:6]
    r = residual(p)
    r1 = r[:42] / k_px * g['fa']                     # back to pixels (approx.)
    r2 = r[42:]
    return dict(X=X, rms_px=float(np.sqrt(np.mean(r1 ** 2))), n_depth=int(ok.sum()),
                n_depth_inl=int((np.abs(r2) < 2.5).sum()), scale=float(np.exp(p[6])), cost=float(sol.cost),
                depth_ok=bool(depth_ok), dz_med=float(np.median(np.abs(r2)) * a.sigma_z) if len(r2) else float('nan'))


# ---------------------------------------------------------------- MediaPipe
class Detector:
    def __init__(self, a):
        import mediapipe as mp
        self.mp, self.api = mp, a.api
        if a.api == 'legacy':
            self.h = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2,
                                              model_complexity=a.model_complexity,
                                              min_detection_confidence=a.min_det, min_tracking_confidence=a.min_track)
        else:
            from mediapipe.tasks import python as mpt
            from mediapipe.tasks.python import vision
            opts = vision.HandLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=a.task_model),
                                                running_mode=vision.RunningMode.VIDEO, num_hands=2,
                                                min_hand_detection_confidence=a.min_det,
                                                min_hand_presence_confidence=a.min_det,
                                                min_tracking_confidence=a.min_track)
            self.h = vision.HandLandmarker.create_from_options(opts)

    def __call__(self, rgb, t_ms):
        H, W = rgb.shape[:2]
        out = []
        if self.api == 'legacy':
            r = self.h.process(rgb)
            if not r.multi_hand_landmarks or not r.multi_hand_world_landmarks:
                return out
            for lm, wl, hd in zip(r.multi_hand_landmarks, r.multi_hand_world_landmarks, r.multi_handedness):
                c = hd.classification[0]
                out.append(dict(label=c.label, score=float(c.score),
                                uv=np.array([[q.x * W, q.y * H] for q in lm.landmark], float),
                                wl=np.array([[q.x, q.y, q.z] for q in wl.landmark], float)))
        else:
            img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
            r = self.h.detect_for_video(img, int(t_ms))
            for lm, wl, hd in zip(r.hand_landmarks, r.hand_world_landmarks, r.handedness):
                c = hd[0]
                out.append(dict(label=c.category_name, score=float(c.score),
                                uv=np.array([[q.x * W, q.y * H] for q in lm], float),
                                wl=np.array([[q.x, q.y, q.z] for q in wl], float)))
        return [d for d in out if d['label'] in ('Left', 'Right') and np.isfinite(d['wl']).all()]


# ---------------------------------------------------------------- temporal processing
def palm_c(J):
    return J[PALM].mean(0)


def runs(mask):
    """Half-open [s, e) runs where mask is True."""
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def link_tracks(cands, T, a):
    out = {s: [None] * T for s in SIDES}
    last = {s: (None, -10 ** 9) for s in SIDES}
    st = dict(dup=0, same_label=0, swapped_pairs=0, reassigned=0, dropped_jump=0)
    for k in range(T):
        ds = sorted(cands[k], key=lambda d: -d['score'])
        if len(ds) == 2 and np.linalg.norm(palm_c(ds[0]['J']) - palm_c(ds[1]['J'])) < a.dup_dist:
            ds = ds[:1]
            st['dup'] += 1
        recent = {s: last[s][0] is not None and k - last[s][1] <= a.recent for s in SIDES}

        def dist(d, s):
            return float(np.linalg.norm(palm_c(d['J']) - last[s][0])) if recent[s] else float('nan')

        assign = {}
        if len(ds) == 2:
            d0, d1 = ds
            if d0['side'] == d1['side']:
                st['same_label'] += 1
                if recent['right'] and recent['left']:
                    c01 = dist(d0, 'right') + dist(d1, 'left')
                    c10 = dist(d0, 'left') + dist(d1, 'right')
                    assign = {'right': d0, 'left': d1} if c01 <= c10 else {'right': d1, 'left': d0}
                else:
                    r_, l_ = (d0, d1) if d0['u_wrist'] >= d1['u_wrist'] else (d1, d0)
                    assign = {'right': r_, 'left': l_}
            else:
                assign = {d0['side']: d0, d1['side']: d1}
                if recent['right'] and recent['left']:
                    keep = dist(assign['right'], 'right') + dist(assign['left'], 'left')
                    swap = dist(assign['right'], 'left') + dist(assign['left'], 'right')
                    if swap + a.swap_margin < keep:
                        assign = {'right': assign['left'], 'left': assign['right']}
                        st['swapped_pairs'] += 1
        elif len(ds) == 1:
            d = ds[0]
            s = d['side']
            o = 'left' if s == 'right' else 'right'
            d_own, d_oth = dist(d, s), dist(d, o)
            if recent[o] and d_oth < a.reassign_near and (not recent[s] or d_own > a.reassign_far):
                s = o
                st['reassigned'] += 1
            assign = {s: d}
        for s, d in assign.items():
            if recent[s] and k - last[s][1] <= 3 and np.linalg.norm(palm_c(d['J']) - last[s][0]) > a.max_jump:
                st['dropped_jump'] += 1
                continue
            out[s][k] = d
            last[s] = (palm_c(d['J']), k)
    return out, st


def forearm_x(d):
    """Image-x direction from the knuckles to the wrist, in [-1, 1]. Egocentric views: the right forearm leaves the
    hand toward image-right (> 0), the left one toward image-left (< 0), even when the hands cross at an object."""
    f = d['uv'][0] - d['uv'][[5, 9, 13, 17]].mean(0)
    return float(f[0] / (np.linalg.norm(f) + 1e-6))


def link_viterbi(cands, T, a, img_w):
    """Whole-clip identity assignment (2026-10-20, box 1 ep12: the greedy linker put the right-hand track on the
    left hand during a hand-over, frames 61-83). Per frame, options = which detection is right / left / unused.
    Costs: MediaPipe label disagreement (x its score), forearm direction, image side (weak), unused detection, and
    palm motion beyond a free band between consecutive frames. Dynamic programming over all frames."""
    sg = {'right': 1.0, 'left': -1.0}

    def emit(d, s):
        c = a.w_label * d['score'] * (d['side'] != s)
        c += a.w_arm * max(0.0, -sg[s] * forearm_x(d))
        c += a.w_imgx * max(0.0, -sg[s] * (d['u_wrist'] - img_w / 2) / (img_w / 2))
        return c

    opts, ocost = [], []
    for k in range(T):
        ds = sorted(cands[k], key=lambda d: -d['score'])
        if len(ds) == 2 and np.linalg.norm(palm_c(ds[0]['J']) - palm_c(ds[1]['J'])) < a.dup_dist:
            ds = ds[:1]
        cands[k] = ds
        n = len(ds)
        o = [{}] + [{s: i} for i in range(n) for s in SIDES] + \
            [{'right': i, 'left': j} for i in range(n) for j in range(n) if i != j]
        opts.append(o)
        ocost.append([sum(emit(ds[i], s) for s, i in m.items()) + a.w_unused * (n - len(m)) for m in o])

    def trans(k, m0, m1):
        c = 0.0
        for s in SIDES:
            if s in m0 and s in m1:
                step = np.linalg.norm(palm_c(cands[k - 1][m0[s]]['J']) - palm_c(cands[k][m1[s]]['J']))
                c += a.w_motion * max(0.0, step - a.motion_free) / 0.05
        return c

    acc, back = [np.array(ocost[0])], []
    for k in range(1, T):
        cur, bk = np.empty(len(opts[k])), np.empty(len(opts[k]), int)
        for j, m1 in enumerate(opts[k]):
            tot = [acc[-1][i] + trans(k, m0, m1) for i, m0 in enumerate(opts[k - 1])]
            bk[j] = int(np.argmin(tot))
            cur[j] = tot[bk[j]] + ocost[k][j]
        acc.append(cur)
        back.append(bk)
    path = [int(np.argmin(acc[-1]))]
    for k in range(T - 1, 0, -1):
        path.append(int(back[k - 1][path[-1]]))
    path = path[::-1]
    out = {s: [None] * T for s in SIDES}
    st = dict(label_overridden=0, unused=0, arm_disagrees_label=0)
    for k in range(T):
        m = opts[k][path[k]]
        st['unused'] += len(cands[k]) - len(m)
        for s, i in m.items():
            d = cands[k][i]
            out[s][k] = d
            st['label_overridden'] += d['side'] != s
            st['arm_disagrees_label'] += (forearm_x(d) > 0) != (d['side'] == 'right')
    return out, st


def postprocess(seq, T, a):
    J = np.zeros((T, 21, 3))
    meas = np.zeros(T, bool)
    for k, d in enumerate(seq):
        if d is not None:
            J[k], meas[k] = d['J'], True
    P = J[:, PALM].mean(1)
    idx = np.flatnonzero(meas)
    bad = []
    for i, k in enumerate(idx):
        nb = idx[max(0, i - 4):i + 5]
        nb = nb[nb != k]
        if len(nb) >= 3 and np.linalg.norm(P[k] - np.median(P[nb], 0)) > a.outlier_dist:
            bad.append(k)
    meas[bad] = False
    valid = meas.copy()
    filled = np.zeros(T, bool)
    idx = np.flatnonzero(meas)
    for i0, i1 in zip(idx[:-1], idx[1:]):
        if 0 < i1 - i0 - 1 <= a.max_gap:
            w = (np.arange(i0 + 1, i1) - i0) / (i1 - i0)
            J[i0 + 1:i1] = (1 - w)[:, None, None] * J[i0] + w[:, None, None] * J[i1]
            valid[i0 + 1:i1] = True
            filled[i0 + 1:i1] = True
    for s, e in runs(valid):
        n = e - s
        w = min(a.smooth_win, n if n % 2 else n - 1)
        if w >= 5:
            J[s:e] = savgol_filter(J[s:e], w, 2, axis=0)
    if valid.any():
        vi = np.flatnonzero(valid)
        for k in np.flatnonzero(~valid):
            j = np.searchsorted(vi, k)
            J[k] = J[vi[j - 1]] if j > 0 else J[vi[0]]   # hold previous valid (leading: first valid)
    return J, valid, meas, filled, len(bad)


# ---------------------------------------------------------------- main
def main():
    a = parse_args()
    os.makedirs(a.out, exist_ok=True)
    g = geometry(f'{a.t3}/calib.json')
    W_C = np.load(a.poses)['world_T_cam'].astype(np.float64)        # (T,4,4) rect-left cam k -> world
    T = len(W_C)
    depths = np.load(a.depth, mmap_mode='r')
    if depths.shape[0] < T or tuple(depths.shape[1:]) != (g['RSZ'][1], g['RSZ'][0]):
        raise SystemExit(f'depth cache shape {depths.shape} does not cover T={T} frames of {g["RSZ"]}')
    cap = cv2.VideoCapture(a.video_a)
    Wa, Ha = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_a = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_a = cap.get(cv2.CAP_PROP_FPS) or 20.0
    log(f'ep{a.ep}: T={T} stereo frames, cam_a {Wa}x{Ha} frames={n_a} fps={fps_a:.2f} offset={a.a_offset}',
        f'baseline={g["baseline"]:.4f} t_ab={np.round(g["t_ab"], 4).tolist()}')
    if n_a and n_a < T + a.a_offset:
        log(f'WARNING: cam_a has {n_a} frames < T + offset = {T + a.a_offset}; trailing frames get no detection')
    size_a = (Wa, Ha)

    # ---- pass 1: MediaPipe over cam_a (sequential, tracking mode)
    det = Detector(a)
    dets = [[] for _ in range(T)]
    j = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        k = j - a.a_offset
        if k >= T:
            break
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        ds = det(rgb, j * 1000.0 / fps_a)
        if 0 <= k < T:
            for d in ds:
                d['u_wrist'] = float(d['uv'][0, 0])
                d['chir'] = chirality(d['wl'])
            dets[k] = ds
        j += 1
    cap.release()
    n_det = np.array([len(d) for d in dets])
    log(f'detections: frames with >=1 hand {int((n_det >= 1).sum())}/{T}, with 2 hands {int((n_det == 2).sum())}')

    # ---- handedness convention
    pairs = [ds for ds in dets if len(ds) == 2 and {d['label'] for d in ds} == {'Left', 'Right'}]
    votes = [next(d for d in ds if d['label'] == 'Right')['u_wrist'] > next(d for d in ds if d['label'] == 'Left')['u_wrist']
             for ds in pairs]
    frac_raw_right_on_right = float(np.mean(votes)) if votes else float('nan')
    chir_raw = {lab: [d['chir'] for ds in dets for d in ds if d['label'] == lab] for lab in ('Right', 'Left')}
    chir_med = {lab: float(np.median(v)) if v else float('nan') for lab, v in chir_raw.items()}
    if a.swap == 'auto':
        if len(votes) >= 10:
            swap, why = frac_raw_right_on_right < 0.5, f'image-x over {len(votes)} two-hand frames'
        elif len(chir_raw['Right']) >= 20 and len(chir_raw['Left']) >= 20 and abs(chir_med['Right'] - chir_med['Left']) > 0.01:
            swap, why = chir_med['Right'] < chir_med['Left'], 'chirality medians'
        else:
            swap, why = True, 'default (MediaPipe assumes mirrored input)'
    else:
        swap, why = a.swap == 'yes', 'forced'
    log(f'handedness: raw Right on image-right in {frac_raw_right_on_right:.2f} of {len(votes)} pairs;',
        f'chirality median raw Right {chir_med["Right"]:+.4f} raw Left {chir_med["Left"]:+.4f} -> swap={swap} ({why})')
    for ds in dets:
        for d in ds:
            phys = {'Right': 'right', 'Left': 'left'}[d['label']]
            d['side'] = ('left' if phys == 'right' else 'right') if swap else phys

    # ---- world-landmark convention check (fit with and without z-mirror on a sample)
    zcache = {}

    def zb_of(k):
        if k not in zcache:
            if len(zcache) > 8:
                zcache.clear()
            zcache[k] = zbuffer_a(depths[k], g, size_a, a.depth_stride, a.zbuf_scale)
        return zcache[k]

    mirror = a.wl_mirror == 'yes'
    ratios = []
    if a.wl_mirror == 'auto':
        ks = [k for k in range(T) if dets[k]]
        for k in ks[::max(1, len(ks) // 30)][:30]:
            zb = zb_of(k)
            for d in dets[k][:1]:
                f0, f1 = fit_hand(d['uv'], d['wl'], zb, g, a, False), fit_hand(d['uv'], d['wl'], zb, g, a, True)
                if f0 and f1 and f0['n_depth'] >= 8:
                    ratios.append(f1['cost'] / max(f0['cost'], 1e-9))
        if len(ratios) >= 8 and np.median(ratios) < 0.7:
            mirror = True
        log(f'world-landmark mirror check: median cost(mirrored)/cost(as-is) = '
            f'{np.median(ratios) if ratios else float("nan"):.3f} over {len(ratios)} fits -> mirror={mirror}')
        if mirror:
            log('WARNING: MediaPipe world landmarks fit better mirrored; chirality of the output was flipped. Inspect the overlay.')
            for ds in dets:
                for d in ds:
                    d['chir'] = chirality(d['wl'] * np.array([1.0, 1.0, -1.0]))

    # ---- pass 2: lift every detection
    cands = [[] for _ in range(T)]
    n_fit = n_rej = 0
    for k in range(T):
        if not dets[k]:
            continue
        zb = zb_of(k)
        for d in dets[k]:
            f = fit_hand(d['uv'], d['wl'], zb, g, a, mirror)
            n_fit += 1
            if f is None or f['rms_px'] > a.max_rms_px or not (0.10 < f['X'][0, 2] < 1.5):
                n_rej += 1
                continue
            Xr = f['X'] @ g['T_rect_a'][:3, :3].T + g['T_rect_a'][:3, 3]
            Jw = Xr @ W_C[k][:3, :3].T + W_C[k][:3, 3]
            cands[k].append(dict(d, J=Jw, fit=f))
    log(f'lifted {n_fit - n_rej}/{n_fit} detections (rejected {n_rej})')

    seq, st = link_viterbi(cands, T, a, Wa) if a.linker == 'viterbi' else link_tracks(cands, T, a)
    log(f'linking ({a.linker}):', st)
    res = {}
    for s in SIDES:
        J, valid, meas, filled, n_out = postprocess(seq[s], T, a)
        diag = {k: np.full(T, np.nan) for k in ('rms_px', 'n_depth', 'n_depth_inl', 'scale', 'chir', 'score', 'dz_med')}
        uv = np.full((T, 21, 2), np.nan)
        depth_ok = np.zeros(T, bool)
        for k, d in enumerate(seq[s]):
            if d is None:
                continue
            f = d['fit']
            for key in ('rms_px', 'n_depth', 'n_depth_inl', 'scale', 'dz_med'):
                diag[key][k] = f[key]
            diag['chir'][k], diag['score'][k] = d['chir'], d['score']
            uv[k] = d['uv']
            depth_ok[k] = f['depth_ok']
        res[s] = dict(J=J, valid=valid, meas=meas, filled=filled, n_out=n_out, diag=diag, uv=uv, depth_ok=depth_ok)
        hl = np.linalg.norm(J[valid][:, 12] - J[valid][:, 0], axis=1) if valid.any() else np.array([np.nan])
        log(f'{s:5s}: measured {int(meas.sum())}/{T}, valid {int(valid.sum())} (filled {int(filled.sum())}),',
            f'outliers {n_out}, depth-ok {int(depth_ok.sum())}, median rms {np.nanmedian(diag["rms_px"]):.1f}px,',
            f'scale {np.nanmedian(diag["scale"]):.3f}, wrist->middle-tip {np.nanmedian(hl) * 100:.1f}cm,',
            f'chirality median {np.nanmedian(diag["chir"]):+.4f} ({"+" if s == "right" else "-"} expected),',
            f'mean wrist u {np.nanmean(uv[:, 0, 0]):.0f}px')
    ur, ul = res['right']['uv'][:, 0, 0], res['left']['uv'][:, 0, 0]
    both = np.isfinite(ur) & np.isfinite(ul)
    frac_rr = float(np.mean(ur[both] > ul[both])) if both.any() else float('nan')
    log(f'sanity: final right wrist right of left wrist in {frac_rr:.2f} of {int(both.sum())} two-hand frames (expect > 0.5)')

    out = dict(world_frame='rectified-left camera at frame 0 (OpenCV axes)', T=T, a_offset=a.a_offset,
               swap=bool(swap), wl_mirror=bool(mirror), n_det=n_det, Ka=g['Ka'], Da=g['Da'],
               T_rect_a=g['T_rect_a'], KR=g['KR'], size_a=np.array(size_a))
    for s in SIDES:
        r = res[s]
        out[f'joints_{s}'] = r['J'].astype(np.float32)
        out[f'valid_{s}'] = r['valid']
        out[f'measured_{s}'] = r['meas']
        out[f'filled_{s}'] = r['filled']
        out[f'depth_ok_{s}'] = r['depth_ok']
        out[f'uv_a_{s}'] = r['uv'].astype(np.float32)
        for key, v in r['diag'].items():
            out[f'{key}_{s}'] = v.astype(np.float32)
    np.savez_compressed(f'{a.out}/hands.npz', **out)
    summary = dict(ep=a.ep, T=T, frames_with_hand=int((n_det >= 1).sum()), frames_two_hands=int((n_det == 2).sum()),
                   swap=bool(swap), swap_reason=why, frac_raw_right_on_right=frac_raw_right_on_right,
                   n_pairs=len(votes), chir_med_raw=chir_med, wl_mirror=bool(mirror),
                   mirror_ratio_median=float(np.median(ratios)) if ratios else None,
                   final_right_right_of_left=frac_rr, linking=st, fits=n_fit, rejected=n_rej,
                   sides={s: dict(measured=int(res[s]['meas'].sum()), valid=int(res[s]['valid'].sum()),
                                  filled=int(res[s]['filled'].sum()), depth_ok=int(res[s]['depth_ok'].sum()),
                                  rms_px_median=float(np.nanmedian(res[s]['diag']['rms_px'])) if res[s]['meas'].any() else None,
                                  scale_median=float(np.nanmedian(res[s]['diag']['scale'])) if res[s]['meas'].any() else None)
                          for s in SIDES})
    json.dump(summary, open(f'{a.out}/hands_log.json', 'w'), indent=1)

    # ---- overlay: landmarks (green right / orange left), refit joints reprojected (red), depth z-buffer tint
    meas_any = res['right']['meas'] | res['left']['meas']
    ks = np.flatnonzero(meas_any)
    if len(ks):
        sel = sorted(set(ks[np.linspace(0, len(ks) - 1, min(a.overlay_frames, len(ks))).astype(int)].tolist()))
        want = {k + a.a_offset: k for k in sel}
        cap = cv2.VideoCapture(a.video_a)
        tiles, j = [], 0
        while want:
            ok, fr = cap.read()
            if not ok:
                break
            if j in want:
                k = want.pop(j)
                img = fr.copy()
                zb = zb_of(k)
                zb_up = cv2.resize(zb, (Wa, Ha), interpolation=cv2.INTER_NEAREST)
                m = zb_up > 0
                if m.any():
                    zn = np.clip((zb_up - 0.2) / 0.8, 0, 1)
                    heat = cv2.applyColorMap((255 * (1 - zn)).astype(np.uint8), cv2.COLORMAP_JET)
                    img[m] = (0.65 * img[m] + 0.35 * heat[m]).astype(np.uint8)
                for s, col in (('right', (0, 220, 0)), ('left', (0, 140, 255))):
                    r = res[s]
                    if r['meas'][k]:
                        uv = r['uv'][k]
                        for b0, b1 in BONES:
                            cv2.line(img, tuple(np.int32(uv[b0])), tuple(np.int32(uv[b1])), col, 3)
                    if r['valid'][k]:
                        Xr = (r['J'][k] - W_C[k][:3, 3]) @ W_C[k][:3, :3]          # world -> rect k
                        Xa = Xr @ g['T_a_rect'][:3, :3].T + g['T_a_rect'][:3, 3]
                        if (Xa[:, 2] > 0.05).all():
                            pr, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), g['Ka'], g['Da'])
                            for q in pr.reshape(-1, 2):
                                if np.isfinite(q).all():
                                    cv2.circle(img, tuple(np.int32(q)), 6, (0, 0, 255), -1)
                    txt = f'{s}: rms {r["diag"]["rms_px"][k]:.1f}px nd {r["diag"]["n_depth"][k]:.0f}' if r['meas'][k] else f'{s}: -'
                    cv2.putText(img, txt, (20, 60 if s == 'right' else 120), cv2.FONT_HERSHEY_SIMPLEX, 1.6, col, 4)
                cv2.putText(img, f'k={k}', (20, Ha - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 4)
                tiles.append(cv2.resize(img, (Wa // 3, Ha // 3)))
            j += 1
        cap.release()
        if tiles:
            while len(tiles) % 3:
                tiles.append(np.zeros_like(tiles[0]))
            grid = np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)])
            cv2.imwrite(f'{a.out}/hands_overlay.jpg', grid)
    log('saved', f'{a.out}/hands.npz', f'{a.out}/hands_overlay.jpg', f'{a.out}/hands_log.json')


if __name__ == '__main__':
    main()
