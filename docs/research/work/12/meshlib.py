"""Helpers: load scanned GLB, sample coloured surface points, splat-render."""
import numpy as np, trimesh
from PIL import Image
ROOT = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'

def load(name):
    s = trimesh.load(f'{ROOT}/{name}/{name}.glb')
    g = list(s.geometry.values())[0]
    tex = np.asarray(g.visual.material.baseColorTexture.convert('RGB')).astype(np.float32) / 255.
    return g, tex

def sample(g, tex, n=600000, seed=0):
    rng = np.random.default_rng(seed)
    area = g.area_faces
    fi = rng.choice(len(area), size=n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s1 = np.sqrt(r1)
    b = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
    tri = g.vertices[g.faces[fi]]           # n,3,3
    P = (b[:, :, None] * tri).sum(1)
    uvt = g.visual.uv[g.faces[fi]]
    uv = (b[:, :, None] * uvt).sum(1)
    H, W = tex.shape[:2]
    u = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1)
    v = np.clip((1 - (uv[:, 1] % 1.0)) * (H - 1), 0, H - 1)   # glTF uv origin top-left? test both
    C = tex[v.round().astype(int), u.round().astype(int)]
    N = g.face_normals[fi]
    return P, C, N

def splat(P, C, R, size=400, scale=None, center=None, bg=1.0, psize=1):
    """Orthographic render: camera looks along +z of rotated frame (P@R.T). Keeps nearest (max z toward viewer = smallest z)."""
    Q = P @ R.T
    if center is None: center = Q.mean(0)
    Q = Q - center
    if scale is None: scale = 0.45 * size / np.abs(Q[:, :2]).max()
    x = (Q[:, 0] * scale + size / 2).astype(int)
    y = (-Q[:, 1] * scale + size / 2).astype(int)
    ok = (x >= 0) & (x < size) & (y >= 0) & (y < size)
    x, y, z, c = x[ok], y[ok], Q[ok, 2], C[ok]
    order = np.argsort(-z)        # far first, near (small z... we view from -z side) last
    img = np.full((size, size, 3), bg, np.float32)
    for dx in range(psize):
        for dy in range(psize):
            xx = np.clip(x[order] + dx, 0, size - 1); yy = np.clip(y[order] + dy, 0, size - 1)
            img[yy, xx] = c[order]
    return img

def save(img, path):
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(path)

def rot(axis, ang):
    from scipy.spatial.transform import Rotation as Rr
    return Rr.from_rotvec(np.asarray(axis, float) / np.linalg.norm(axis) * ang).as_matrix()
