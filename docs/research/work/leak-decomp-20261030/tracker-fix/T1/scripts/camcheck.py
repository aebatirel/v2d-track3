"""GT-free camera check behind S6 (31 Oct 2026): is an object's perceived step a real move or a camera (VO) error?

S6 reads an object's travel in OUR world frame (world_T_cam @ cam_T_obj). A VO error moves every world-frame object, so a
static object can "travel" (ep24: 2.4 cm VO step). This check asks the static background instead: it warps our frame-0
rectified image, back-projected with our own frame-0 depth (det_f0.npz 'depth', half resolution, K/2), into frame t
through world_T_cam[t] @ E, and fits the correction E (6-DoF, and translation only) that best explains frame t: robust
photometric cost mean(log(1 + (r/10)^2)) of the median-centred residual r = I0 - It on textured pixels (top 40 % gradient),
coarse to fine (Gaussian sigma 4, 2, 0 px), Powell from E = I. Excluded: our tracked objects (rendered surface samples,
dilated) at frame 0 and frame t, and our hands (hull of the 21 joints, dilated and extended to the bottom image edge for
the arm) at frame 0 and frame t. Readout: the object's step after the correction ("corrected step"). If it stays at the
tracked step, the camera holds and the step is the object's own (a real move or a tracker error); if it drops to ~0, the
camera moved the world and the object is static. Controls: public ep24 (known 2.4 cm VO step on static board 2) and
ep11 (static blue cup, tracker lift, camera fine).
Inputs: our perception outputs only (poses.npz, det_f0.npz, hands, the cam-c video, the public camera calibration for
rectification, our meshes). No mocap, scans or observation.objects; every path goes through refine.assert_inference_input.
Usage: python -I camcheck.py --poses P --det D --hands H --video V --calib C --meshes DIR --obj NAME --frames 10,46,...
                             --out OUT.json
"""
import argparse, json, sys

import cv2
import numpy as np
import trimesh
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/pipeline')
import det_rules  # noqa: E402
from refine import assert_inference_input  # noqa: E402
from track_overlay import rectify_maps  # noqa: E402


def read_frames(video, MC, idx):
    cap, out, t = cv2.VideoCapture(video), {}, 0
    while len(out) < len(idx):
        ok, f = cap.read()
        if not ok:
            break
        if t in idx:
            r = cv2.remap(f, MC[0], MC[1], cv2.INTER_LINEAR)
            out[t] = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)[::2, ::2].astype(np.float32)
        t += 1
    return out


def proj(X, K):
    z = X[:, 2]
    return np.stack([X[:, 0] / z * K[0, 0] + K[0, 2], X[:, 1] / z * K[1, 1] + K[1, 2]], 1), z


def bilinear(I, x, y):
    x0 = np.clip(np.floor(x).astype(int), 0, I.shape[1] - 2)
    y0 = np.clip(np.floor(y).astype(int), 0, I.shape[0] - 2)
    fx, fy = x - x0, y - y0
    return ((1 - fy) * ((1 - fx) * I[y0, x0] + fx * I[y0, x0 + 1]) + fy * ((1 - fx) * I[y0 + 1, x0] + fx * I[y0 + 1, x0 + 1]))


def mask_objects(pts, camT, K, shape, dil=9):
    m = np.zeros(shape, np.uint8)
    for n, X in pts.items():
        Y = X @ camT[n][:3, :3].T + camT[n][:3, 3]
        uv, z = proj(Y, K)
        ok = (z > 0.05) & (uv[:, 0] >= 0) & (uv[:, 0] < shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < shape[0])
        m[uv[ok, 1].astype(int), uv[ok, 0].astype(int)] = 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return cv2.dilate(m, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8)).astype(bool)


def mask_hands(Hz, t, W_t, K, shape, dil=25):
    m = np.zeros(shape, np.uint8)
    for s in ('left', 'right'):
        if f'joints_{s}' not in Hz.files or not bool(Hz[f'valid_{s}'][t]):
            continue
        J = Hz[f'joints_{s}'][t].astype(float)
        if not np.isfinite(J).all():
            continue
        Y = (J - W_t[:3, 3]) @ W_t[:3, :3]                  # world -> camera t
        uv, z = proj(Y, K)
        if (z <= 0.05).any():
            continue
        wr = uv[0]
        P = np.vstack([uv, [[wr[0] - 40, shape[0] - 1], [wr[0] + 40, shape[0] - 1]]]).astype(np.int32)
        cv2.fillConvexPoly(m, cv2.convexHull(P), 1)
    return cv2.dilate(m, np.ones((2 * dil + 1, 2 * dil + 1), np.uint8)).astype(bool)


