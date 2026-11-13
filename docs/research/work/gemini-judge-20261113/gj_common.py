"""Shared helpers for the Gemini judge tests G-A and G-B (2026-11-13). INFERENCE SIDE ONLY.

Everything here reads our own perception outputs (tracks, hands), the public calibration, the public videos and our
own or generated meshes. Nothing here may open ground truth: mocap, dataset parquets (`observation.objects` pose),
public scans used as GT, label files (`calib_gt`, `*_pf.npz`, `/gt/`) or scorer outputs. `guard()` enforces a
deny-list on every path the builders open.

Geometry is the repository's own, imported unchanged:
  - rectified-left camera (the camera our tracks live in): pipeline/track_overlay.py rectify_maps();
  - colour camera ego_cam_a: docs/research/mesh-2026-10-26/scripts/crops.py geometry() (T_a_rect, Ka, Da), with
    colour frame j = k + a_offset for stereo frame k (pipeline/hands_mp.py; a_offset is stored in hands.npz).
"""
import json, os, re, sys

import numpy as np
import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
sys.path.insert(0, os.path.join(REPO, 'docs', 'research', 'mesh-2026-10-26', 'scripts'))
from track_overlay import rectify_maps  # noqa: E402
from crops import geometry as colour_geometry  # noqa: E402

# Substrings of paths that hold or derive from ground truth (same spirit as refine.FORBIDDEN_SUBSTR).
FORBIDDEN = ('calib_gt', '/gt/', '_pf.npz', 'per_frame.npz', 'per_frame.csv', 'score_registered', 'result.json',
             'quarantine_gt', 'baseline/', 'mocap', '.parquet', '/scan', '_scan', 'collision.glb', 'track_3/public/mesh',
             'rows.json', 'scores.jsonl', 'table.md', 'selection.json')


def guard(path):
    """Raise if a path the inference side is about to open could hold ground truth."""
    for p in (str(path), os.path.realpath(str(path))):
        low = p.lower()
        for f in FORBIDDEN:
            if f in low:
                raise ValueError(f'inference guard: refusing {path!r} (matches {f!r})')
    return path


def nice_name(obj):
    """Slot name -> plain object name for the text input (object names are allowed: the kit gives them for eval)."""
    return obj.replace('_', ' ')


class Reader:
    """Sequential frame reader (seeking an mp4 per frame is slow)."""
    def __init__(self, path):
        self.cap = cv2.VideoCapture(guard(path)); self.i = -1; self.img = None
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.W = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)); self.H = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get(self, j):
        if j < self.i:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, j); self.i = j - 1
        while self.i < j:
            ok, self.img = self.cap.read(); self.i += 1
            if not ok:
                return None
        return self.img


def load_mesh(path):
    import trimesh
    m = trimesh.load(guard(path), force='mesh', process=False)
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def square_window(x0, y0, x1, y1, grow, min_side):
    """Square window (cx, cy, side) around a box, side = max(grow * longest edge, min_side)."""
    side = max(grow * max(x1 - x0, y1 - y0), min_side)
    return 0.5 * (x0 + x1), 0.5 * (y0 + y1), float(side)


def crop_affine(img, cx, cy, side, out):
    """Crop the square window (cx, cy, side) of img and resample it to out x out (border = black)."""
    s = out / side
    A = np.array([[s, 0, -(cx - side / 2) * s], [0, s, -(cy - side / 2) * s]], np.float64)
    return cv2.warpAffine(img, A, (out, out), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def project_pinhole(X, K):
    return (X[:, :2] / X[:, 2:3]) * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]


def silhouette_pinhole(V, F, T, K, cx, cy, side, out):
    """Filled silhouette (uint8 0/1, out x out) of mesh (V, F) at pose T (object -> camera), pinhole K, inside the
    square window (cx, cy, side) of the full image, resampled to out x out. Every face is filled one by one (no
    culling; cv2.fillPoly on a list of polygons would use the even-odd rule and cancel overlapping faces)."""
    X = V @ T[:3, :3].T + T[:3, 3]
    if (X[:, 2] <= 0.02).any():
        raise ValueError('mesh crosses the camera plane')
    uv = project_pinhole(X, K)
    s = out / side
    p = (uv - [cx - side / 2, cy - side / 2]) * s
    SH = 4                                              # fixed-point subpixel bits
    tri = np.round(p[F] * (1 << SH)).astype(np.int32)
    m = np.zeros((out, out), np.uint8)
    for t in tri:
        cv2.fillConvexPoly(m, t, 1, cv2.LINE_8, SH)
    return m


def outline(mask):
    """External contour(s) of a filled silhouette. Internal contours are not drawn: our library meshes are not
    watertight, and their holes (e.g. in the pot's floor) would draw edges the real object does not have."""
    cnt, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return cnt


class Shader:
    """Ray-cast grey render of a mesh (embree via trimesh). Rays are given per pixel in the camera frame."""
    def __init__(self, V, F):
        import trimesh
        self.mesh = trimesh.Trimesh(V, F, process=False)
        self.N = self.mesh.face_normals
        from trimesh.ray.ray_pyembree import RayMeshIntersector
        self.rmi = RayMeshIntersector(self.mesh)

    def render(self, T, dirs_cam, bg=255):
        """T: object -> camera; dirs_cam (H, W, 3) unit rays in the camera frame. Returns (H, W) uint8 grey image and
        the hit mask. Headlight shading on |cos| (generated meshes are not reliably oriented) plus a weak key light
        from the camera's up-left so that curvature reads."""
        H, W, _ = dirs_cam.shape
        R, t = T[:3, :3], T[:3, 3]
        o = -R.T @ t                                     # camera centre in the object frame
        d = dirs_cam.reshape(-1, 3) @ R                  # = (R^T d^T)^T
        tri = self.rmi.intersects_first(np.repeat(o[None], len(d), 0), d)
        hit = tri >= 0
        n = self.N[tri[hit]]
        head = np.abs((n * d[hit]).sum(1))
        key_cam = np.array([-0.4, -0.6, -0.7]); key_cam /= np.linalg.norm(key_cam)
        key = np.abs(n @ (R.T @ key_cam))
        I = 0.12 + 0.68 * head + 0.20 * key
        img = np.full(H * W, bg, np.float64)
        img[hit] = 225 * np.clip(I, 0, 1)
        return img.reshape(H, W).astype(np.uint8), hit.reshape(H, W)


def pixel_rays_distorted(K, D, cx, cy, side, out):
    """Unit camera-frame rays through the centres of an out x out grid covering the square window (cx, cy, side) of
    a camera with intrinsics K and OpenCV distortion D (pixel coordinates are in the distorted image)."""
    g = (np.arange(out) + 0.5) * side / out
    u, v = np.meshgrid(cx - side / 2 + g, cy - side / 2 + g)
    pts = np.stack([u.ravel(), v.ravel()], 1).reshape(-1, 1, 2).astype(np.float64)
    nrm = cv2.undistortPoints(pts, K, D).reshape(-1, 2)
    d = np.c_[nrm, np.ones(len(nrm))]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return d.reshape(out, out, 3)


def project_distorted(X, K, D):
    return cv2.projectPoints(X.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, D)[0].reshape(-1, 2)


def jpeg_bytes(img_bgr, q=90):
    ok, b = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, q])
    assert ok
    return b.tobytes()


def write_jsonl(path, rows):
    with open(path, 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')


def k_from_label(label):
    m = re.search(r'_k(\d+)_s\d+$', label)
    return int(m.group(1)) if m else None
