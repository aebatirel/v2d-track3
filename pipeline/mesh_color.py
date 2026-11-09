"""Paint a reconstructed mesh with the observed grey level (inference only: our video, depth and tracked poses).

FoundationPose compares rendered appearance with the image, and a reconstruction from recon_mesh.py has no colour.
Each vertex is projected into every STRIDE-th rectified-left mono frame of each episode with cam_T_<obj>; where the
stereo depth at that pixel agrees with the vertex depth (|d - z| < --vis_tol, i.e. visible, not occluded) the grey
level is collected; the vertex colour is the median. Vertices never seen get the median of all seen vertices.
Usage: python mesh_color.py --mesh in.glb --obj NAME --poses a.npz[,b.npz] [--depth a.npy[,b.npy]]
                            --video a_c.mp4[,b_c.mp4] --calib calib.json --out out.glb
--cam a (2026-11-09, colour-camera test, docs/analysis/colourcam-20261109/PREREG.md): paint RGB from colour camera a
instead (--video = the camera-a videos). Stereo frame t pairs with camera-a frame t + A_OFFSET (det_rules); each vertex is
projected into the raw camera-a image with its distortion; a sample counts when the vertex passes the stereo-depth test
in the rectified-left view (as the grey mode) and is not hidden by the mesh itself in camera a (own z-buffer, 4-px grid).
The vertex colour is the per-channel median. The default (--cam c) is unchanged.
"""
import argparse, json
import numpy as np, cv2, trimesh


