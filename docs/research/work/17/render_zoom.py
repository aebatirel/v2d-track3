"""Zoomed orthographic splat renders of scan regions (to inspect candidate / missing markers)."""
import sys, json, numpy as np
from PIL import Image
from markers_cat import load, sample
def look(P, C, N, ctr, view, half=0.03, size=300):
    v = np.asarray(view, float); v /= np.linalg.norm(v)
    up = np.array([0, 0, 1.0]) if abs(v[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(up, v); x /= np.linalg.norm(x); y = np.cross(v, x)
    Q = P - ctr; m = (np.abs(Q @ x) < half) & (np.abs(Q @ y) < half) & (np.abs(Q @ v) < 0.08)
    Q, c = Q[m], C[m]
    u = ((Q @ x) / half * 0.5 + 0.5) * (size - 1); w = ((-(Q @ y)) / half * 0.5 + 0.5) * (size - 1); z = Q @ v
    o = np.argsort(z)  # far (small z along view toward viewer?) first
    img = np.ones((size, size, 3), np.float32)
    ui, wi = u[o].astype(int), w[o].astype(int)
    for dx in (0, 1):
        for dy in (0, 1):
            img[np.clip(wi + dy, 0, size - 1), np.clip(ui + dx, 0, size - 1)] = c[o]
    return img
if __name__ == '__main__':
    name = sys.argv[1]; pts = json.loads(sys.argv[2]); half = float(sys.argv[3]) if len(sys.argv) > 3 else 0.03
    g, tex = load(name); P, C, N, _ = sample(g, tex, 3_000_000, seed=1)
    cen = P.mean(0); tiles = []
    for p in pts:
        p = np.array(p) / 1000.0
        if len(pts[0]) == 6: view = p[3:] ; p = p[:3]
        else:
            k = np.linalg.norm(P - p, axis=1) < 0.006
            view = N[k].mean(0) * np.sign(np.mean(((P - cen) * N).sum(1))) if k.sum() > 10 else p - cen
        tiles.append(look(P, C, N, p, view, half))
    im = np.concatenate(tiles, 1)
    Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).save(f'out/zoom_{name}.png'); print('saved', im.shape)
