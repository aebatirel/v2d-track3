"""Paint a reconstructed mesh with the observed grey level (inference only: our video, depth and tracked poses).

FoundationPose compares rendered appearance with the image, and a reconstruction from recon_mesh.py has no colour.
Each vertex is projected into every STRIDE-th rectified-left mono frame of each episode with cam_T_<obj>; where the
stereo depth at that pixel agrees with the vertex depth (|d - z| < --vis_tol, i.e. visible, not occluded) the grey
level is collected; the vertex colour is the median. Vertices never seen get the median of all seen vertices.
Usage: python mesh_color.py --mesh in.glb --obj NAME --poses a.npz[,b.npz] [--depth a.npy[,b.npy]]
                            --video a_c.mp4[,b_c.mp4] --calib calib.json --out out.glb
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
    a = p.parse_args()
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


if __name__ == '__main__':
    main()