def rectify(calib_path):
    C = json.load(open(calib_path)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                                (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                                alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    return cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, (1600, 1000), cv2.CV_32FC1), P1[:3, :3]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('mesh', 'obj', 'poses', 'video', 'calib', 'out'):
        p.add_argument(f'--{k}', required=True)
    p.add_argument('--depth', default=None, help='stereo depth per episode for the visibility test; without it the '
                   "mesh's own z-buffer decides (self-occlusion only; hands are outvoted by the median)")
    p.add_argument('--stride', type=int, default=4); p.add_argument('--vis_tol', type=float, default=0.01)
    p.add_argument('--cam', default='c', choices=['c', 'a'])
    a = p.parse_args()
    if a.cam == 'a':
        return paint_a(a)
    (MX, MY), K = rectify(a.calib)
    m = trimesh.load(a.mesh, force='mesh'); V = np.asarray(m.vertices)
    samples = [[] for _ in range(len(V))]
    depths = a.depth.split(',') if a.depth else [None] * len(a.poses.split(','))
    for pp, dp, vp in zip(a.poses.split(','), depths, a.video.split(',')):
        T = np.load(pp)[f'cam_T_{a.obj}']; D = np.load(dp, mmap_mode='r') if dp else None
        cap = cv2.VideoCapture(vp); t = -1
        while True:
            ok, f = cap.read(); t += 1
            if not ok or t >= (min(len(T), len(D)) if D is not None else len(T)):
                break
            if t % a.stride:
                continue
            g = cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MX, MY, cv2.INTER_LINEAR)
            X = V @ T[t][:3, :3].T + T[t][:3, 3]; z = X[:, 2]
            ok_ = z > 0.05
            u = np.full(len(V), -1); v = np.full(len(V), -1)
            u[ok_] = np.round(K[0, 0] * X[ok_, 0] / z[ok_] + K[0, 2]).astype(int)
            v[ok_] = np.round(K[1, 1] * X[ok_, 1] / z[ok_] + K[1, 2]).astype(int)
            ok_ &= (u >= 0) & (u < g.shape[1]) & (v >= 0) & (v < g.shape[0])
            idx = np.nonzero(ok_)[0]
            if D is not None:
                d = np.asarray(D[t])[v[idx], u[idx]]
            else:                                                  # own z-buffer on a 4-px grid
                zb = np.full((g.shape[0] // 4 + 1, g.shape[1] // 4 + 1), np.inf)
                np.minimum.at(zb, (v[idx] // 4, u[idx] // 4), z[idx])
                d = zb[v[idx] // 4, u[idx] // 4]
            vis = np.isfinite(d) & (np.abs(d - z[idx]) < a.vis_tol)
            for i, val in zip(idx[vis], g[v[idx[vis]], u[idx[vis]]]):
                samples[i].append(val)
    seen = np.array([len(s) > 0 for s in samples])
    grey = np.array([np.median(s) if s else 0 for s in samples], float)
    if seen.any():
        grey[~seen] = np.median(grey[seen])
    else:
        grey[:] = 128
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.c_[np.repeat(grey[:, None], 3, 1), np.full(len(V), 255)].astype(np.uint8))
    m.export(a.out)
    print(json.dumps(dict(obj=a.obj, verts=len(V), seen_frac=round(float(seen.mean()), 3),
                          grey_median=float(np.median(grey)), grey_p10_p90=[float(np.percentile(grey, 10)), float(np.percentile(grey, 90))])))


def paint_a(a):
    """--cam a: RGB from colour camera a along the rectified-left poses (see the module docstring)."""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from det_rules import A_OFFSET
    C = json.load(open(a.calib)); cam = C['cameras']
    sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                                (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                                alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    K = P1[:3, :3]
    ext = lambda n: np.array(cam[n]['extrinsics_to_stereo_left'], float)  # noqa: E731
    T_a_c = np.linalg.inv(ext('ego_cam_a')) @ ext('ego_cam_c')
    Ra, ta = T_a_c[:3, :3] @ R1.T, T_a_c[:3, 3]                       # rectified-left -> camera a
    Ka, Da = K_('ego_cam_a'), D_('ego_cam_a')
    m = trimesh.load(a.mesh, force='mesh'); V = np.asarray(m.vertices)
    samples = [[] for _ in range(len(V))]
    depths = a.depth.split(',') if a.depth else [None] * len(a.poses.split(','))
    used = 0
    for pp, dp, vp in zip(a.poses.split(','), depths, a.video.split(',')):
        T = np.load(pp)[f'cam_T_{a.obj}']; D = np.load(dp, mmap_mode='r') if dp else None
        n_ = min(len(T), len(D)) if D is not None else len(T)
        cap = cv2.VideoCapture(vp); ta_ = -1
        while True:
            ok, f = cap.read(); ta_ += 1
            if not ok:
                break
            t = ta_ - A_OFFSET
            if t < 0 or t % a.stride:
                continue
            if t >= n_:
                break
            img = cv2.cvtColor(f, cv2.COLOR_BGR2RGB); H, W = img.shape[:2]
            X = V @ T[t][:3, :3].T + T[t][:3, 3]; z = X[:, 2]
            vis = z > 0.05
            if D is not None:                                          # stereo-depth test in the rectified-left view
                u = np.full(len(V), -1); v = np.full(len(V), -1)
                u[vis] = np.round(K[0, 0] * X[vis, 0] / z[vis] + K[0, 2]).astype(int)
                v[vis] = np.round(K[1, 1] * X[vis, 1] / z[vis] + K[1, 2]).astype(int)
                vis &= (u >= 0) & (u < 1600) & (v >= 0) & (v < 1000)
                idx = np.nonzero(vis)[0]; d = np.asarray(D[t])[v[idx], u[idx]]
                vis[idx] = np.isfinite(d) & (np.abs(d - z[idx]) < a.vis_tol)
            Xa = X @ Ra.T + ta; za = Xa[:, 2]; vis &= za > 0.05
            uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); uv = uv.reshape(-1, 2)
            ua, va = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
            vis &= (ua >= 0) & (ua < W) & (va >= 0) & (va < H)
            idx = np.nonzero(vis)[0]
            if len(idx) == 0:
                continue
            zb = np.full((H // 4 + 1, W // 4 + 1), np.inf)              # own z-buffer in camera a (self-occlusion)
            np.minimum.at(zb, (va[idx] // 4, ua[idx] // 4), za[idx])
            keep = za[idx] <= zb[va[idx] // 4, ua[idx] // 4] + a.vis_tol
            for i, val in zip(idx[keep], img[va[idx[keep]], ua[idx[keep]]]):
                samples[i].append(val)
            used += 1
    seen = np.array([len(s_) > 0 for s_ in samples])
    col = np.array([np.median(np.stack(s_), 0) if s_ else [0, 0, 0] for s_ in samples], float)
    if seen.any():
        col[~seen] = np.median(col[seen], 0)
    else:
        col[:] = 128
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.c_[col, np.full(len(V), 255)].astype(np.uint8))
    m.export(a.out)
    print(json.dumps(dict(obj=a.obj, cam='a', verts=len(V), frames=used, seen_frac=round(float(seen.mean()), 3),
                          rgb_median=np.median(col, 0).round(1).tolist())))


if __name__ == '__main__':
    main()
