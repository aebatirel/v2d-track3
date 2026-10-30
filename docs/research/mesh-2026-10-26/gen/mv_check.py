"""GT-free frame check for Pixal3D-MV outputs (batch-2 generative probe, 2026-10-29).

Projects a mesh given in OUR object frame into every view of a mv_views.py view set (the virtual pinhole cameras of
transforms.json, mapped back to the object frame with probe_meta.json) and reports the silhouette IoU against the
view's own mask (alpha). Uses only our views and masks; no scan. A correct frame mapping gives IoU close to the
mask quality (~0.85-0.95); a wrong axis convention gives low IoU.
Usage: mv_check.py VIEWDIR mesh.ply [mesh2.ply ...]
"""
import json, math, os, sys
import numpy as np
import cv2
import trimesh

GL = np.diag([1.0, -1.0, -1.0])


def views(vd):
    T = json.load(open(os.path.join(vd, 'transforms.json')))
    M = json.load(open(os.path.join(vd, 'probe_meta.json')))
    s, c, A = M['s'], np.array(M['c']), np.array(M['A'])
    out = []
    for fr in T['frames']:
        C = np.array(fr['transform_matrix'])
        Rw, ow = C[:3, :3] @ GL, C[:3, 3]                 # OpenCV-axes camera-to-world in the Pixal3D world
        R_co = A.T @ Rw                                   # camera -> object rotation
        o = c + A.T @ ow / s                              # camera centre, object frame
        alpha = cv2.imread(os.path.join(vd, fr['file_path']), cv2.IMREAD_UNCHANGED)[:, :, 3] > 127
        S = alpha.shape[0]
        f = S / (2 * math.tan(fr['camera_angle_x'] / 2))
        out.append((fr['file_path'], R_co, o, f, S, alpha))
    return out


def silhouette(pts, R_co, o, f, S):
    X = (pts - o) @ R_co                                  # object -> camera (OpenCV axes): R_co^T (p - o)
    X = X[X[:, 2] > 1e-4]
    u = f * X[:, 0] / X[:, 2] + S / 2; v = f * X[:, 1] / X[:, 2] + S / 2
    ok = (u >= 0) & (u < S) & (v >= 0) & (v < S)
    img = np.zeros((S, S), np.uint8)
    img[v[ok].astype(int), u[ok].astype(int)] = 1
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return img > 0


def main():
    vd = sys.argv[1]
    V = views(vd)
    for mp in sys.argv[2:]:
        m = trimesh.load(mp, force='mesh', process=False)
        pts = trimesh.sample.sample_surface(m, 400000, seed=0)[0]
        ious = []
        for name, R_co, o, f, S, alpha in V:
            sil = silhouette(pts, R_co, o, f, S)
            ious.append(float((sil & alpha).sum() / max((sil | alpha).sum(), 1)))
        print(json.dumps(dict(mesh=os.path.basename(mp), views=[v[0] for v in V], iou=[round(x, 3) for x in ious],
                              mean_iou=round(float(np.mean(ious)), 3))))


if __name__ == '__main__':
    main()
