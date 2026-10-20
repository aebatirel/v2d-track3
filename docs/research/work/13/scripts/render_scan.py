"""Painter's-algorithm orthographic render of a scan (texture colours sampled at face centroids)."""
import sys, numpy as np, trimesh
from PIL import Image, ImageDraw
MESH = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
def load(name):
    import os
    d = f"{MESH}/{name}"
    p = f"{d}/{name}_visual.glb" if os.path.exists(f"{d}/{name}_visual.glb") else f"{d}/{name}.glb"
    m = trimesh.load(p, force="mesh", process=False)
    return m
def face_colors(m):
    try:
        vis = m.visual
        uv = vis.uv
        img = vis.material.baseColorTexture if hasattr(vis.material, "baseColorTexture") else vis.material.image
        img = np.asarray(img.convert("RGB"))
        H, W = img.shape[:2]
        fuv = uv[m.faces].mean(1)
        x = np.clip((fuv[:, 0] % 1) * (W - 1), 0, W - 1).astype(int)
        y = np.clip((1 - fuv[:, 1] % 1) * (H - 1), 0, H - 1).astype(int)
        return img[y, x].astype(float)
    except Exception as e:
        print("no texture", e)
        return np.full((len(m.faces), 3), 200.0)
def render(m, view, size=700, out=None, shade=True, cols=None):
    V = np.asarray(m.vertices); F = np.asarray(m.faces)
    R = {"+x": np.array([[0,1,0],[0,0,1],[1,0,0]]), "-x": np.array([[0,-1,0],[0,0,1],[-1,0,0]]),
         "+y": np.array([[-1,0,0],[0,0,1],[0,1,0]]), "-y": np.array([[1,0,0],[0,0,1],[0,-1,0]]),
         "+z": np.array([[1,0,0],[0,1,0],[0,0,1]]), "-z": np.array([[1,0,0],[0,-1,0],[0,0,-1]])}[view]
    # rows: screen-right, screen-up, toward viewer (viewer looks from +axis toward origin)
    P = V @ R.T
    lo = P[:, :2].min(0); hi = P[:, :2].max(0); s = (size - 20) / (hi - lo).max()
    xy = (P[:, :2] - lo) * s + 10; xy[:, 1] = size - xy[:, 1]
    T = P[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    depth = T[:, :, 2].mean(1)
    order = np.argsort(depth)
    c = cols if cols is not None else face_colors(m)
    lam = 0.35 + 0.65 * np.abs(n[:, 2]) if shade else np.ones(len(F))
    im = Image.new("RGB", (size, size), (40, 40, 60)); dr = ImageDraw.Draw(im)
    for i in order:
        cc = tuple(int(v) for v in np.clip(c[i] * lam[i], 0, 255))
        dr.polygon([tuple(p) for p in xy[F[i]]], fill=cc)
    if out: im.save(out)
    return im
if __name__ == "__main__":
    name = sys.argv[1]; views = sys.argv[2].split(",")
    m = load(name); fc = face_colors(m)
    ims = [render(m, v, cols=fc) for v in views]
    W = sum(i.width for i in ims); H = ims[0].height
    canvas = Image.new("RGB", (W, H)); x = 0
    for i, v in zip(ims, views):
        ImageDraw.Draw(i).text((10, 10), f"{name} view from {v}", fill=(255, 255, 0)); canvas.paste(i, (x, 0)); x += i.width
    canvas.save(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/render/{name}_{'_'.join(views)}.jpg")
    print(len(m.faces), "faces")
