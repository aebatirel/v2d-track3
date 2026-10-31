"""T5, first stage (tracker-fix PLAN.md §3 T5, §4 item 3; 31 Oct 2026): a robust camera (VO) for one public episode,
CPU only, GT-free. Re-runs only the camera; the object tracks (cam_T_obj) are kept and recomposed by t5_score.py.

Camera variants written (world = perc2's rectified-left camera c at frame 0, OpenCV axes, metres, as perc2):
  base       perc2's stored chain (poses.npz world_T_cam), unchanged (control).
  plane      F3 alone: perc2's stored chain + the table-plane constraint at its own keyframes (vo.json). The chain
             W[t] = W[kf] inv(M_t) is re-based exactly: at keyframe kf_j the keyframe's own support plane (camera frame,
             from its own stereo depth) is mapped to world with the corrected chain so far, and the minimal world
             correction that puts it onto the frame-0 plane (rotation of the normal about the centroid of the table
             inliers, then a shift along the normal) is composed onto every later frame. 3 DoF: height and tilt.
  rvo        F1: keyframe-map VO in perc2's rectified frames: SIFT on rectified c with our tracked objects (our meshes
             at our cam_T_obj, filled triangles, dilated DIL_OBJ px) and our hands (hull of the 21 hands_refined joints,
             mapped to camera t through the camera they were built with, extended to the bottom image edge for the
             forearm, dilated DIL_HAND px) masked out. A keyframe's map = its masked keypoints with metric 3-D from the
             rectified c/b pair: --map sgbm (default) samples our SGBM depth at the keypoint; --map sift is vo17's sparse
             stereo (row-constrained SIFT c-b matches, Z = f B / d). Each frame is matched first to the EARLIEST keyframe
             (frame 0 first) whose map gives >= KF_OK PnP inliers (SQPnP RANSAC 1.5 px + LM); a new keyframe is opened,
             with the best candidate's pose, only when none does (the 13 Oct pipeline/perc.py rule, here with stereo maps).
             Ablations: --kf_mode latest (perc2's chain: match only the latest keyframe, re-base on the previous frame
             when it gives < KF_OK); --no_mask 1 (no object or hand masks).
  rvo_plane  F1 + F3: rvo with the table-plane constraint applied to each new keyframe's pose before its map is built.
Plane fit (same SGBM depth for frame 0 and keyframes, objects and hands masked, step-4 samples 0.2-1.2 m): frame 0 by
det_rules.table_plane's RANSAC (normal within 65 deg of camera up, 6 mm) + 2 least-squares refits; a keyframe from the
samples within PL_BAND (3 cm) of the frame-0 plane seen through its current pose estimate, then least-squares refits on
shrinking bands (1 cm, 6 mm). (First version, not used: det_rules RANSAC on the masked keyframe depth found other planes,
12-42 deg off, once the boards and hands covered most of the small table, f40-61.) A keyframe correction is skipped
(logged) when the fit has < --pl_min samples, rms > PL_MAXRMS mm, or would tilt > PL_MAXDEG or shift > PL_MAXCM.
Inputs (inference outputs and public calibration only; every path passes refine.assert_inference_input): b/c videos,
the public camera calibration, our poses.npz, vo.json, hands_refined.npz, our meshes. No mocap, no scans, no
observation.objects.
Usage: python -I vo_t5.py --b B.mp4 --c C.mp4 --calib CAL.json --poses poses.npz --vo vo.json --hands hands_refined.npz
                          --meshes DIR --out OUTDIR [--variants base,plane,rvo,rvo_plane] [--kf_ok 120] [--map sgbm|sift]
                          [--pl_min 300] [--kf_mode earliest|latest] [--no_mask 0|1]
Outputs: OUTDIR/W_<variant>.npy (N,4,4) world_T_cam; OUTDIR/vo_t5.json (keyframes, inliers, planes, corrections, params).
"""
import argparse, hashlib, json, os, sys, time

import cv2
import numpy as np
import trimesh

REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/pipeline')
import det_rules  # noqa: E402
from refine import assert_inference_input  # noqa: E402

