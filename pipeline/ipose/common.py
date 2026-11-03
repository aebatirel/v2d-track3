"""Instance-level pot pose (ipose, 3 Nov 2026): shared geometry, data access and the point-splat renderer.

Licence-clean, own code (no nvdiffrast / OpenGL): the mesh is densely sampled once (points, normals, albedo) and each
view is rendered by projecting the points and keeping the nearest per pixel (z-buffer via scatter_reduce), then holes
are closed with a 3x3 nearest fill. Gives grey image, visible-surface object coordinates (XYZ map), depth and mask.
Camera convention: OpenCV (x right, y down, z forward); intrinsics in pixels with pixel centres at integer coords.
Images are the RECTIFIED LEFT ego camera (ego_cam_c) of pipeline/perc2.py (mono, 1600x1000).
"""
import os, json
import numpy as np, cv2, trimesh, torch

T3 = os.environ.get('T3', '/content/t3')
RSZ = (1600, 1000)


def rectification(calib_path=None):
    """perc2's rectification (left = ego_cam_c, right = ego_cam_b); returns (map_c, KR)."""
    C = json.load(open(calib_path or f'{T3}/calib.json')); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
    Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
    E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, (1280, 800), R, T, alpha=0, newImageSize=RSZ,
                                                flags=cv2.CALIB_ZERO_DISPARITY)
    MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
    return MC, P1[:3, :3].copy()


def rect_left_frames(ep, split='public', idx=None):
    """Grey rectified-left frames (uint8 1000x1600) of an episode, all or only those in idx."""
    MC, _ = rectification()
    vd = f'{T3}/v' if split == 'public' else f'{T3}/eval/v'
    cap = cv2.VideoCapture(f'{vd}/ep{ep}_c.mp4'); out = {}; i = 0
    want = None if idx is None else set(int(k) for k in idx)
    while True:
        ok, f = cap.read()
        if not ok: break
        if want is None or i in want:
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            out[i] = cv2.remap(g, MC[0], MC[1], cv2.INTER_LINEAR)
        i += 1
    return out


def load_points(mesh_path, n=400_000, seed=0):
    """Dense surface samples of the mesh: points (n,3), normals (n,3), grey albedo (n,) in [0,1]."""
    m = trimesh.load(mesh_path, force='mesh')
    rng = np.random.default_rng(seed)
    pts, fid = trimesh.sample.sample_surface(m, n, seed=int(rng.integers(1 << 30)))
    nrm = m.face_normals[fid]
    alb = np.full(n, 0.8)
    vc = getattr(m.visual, 'vertex_colors', None)
    if vc is not None and len(vc) == len(m.vertices):
        bary = trimesh.triangles.points_to_barycentric(m.triangles[fid], pts)
        c = (vc[m.faces[fid]][..., :3].astype(float) / 255 * bary[..., None]).sum(1)
        alb = c @ np.array([0.299, 0.587, 0.114])
        alb = np.clip(alb / max(np.percentile(alb, 95), 1e-3) * 0.9, 0, 1)    # white pot: scan colours run dark
    return pts.astype(np.float32), nrm.astype(np.float32), alb.astype(np.float32), m


def crop_K(K, cx, cy, side, out):
    """Intrinsics of the square crop [cx-side/2, cx+side/2] x [cy-side/2, ...] resized to out x out."""
    s = out / side
    Kc = K.copy().astype(np.float64)
    Kc[0, 0] *= s; Kc[1, 1] *= s
    Kc[0, 2] = (K[0, 2] - (cx - side / 2)) * s - 0.5 * (1 - s)
    Kc[1, 2] = (K[1, 2] - (cy - side / 2)) * s - 0.5 * (1 - s)
    return Kc