def main():
    p = argparse.ArgumentParser()
    for k in ('poses', 'det', 'hands', 'video', 'calib', 'meshes', 'obj', 'frames', 'out'):
        p.add_argument('--' + k, required=True)
    p.add_argument('--label', default='')
    a = p.parse_args()
    for f in (a.poses, a.det, a.hands, a.video, a.calib, a.meshes):
        assert_inference_input(f)
    P = np.load(a.poses)
    W = P['world_T_cam'].astype(float)
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    camT = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    det = np.load(a.det)
    Hz = np.load(a.hands)
    K = np.asarray(det['K'], float)
    K2 = np.diag([0.5, 0.5, 1.0]) @ K
    D0 = det['depth'].astype(np.float32)
    shape = D0.shape
    pl = det_rules.table_plane(D0, K2)                       # camera-0 plane, n.x + d = 0
    n = W[0][:3, :3] @ np.asarray(pl[0], float)
    n /= np.linalg.norm(n)
    MC, KR = rectify_maps(a.calib)
    frames = [int(x) for x in a.frames.split(',')]
    I = read_frames(a.video, MC, set([0] + frames))
    img0_corr = float(np.corrcoef(I[0].ravel(), det['image'].astype(np.float32).ravel())[0, 1])
    meshes = {k: trimesh.load(f'{a.meshes}/{k}.glb', force='mesh') for k in names}
    pts = {k: np.asarray(trimesh.sample.sample_surface(m, 20000, seed=0)[0], float) for k, m in meshes.items()}
    cen = {k: np.asarray(m.vertices, float).mean(0) for k, m in meshes.items()}
    O = {k: np.einsum('tij,tjk->tik', W, camT[k]) for k in names}
    c = O[a.obj][:, :3, :3] @ cen[a.obj] + O[a.obj][:, :3, 3]

    # frame-0 source pixels: valid depth, textured, off our objects and hands
    vv, uu = np.mgrid[0:shape[0], 0:shape[1]]
    g = np.hypot(cv2.Sobel(I[0], cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(I[0], cv2.CV_32F, 0, 1, ksize=3))
    bad0 = mask_objects(pts, {k: camT[k][0] for k in names}, K2, shape) | mask_hands(Hz, 0, W[0], K2, shape)
    sel = (D0 > 0.15) & (D0 < 2.5) & ~bad0 & (g > np.percentile(g, 60))
    idx = np.flatnonzero(sel)
    idx = idx[np.random.default_rng(0).permutation(len(idx))[:80000]]
    z0 = D0.ravel()[idx].astype(float)
    X0 = np.stack([(uu.ravel()[idx] - K2[0, 2]) / K2[0, 0] * z0, (vv.ravel()[idx] - K2[1, 2]) / K2[1, 1] * z0, z0], 1)
    Xw = X0 @ W[0][:3, :3].T + W[0][:3, 3]
    i0 = I[0].ravel()[idx]
    res = dict(label=a.label, obj=a.obj, n_world=np.round(n, 5).tolist(), rect_check_corr_vs_det_image=round(img0_corr, 4),
               n_source_px=int(len(idx)), frames={})
    for t in frames:
        dc = c[t] - c[0]
        v = float(dc @ n)
        hvec = dc - v * n
        hcm = float(np.linalg.norm(hvec) * 100)
        badt = mask_objects(pts, {k: camT[k][t] for k in names}, K2, shape) | mask_hands(Hz, t, W[t], K2, shape)
        It = I[t]

        def E_of(p):                                         # p = (omega deg x3, tau cm x3), camera-t coordinates
            E = np.eye(4)
            E[:3, :3] = Rot.from_rotvec(np.radians(p[:3])).as_matrix()
            E[:3, 3] = np.asarray(p[3:]) / 100
            return E

        def warp(p, Ib):
            Wt = W[t] @ E_of(p)
            Y = (Xw - Wt[:3, 3]) @ Wt[:3, :3]
            uv, z = proj(Y, K2)
            ok = (z > 0.05) & (uv[:, 0] >= 0) & (uv[:, 0] <= shape[1] - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= shape[0] - 1)
            ok[ok] &= ~badt[uv[ok, 1].round().astype(int), uv[ok, 0].round().astype(int)]
            return ok, bilinear(Ib, uv[ok, 0], uv[ok, 1]) if ok.any() else np.zeros(0)

        def cost(p, lev=0):
            I0b, Itb = pyr[lev]
            ok, s_ = warp(p, Itb)
            if ok.sum() < 0.2 * len(Xw):
                return 1e3
            r = I0b.ravel()[idx][ok] - s_
            r = r - np.median(r)
            return float(np.mean(np.log1p((r / 10.0) ** 2)))

        def stats(p):
            ok, s_ = warp(p, It)
            r = i0[ok] - s_
            return float(np.median(np.abs(r - np.median(r)))), float(np.corrcoef(i0[ok], s_)[0, 1]), int(ok.sum())

        pyr = [(cv2.GaussianBlur(I[0], (0, 0), sg), cv2.GaussianBlur(It, (0, 0), sg)) if sg else (I[0], It)
               for sg in (4.0, 2.0, 0)]
        fits = {}
        for kind, free in (('translation', [3, 4, 5]), ('six_dof', [0, 1, 2, 3, 4, 5])):
            p = np.zeros(6)
            for lev in (0, 1, 2):
                def f_(q, lev=lev, free=free, p0=p.copy()):
                    pp = p0.copy()
                    pp[free] = q
                    return cost(pp, lev)
                r_ = minimize(f_, p[free], method='Powell', options=dict(xtol=1e-3, ftol=1e-6, maxfev=3000))
                p[free] = r_.x
            Wc = W[t] @ E_of(p)
            Oc = Wc @ camT[a.obj][t]
            cc = Oc[:3, :3] @ cen[a.obj] + Oc[:3, 3]
            d2 = cc - c[0]
            v2 = float(d2 @ n)
            dw = (Wc @ np.linalg.inv(W[t]))                  # the correction as a world transform
            st0, stp = stats(np.zeros(6)), stats(p)
            fits[kind] = dict(omega_deg=np.round(p[:3], 3).tolist(), tau_cm=np.round(p[3:], 2).tolist(),
                              obj_world_shift_cm=round(float(np.linalg.norm(cc - c[t]) * 100), 2),
                              corrected_obj_step_cm=dict(horizontal=round(float(np.linalg.norm(d2 - v2 * n) * 100), 2),
                                                         vertical=round(v2 * 100, 2)),
                              world_correction_translation_cm=np.round(dw[:3, 3] * 100, 2).tolist(),
                              robust_cost=dict(zero=round(cost(np.zeros(6), 2), 4), fit=round(cost(p, 2), 4)),
                              mad=dict(zero=round(st0[0], 3), fit=round(stp[0], 3)), ncc=dict(zero=round(st0[1], 4), fit=round(stp[1], 4)),
                              px=dict(zero=st0[2], fit=stp[2]))
        res['frames'][str(t)] = dict(obj_step_cm=dict(horizontal=round(hcm, 2), vertical=round(v * 100, 2)), fits=fits)
        f6, f3 = fits['six_dof'], fits['translation']
        print(f'{a.label} f{t}: {a.obj} tracked step h {hcm:.2f} v {v * 100:+.2f} cm | 6dof: omega {f6["omega_deg"]} deg, '
              f'tau {f6["tau_cm"]} cm, object moves {f6["obj_world_shift_cm"]} cm -> corrected step h '
              f'{f6["corrected_obj_step_cm"]["horizontal"]} v {f6["corrected_obj_step_cm"]["vertical"]}; cost '
              f'{f6["robust_cost"]["zero"]}->{f6["robust_cost"]["fit"]}, NCC {f6["ncc"]["zero"]}->{f6["ncc"]["fit"]} | '
              f'transl only: corrected step h {f3["corrected_obj_step_cm"]["horizontal"]} v '
              f'{f3["corrected_obj_step_cm"]["vertical"]}, cost {f3["robust_cost"]["fit"]}', flush=True)
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