T0 = time.time()
DIL_OBJ, DIL_HAND = 15, 31
RATIO_ST, RATIO_KF, ROW_TOL = 0.8, 0.75, 1.5
ZMIN, ZMAX = 0.15, 3.0
PNP_PX, PNP_MIN = 1.5, 30
PL_MAXDEG, PL_MAXCM, PL_BAND, PL_MAXRMS = 5.0, 5.0, 0.03, 4.0


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


def rect_setup(calib):  # identical to pipeline/perc2.py
    C = json.load(open(calib)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
    E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
    SZ, RSZ = (1280, 800), (1600, 1000)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R, T, alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
    MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
    MB = cv2.initUndistortRectifyMap(Kb, db, R2, P2, RSZ, cv2.CV_32FC1)
    return MC, MB, P1[0, 0], -P2[0, 3] / P2[0, 0], P1[:3, :3].copy()


def frames(path, M):
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), M[0], M[1], cv2.INTER_LINEAR))
    return out


def proj(Y, K):
    z = Y[:, 2]
    return np.stack([Y[:, 0] / z * K[0, 0] + K[0, 2], Y[:, 1] / z * K[1, 1] + K[1, 2]], 1), z


def obj_mask(meshes, camT, t, K, shape):
    m = np.zeros(shape, np.uint8)
    for n, (V, F) in meshes.items():
        Y = V @ camT[n][t][:3, :3].T + camT[n][t][:3, 3]
        uv, z = proj(Y, K)
        f = F[(z[F] > 0.05).all(1)]
        if len(f):
            cv2.fillPoly(m, list(np.round(uv[f]).astype(np.int32).clip(-10000, 10000)), 1)
    return cv2.dilate(m, np.ones((2 * DIL_OBJ + 1, 2 * DIL_OBJ + 1), np.uint8))


def hand_mask(Hz, t, Wh, K, shape):
    m = np.zeros(shape, np.uint8)
    for s in ('left', 'right'):
        if f'joints_{s}' not in Hz.files or not bool(Hz[f'valid_{s}'][t]):
            continue
        J = Hz[f'joints_{s}'][t].astype(float)
        if not np.isfinite(J).all():
            continue
        Y = (J - Wh[t][:3, 3]) @ Wh[t][:3, :3]              # hands world -> camera t (the camera they were built with)
        uv, z = proj(Y, K)
        if (z <= 0.05).any():
            continue
        wr = uv[0]
        P = np.vstack([uv, [[wr[0] - 80, shape[0] - 1], [wr[0] + 80, shape[0] - 1]]]).clip(-10000, 10000).astype(np.int32)
        cv2.fillConvexPoly(m, cv2.convexHull(P), 1)
    return cv2.dilate(m, np.ones((2 * DIL_HAND + 1, 2 * DIL_HAND + 1), np.uint8))


def plane_fit(D, K, keep, prior=None):
    """Table plane (n, c), n . x + c = 0, n up (camera y down), from depth D on pixels KEEP (step-4 samples, 0.2-1.2 m).
    No prior (frame 0): det_rules.table_plane's RANSAC, then least-squares refits on its 6 mm band. With a prior plane
    (a keyframe: the frame-0 plane seen through the keyframe's current pose estimate): the samples within PL_BAND of the
    prior, then least-squares refits on shrinking bands (PL_BAND, 1 cm, 6 mm, 6 mm); no RANSAC, so no other plane."""
    Dm = np.where(keep, D, 0).astype(np.float32)
    H, W_ = Dm.shape; vv, uu = np.mgrid[0:H:4, 0:W_:4]; d = Dm[vv, uu]
    ok = (d > 0.2) & (d < 1.2)
    P = np.stack([(uu[ok] - K[0, 2]) * d[ok] / K[0, 0], (vv[ok] - K[1, 2]) * d[ok] / K[1, 1], d[ok]], 1)
    if prior is None:
        pl = det_rules.table_plane(Dm, K)
        if pl is None:
            return None
        n, c = np.asarray(pl[0], float), float(pl[1]); bands = (0.006, 0.006)
    else:
        n, c = np.asarray(prior[0], float), float(prior[1]); bands = (PL_BAND, 0.01, 0.006, 0.006)
    for b in bands:
        inl = np.abs(P @ n + c) < b
        if inl.sum() < 50:
            return None
        Q = P[inl]; mu = Q.mean(0)
        n = np.linalg.svd(Q - mu, full_matrices=False)[2][-1]
        if n[1] > 0:
            n = -n
        c = -float(n @ mu)
    inl = np.abs(P @ n + c) < 0.006
    return dict(n=n, c=c, n_inl=int(inl.sum()), centroid=P[inl].mean(0), rms_mm=float(np.sqrt(np.mean((P[inl] @ n + c) ** 2)) * 1000))