def crop_image(img, cx, cy, side, out, interp=cv2.INTER_LINEAR, border=0):
    """Crop matching crop_K (affine warp, pixel-centre exact)."""
    s = out / side
    A = np.array([[s, 0, -(cx - side / 2) * s - 0.5 * (1 - s)], [0, s, -(cy - side / 2) * s - 0.5 * (1 - s)]])
    return cv2.warpAffine(img, A, (out, out), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def project(K, T, P):
    q = P @ T[:3, :3].T + T[:3, 3]
    return np.c_[K[0, 0] * q[:, 0] / q[:, 2] + K[0, 2], K[1, 1] * q[:, 1] / q[:, 2] + K[1, 2]], q[:, 2]


def roi_from_pose(K, T, P, scale=1.3):
    """Square ROI (cx, cy, side) around the projected object."""
    uv, z = project(K, T, P)
    lo, hi = uv.min(0), uv.max(0)
    c = (lo + hi) / 2
    return float(c[0]), float(c[1]), float(max(hi - lo) * scale)


class Splat:
    """Point-splat renderer on torch (CPU or CUDA)."""
    def __init__(self, pts, nrm, alb, device='cpu'):
        self.P = torch.as_tensor(pts, device=device)
        self.N = torch.as_tensor(nrm, device=device)
        self.A = torch.as_tensor(alb, device=device)
        self.dev = device

    @torch.no_grad()
    def render(self, K, T, H, W, light=None):
        """One view. K (3,3), T (4,4) object->camera. Returns dict of numpy: depth (H,W, 0 = empty), xyz (H,W,3, object
        coords), mask (H,W bool), grey (H,W float, shaded albedo; 0 outside), normal_cam (H,W,3)."""
        d = self.dev
        K = torch.as_tensor(K, dtype=torch.float32, device=d); T = torch.as_tensor(T, dtype=torch.float32, device=d)
        R, t = T[:3, :3], T[:3, 3]
        q = self.P @ R.T + t
        n = self.N @ R.T
        z = q[:, 2]
        front = (z > 1e-3) & ((n * q).sum(1) < 0)            # facing the camera
        u = torch.round(K[0, 0] * q[:, 0] / z + K[0, 2]).long()
        v = torch.round(K[1, 1] * q[:, 1] / z + K[1, 2]).long()
        ok = front & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        idx = torch.nonzero(ok).squeeze(1)
        pix = v[idx] * W + u[idx]
        zb = torch.full((H * W,), float('inf'), device=d)
        zb.scatter_reduce_(0, pix, z[idx], reduce='amin')
        win = z[idx] <= zb[pix] + 1e-6
        idx, pix = idx[win], pix[win]
        owner = torch.full((H * W,), -1, dtype=torch.long, device=d)
        owner[pix] = idx
        owner = owner.view(H, W)
        # hole fill: empty pixels whose 3x3 neighbourhood has >= 5 filled take the nearest-depth neighbour
        own = owner.cpu().numpy() if d != 'cpu' else owner.numpy()
        filled = own >= 0
        if filled.any():
            zz = np.where(filled, (z.cpu().numpy() if d != 'cpu' else z.numpy())[np.maximum(own, 0)], np.inf)
            cnt = cv2.boxFilter(filled.astype(np.float32), -1, (3, 3), normalize=False)
            zmin = cv2.erode(zz.astype(np.float32), np.ones((3, 3), np.uint8))   # min over 3x3
            hole = (~filled) & (cnt >= 4)
            if hole.any():
                ys, xs = np.nonzero(hole)
                best = np.full(len(ys), -1); bz = np.full(len(ys), np.inf)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = np.clip(ys + dy, 0, H - 1), np.clip(xs + dx, 0, W - 1)
                        cz = zz[yy, xx]; better = cz < bz
                        bz[better] = cz[better]; best[better] = own[yy, xx][better]
                own[ys, xs] = best
        mask = own >= 0
        o = torch.as_tensor(np.maximum(own, 0), device=d)
        out = dict(mask=mask)
        Pq = self.P[o]; Nc = n[o]; Q = q[o]
        out['xyz'] = (Pq.cpu().numpy() * mask[..., None])
        out['depth'] = (Q[..., 2].cpu().numpy() * mask)
        out['normal_cam'] = Nc.cpu().numpy()
        alb = self.A[o]
        if light is None:
            light = dict(amb=0.5, dirs=[(np.array([0.3, 0.5, 1.0]), 0.6)], spec=0.0, shin=20.0)  # ldir: travel direction
        view = -Q / torch.linalg.norm(Q, dim=-1, keepdim=True)
        shade = torch.full_like(alb, float(light['amb']))
        sp = torch.zeros_like(alb)
        for ldir, k in light['dirs']:
            l = torch.as_tensor(-np.asarray(ldir, np.float32) / np.linalg.norm(ldir), device=d)  # towards the light
            ndl = (Nc * l).sum(-1)
            shade = shade + k * ndl.clamp(min=0)
            r = 2 * ndl[..., None] * Nc - l
            sp = sp + k * (r * view).sum(-1).clamp(min=0) ** float(light['shin'])
        g = alb * shade + float(light['spec']) * sp
        out['grey'] = (g.cpu().numpy() * mask)
        return out


def kabsch(A, B, w=None):
    """R, t minimising sum w |R A + t - B|^2 (A, B: (n,3))."""
    w = np.ones(len(A)) if w is None else w
    w = w / w.sum()
    ca, cb = (A * w[:, None]).sum(0), (B * w[:, None]).sum(0)
    H = ((A - ca) * w[:, None]).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def se3(R, t):
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t
    return T
