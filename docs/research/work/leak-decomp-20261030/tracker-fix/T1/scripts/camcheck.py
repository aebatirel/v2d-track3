"""GT-free camera check behind S6 (31 Oct 2026): is an object's perceived step a real move or a camera (VO) error?

S6 reads an object's travel in OUR world frame (world_T_cam @ cam_T_obj). A VO error moves every world-frame object, so a
static object can "travel" (ep24: 2.4 cm VO step). This check asks the static background instead: it warps our frame-0
rectified image, back-projected with our own frame-0 depth (det_f0.npz 'depth', half resolution, K/2), into frame t
through our camera world_T_cam[t] shifted by a world translation delta, and finds the delta that best explains frame t
(robust photometric residual: median absolute deviation of I0 - It on textured pixels, both images half resolution).
Excluded: our tracked objects (rendered surface samples, dilated) at frame 0 and frame t, and our hands (hull of the
21 joints, dilated and extended to the bottom image edge for the arm) at frame 0 and frame t.
delta ~ 0: the camera holds, and a world-frame object step is the object's own (a real move, or a tracker error).
delta ~ the object's step: the camera moved the world, and the object is static.
Reading the delta: if our camera is offset by +s (world_T_cam = T(+s) @ true), world-frame objects appear shifted by +s,
and the scan's minimum is at delta = +s. Components are given along u (the object's horizontal step direction at t),
w = n x u, and n (our frame-0 table normal, up), all in our world (= camera 0).
Inputs: our perception outputs only (poses.npz, det_f0.npz, hands, the cam-c video, the public camera calibration for
rectification, our meshes). No mocap, scans or observation.objects; every path goes through refine.assert_inference_input.
Usage: python -I camcheck.py --poses P --det D --hands H --video V --calib C --meshes DIR --obj NAME --frames 10,46,...
                             --out OUT.json
"""
import argparse, json, sys

import cv2
import numpy as np
import trimesh

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
        u = hvec / np.linalg.norm(hvec) if hcm > 0.5 else np.cross(n, [1.0, 0, 0]) / np.linalg.norm(np.cross(n, [1.0, 0, 0]))
        w = np.cross(n, u)
        B = np.stack([u, w, n], 1)                          # world <- (u, w, n) coefficients
        badt = mask_objects(pts, {k: camT[k][t] for k in names}, K2, shape) | mask_hands(Hz, t, W[t], K2, shape)
        It = I[t]

        def cost(coef):
            d = B @ np.asarray(coef, float)
            R, p_ = W[t][:3, :3], W[t][:3, 3] - d
            Y = (Xw - p_) @ R
            uv, z = proj(Y, K2)
            ok = (z > 0.05) & (uv[:, 0] >= 0) & (uv[:, 0] <= shape[1] - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= shape[0] - 1)
            ok[ok] &= ~badt[uv[ok, 1].round().astype(int), uv[ok, 0].round().astype(int)]
            if ok.sum() < 0.2 * len(Xw):
                return np.inf, 0.0, int(ok.sum())
            s = bilinear(It, uv[ok, 0], uv[ok, 1])
            r = i0[ok] - s
            mad = float(np.median(np.abs(r - np.median(r))))
            ncc = float(np.corrcoef(i0[ok], s)[0, 1])
            return mad, ncc, int(ok.sum())

        grid = np.arange(-8, 8.01, 2) / 100
        best = min(((cost((x, y, zz))[0], (x, y, zz)) for x in grid for y in grid for zz in grid), key=lambda q: q[0])
        fine = np.arange(-1.5, 1.51, 0.5) / 100
        best = min(((cost((best[1][0] + x, best[1][1] + y, best[1][2] + zz))[0],
                     (best[1][0] + x, best[1][1] + y, best[1][2] + zz)) for x in fine for y in fine for zz in fine),
                   key=lambda q: q[0])
        b = np.asarray(best[1])
        c0, cb = cost((0, 0, 0)), cost(b)
        line = {f'{x:+.1f}': round(cost((x / 100, 0, 0))[0], 3) for x in np.arange(-6, 6.01, 1.0)}
        res['frames'][str(t)] = dict(
            obj_step_cm=dict(horizontal=round(hcm, 2), vertical=round(v * 100, 2)),
            camera_delta_cm=dict(u=round(b[0] * 100, 2), w=round(b[1] * 100, 2), n=round(b[2] * 100, 2),
                                 norm=round(float(np.linalg.norm(b) * 100), 2)),
            mad_at_zero=round(c0[0], 3), mad_at_best=round(cb[0], 3), ncc_at_zero=round(c0[1], 4), ncc_at_best=round(cb[1], 4),
            px_used_at_zero=c0[2], cost_along_u=line)
        print(f'{a.label} f{t}: {a.obj} step h {hcm:.2f} (along u) v {v * 100:+.2f} cm | camera delta u {b[0] * 100:+.2f} '
              f'w {b[1] * 100:+.2f} n {b[2] * 100:+.2f} cm | MAD 0 {c0[0]:.2f} -> best {cb[0]:.2f}, NCC {c0[1]:.3f} -> '
              f'{cb[1]:.3f}, px {c0[2]}', flush=True)
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