def rot_between(a, b):
    v = np.cross(a, b); s = np.linalg.norm(v); cth = float(np.clip(a @ b, -1, 1))
    if s < 1e-12:
        return np.eye(3)
    k = v / s; Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    th = np.arctan2(s, cth)
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def plane_correction(pc, Wk, p0):
    """World transform C putting keyframe plane pc (camera frame, pose Wk) onto the frame-0 plane p0 (world)."""
    R, t = Wk[:3, :3], Wk[:3, 3]
    nw = R @ pc['n']; pw = R @ pc['centroid'] + t                 # plane normal and table-inlier centroid in world
    Rc = rot_between(nw, p0['n'])
    tau = -p0['c'] - p0['n'] @ pw
    C = np.eye(4); C[:3, :3] = Rc; C[:3, 3] = pw - Rc @ pw + tau * p0['n']
    ang = float(np.degrees(np.arccos(np.clip(nw @ p0['n'], -1, 1))))
    return C, ang, float(tau * 100)


def main():
    ap = argparse.ArgumentParser()
    for k in ('b', 'c', 'calib', 'poses', 'vo', 'hands', 'meshes', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--kf_ok', type=int, default=120)
    ap.add_argument('--pl_min', type=int, default=300)
    ap.add_argument('--map', default='sgbm', choices=('sgbm', 'sift'))
    ap.add_argument('--kf_mode', default='earliest', choices=('earliest', 'latest'))
    ap.add_argument('--no_mask', type=int, default=0)
    ap.add_argument('--variants', default='base,plane,rvo,rvo_plane')
    a = ap.parse_args()
    for f in (a.b, a.c, a.calib, a.poses, a.vo, a.hands, a.meshes):
        assert_inference_input(f)
    os.makedirs(a.out, exist_ok=True)
    variants = a.variants.split(',')
    MC, MB, FR, BASE, KR = rect_setup(a.calib)
    log('rectified focal', round(FR, 2), 'baseline', round(BASE, 5))
    rc, rb = frames(a.c, MC), frames(a.b, MB)
    P = np.load(a.poses); W0 = P['world_T_cam'].astype(float)
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    camT = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    N = min(len(rc), len(rb), len(W0)); shape = rc[0].shape
    log('frames c/b/poses', len(rc), len(rb), len(W0), 'objects', names)
    Hz = np.load(a.hands)
    meshes = {}
    for n in names:
        m = trimesh.load(f'{a.meshes}/{n}.glb', force='mesh'); meshes[n] = (np.asarray(m.vertices, float), np.asarray(m.faces, np.int64))
    MASK = [(obj_mask(meshes, camT, t, KR, shape) | hand_mask(Hz, t, W0, KR, shape)).astype(bool) for t in range(N)]
    log('masks: mean masked fraction', round(float(np.mean([m.mean() for m in MASK])), 3), 'max', round(float(max(m.mean() for m in MASK)), 3))

    # ---- table planes (SGBM depth, objects and hands masked), cached per frame
    sgbm = cv2.StereoSGBM_create(minDisparity=0, numDisparities=192, blockSize=5, P1=8 * 25, P2=32 * 25, disp12MaxDiff=1,
                                 uniquenessRatio=10, speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    PL, DEP = {}, {}

    def plane(t, Wpre=None):
        if t not in DEP:
            d = sgbm.compute(rc[t], rb[t]).astype(np.float32) / 16.0
            DEP[t] = np.where(d > 1, FR * BASE / np.maximum(d, 1e-6), 0).astype(np.float32)
        prior = None
        if Wpre is not None:                                   # frame-0 plane in this camera, through the pose estimate
            prior = (Wpre[:3, :3].T @ p0['n'], p0['c'] + float(p0['n'] @ Wpre[:3, 3]))
        PL[t] = plane_fit(DEP[t], KR, ~MASK[t], prior)
        return PL[t]
    p0 = None
    p0 = plane(0)
    log('frame-0 plane', np.round(p0['n'], 4).tolist(), round(p0['c'], 4), 'inliers', p0['n_inl'], 'rms mm', round(p0['rms_mm'], 2))
    rep = dict(params=dict(DIL_OBJ=DIL_OBJ, DIL_HAND=DIL_HAND, RATIO_ST=RATIO_ST, RATIO_KF=RATIO_KF, ROW_TOL=ROW_TOL, ZMIN=ZMIN,
                           ZMAX=ZMAX, PNP_PX=PNP_PX, PNP_MIN=PNP_MIN, MAP=a.map, KF_MODE=a.kf_mode, NO_MASK=a.no_mask, KF_OK=a.kf_ok, PL_MIN=a.pl_min, PL_MAXRMS=PL_MAXRMS, PL_MAXDEG=PL_MAXDEG,
                           PL_MAXCM=PL_MAXCM, PL_BAND=PL_BAND, sgbm='192 disp, block 5, 3WAY, full res'),
               inputs={k: dict(path=getattr(a, k), sha256_16=sha(getattr(a, k))) for k in ('b', 'c', 'calib', 'poses', 'vo', 'hands')},
               meshes={n: sha(f'{a.meshes}/{n}.glb') for n in names}, frames=N, objects=names,
               rect=dict(focal=FR, baseline=BASE, KR=KR.tolist()),
               plane0=dict(n=p0['n'].tolist(), c=p0['c'], n_inl=p0['n_inl'], rms_mm=p0['rms_mm']), variants={})
    out = {}
    if 'base' in variants:
        out['base'] = W0[:N].copy()

    def plane_step(t, Wpre, tag):
        pc = plane(t, Wpre)
        if pc is None:
            return np.eye(4), dict(t=t, applied=False, why='no plane')
        C, ang, tau = plane_correction(pc, Wpre, p0)
        info = dict(t=t, n_inl=pc['n_inl'], rms_mm=round(pc['rms_mm'], 2), tilt_deg=round(ang, 3), shift_cm=round(tau, 3),
                    move_cm_at_table=round(float(np.linalg.norm(C[:3, :3] @ (Wpre[:3, :3] @ pc['centroid'] + Wpre[:3, 3]) + C[:3, 3]
                                                                - (Wpre[:3, :3] @ pc['centroid'] + Wpre[:3, 3])) * 100), 3))
        if pc['n_inl'] < a.pl_min or pc['rms_mm'] > PL_MAXRMS or ang > PL_MAXDEG or abs(tau) > PL_MAXCM:
            info.update(applied=False, why='failed fit gate'); return np.eye(4), info
        info['applied'] = True
        return C, info

    # ---- F3 alone on the stored chain
    if 'plane' in variants:
        kfs = json.load(open(a.vo))['keyframes']
        Cc = np.eye(4); Wp = W0[:N].copy(); infos = []
        bounds = list(kfs) + [N]
        for j, k in enumerate(kfs):
            if k > 0:
                Cj, info = plane_step(k, Cc @ W0[k], 'plane'); Cc = Cj @ Cc; infos.append(info)
            for t in range(k, min(bounds[j + 1], N)):
                Wp[t] = Cc @ W0[t]
        out['plane'] = Wp
        rep['variants']['plane'] = dict(keyframes=kfs, corrections=infos)
        log('plane: corrections', [(i['t'], i.get('tilt_deg'), i.get('shift_cm'), i['applied']) for i in infos])

    # ---- F1 (+F3): stereo keyframe-map VO, masked, earliest usable keyframe
    if 'rvo' in variants or 'rvo_plane' in variants:
        sift = cv2.SIFT_create(nfeatures=4000); siftb = cv2.SIFT_create(nfeatures=6000); bf = cv2.BFMatcher(cv2.NORM_L2)
        FC, ST = [], []
        dmin, dmax = FR * BASE / ZMAX, FR * BASE / ZMIN
        for t in range(N):
            kc, Dc = sift.detectAndCompute(rc[t], None if a.no_mask else (255 * (~MASK[t])).astype(np.uint8))
            kb, Db = siftb.detectAndCompute(rb[t], None) if a.map == 'sift' else ((), None)
            pc_ = np.array([k.pt for k in kc], np.float32).reshape(-1, 2); pb_ = np.array([k.pt for k in kb], np.float32).reshape(-1, 2)
            FC.append((pc_, Dc))
            X = np.full((len(pc_), 3), np.nan)
            if Dc is not None and Db is not None and len(pc_) and len(pb_):
                dv = np.abs(pc_[:, None, 1] - pb_[None, :, 1]); du = pc_[:, None, 0] - pb_[None, :, 0]
                M = ((dv < ROW_TOL) & (du > dmin) & (du < dmax)).astype(np.uint8)
                mm = bf.knnMatch(Dc, Db, k=2, mask=M)
                for x in mm:
                    if len(x) < 2 or x[0].distance >= RATIO_ST * x[1].distance:   # a lone candidate in the band is not trusted
                        continue
                    i, j = x[0].queryIdx, x[0].trainIdx
                    d = float(pc_[i, 0] - pb_[j, 0]); z = FR * BASE / d
                    X[i] = [(pc_[i, 0] - KR[0, 2]) * z / FR, (pc_[i, 1] - KR[1, 2]) * z / FR, z]
            ST.append(X)
            if t % 50 == 0:
                log('features', t, 'c kp', len(pc_), 'stereo 3-D', int(np.isfinite(X[:, 0]).sum()))

        def pnp(kf, t):
            Xw, Dk = kf['Xw'], kf['D']
            pt, Dt = FC[t]
            if Dt is None or len(Xw) < PNP_MIN or len(pt) < PNP_MIN:
                return None, 0
            good = [p[0] for p in bf.knnMatch(Dk, Dt, k=2) if len(p) == 2 and p[0].distance < RATIO_KF * p[1].distance]
            if len(good) < PNP_MIN:
                return None, 0
            O = np.float64([Xw[g.queryIdx] for g in good]); I_ = np.float64([pt[g.trainIdx] for g in good])
            ok, rv, tv, inl = cv2.solvePnPRansac(O, I_, KR, None, iterationsCount=2000, reprojectionError=PNP_PX,
                                                 confidence=0.999, flags=cv2.SOLVEPNP_SQPNP)
            if not ok or inl is None or len(inl) < 20:
                return None, 0
            inl = inl[:, 0]
            rv, tv = cv2.solvePnPRefineLM(O[inl], I_[inl], KR, None, rv, tv)
            for _ in range(2):
                pr, _ = cv2.projectPoints(O, rv, tv, KR, None)
                inl = np.flatnonzero(np.linalg.norm(pr[:, 0] - I_, axis=1) < PNP_PX)
                if len(inl) < 20:
                    return None, 0
                rv, tv = cv2.solvePnPRefineLM(O[inl], I_[inl], KR, None, rv, tv)
            M = np.eye(4); M[:3, :3] = cv2.Rodrigues(rv)[0]; M[:3, 3] = tv[:, 0]
            return np.linalg.inv(M), len(inl)                  # world_T_cam

        def map_pts(t):                                          # keyframe 3-D (camera t) per c keypoint, nan if none
            if a.map == 'sift':
                return ST[t]
            if t not in DEP:
                d = sgbm.compute(rc[t], rb[t]).astype(np.float32) / 16.0
                DEP[t] = np.where(d > 1, FR * BASE / np.maximum(d, 1e-6), 0).astype(np.float32)
            pt = FC[t][0]; z = cv2.remap(DEP[t], pt[:, 0].reshape(-1, 1), pt[:, 1].reshape(-1, 1), cv2.INTER_NEAREST).ravel()
            z = np.where((z > ZMIN) & (z < ZMAX), z, np.nan)
            return np.stack([(pt[:, 0] - KR[0, 2]) * z / FR, (pt[:, 1] - KR[1, 2]) * z / FR, z], 1)

        def make_kf(t, Wt):
            X = map_pts(t); ok = np.isfinite(X[:, 0])
            return dict(t=t, Xw=X[ok] @ Wt[:3, :3].T + Wt[:3, 3], D=FC[t][1][ok])

        for v in [x for x in ('rvo', 'rvo_plane') if x in variants]:
            use_plane = v == 'rvo_plane'
            W = [np.eye(4)]; kfs = [make_kf(0, np.eye(4))]; ninl, used, fails, pinfo = [0], [0], 0, []
            for t in range(1, N):
                cand = []; pick = None
                if a.kf_mode == 'latest' and t - 1 > kfs[-1]['t']:   # ablation: perc2's chain (latest keyframe only)
                    Wl, nl = pnp(kfs[-1], t)
                    if Wl is None or nl < a.kf_ok:
                        kfs.append(make_kf(t - 1, W[t - 1]))
                for kf in (kfs if a.kf_mode == 'earliest' else kfs[-1:]):   # earliest first
                    Wt, n_ = pnp(kf, t)
                    if Wt is not None:
                        cand.append((kf['t'], Wt, n_))
                        if n_ >= a.kf_ok:
                            pick = cand[-1]; break
                if pick is None and cand:
                    pick = max(cand, key=lambda c: c[2])
                if pick is None:
                    fails += 1; W.append(W[-1].copy()); ninl.append(0); used.append(-1); continue
                k, Wt, n_ = pick
                if n_ < a.kf_ok and a.kf_mode == 'earliest':     # no keyframe is usable: open one here
                    if use_plane:
                        C, info = plane_step(t, Wt, v); Wt = C @ Wt; pinfo.append(info)
                    kfs.append(make_kf(t, Wt))
                W.append(Wt); ninl.append(n_); used.append(k)
                if t % 25 == 0:
                    log(v, t, 'kf used', k, 'inliers', n_, 'keyframes', len(kfs))
            W = np.stack(W); out[v] = W
            u = np.array(used)
            rep['variants'][v] = dict(keyframes=[kf['t'] for kf in kfs], inliers=ninl, used=used, fails=fails,
                                      frames_on_kf0=int((u == 0).sum()), median_inliers=int(np.median(ninl[1:])),
                                      min_inliers=int(np.min(ninl[1:])), plane_corrections=pinfo)
            log(v, 'keyframes', [kf['t'] for kf in kfs], 'fails', fails, 'frames on kf0', int((u == 0).sum()),
                'median inliers', int(np.median(ninl[1:])))
            if pinfo:
                log(v, 'plane corrections', [(i['t'], i.get('tilt_deg'), i.get('shift_cm'), i['applied']) for i in pinfo])
    for v, W in out.items():
        np.save(f'{a.out}/W_{v}.npy', W)
        d = np.linalg.norm(W[:, :3, 3] - W0[:N, :3, 3], axis=1) * 100
        rep['variants'].setdefault(v, {})['cam_centre_diff_vs_base_cm'] = dict(f50=round(float(d[min(50, N - 1)]), 3),
                                                                            f100=round(float(d[min(100, N - 1)]), 3),
                                                                            end=round(float(d[-1]), 3), max=round(float(d.max()), 3))
    rep['planes'] = {str(t): (None if p is None else dict(n=np.round(p['n'], 5).tolist(), c=round(p['c'], 5), n_inl=p['n_inl'],
                                                        rms_mm=round(p['rms_mm'], 2))) for t, p in sorted(PL.items())}
    rep['seconds'] = round(time.time() - T0, 1)
    json.dump(rep, open(f'{a.out}/vo_t5.json', 'w'), indent=1)
    log('DONE')


if __name__ == '__main__':
    main()
