"""Unrolled (theta, h) map of spin-specific colour detail on the outer wall (band-pass minus ring mean), x8 gain."""
import numpy as np, json, sys
from meshlib import *; from axis import cyl
from symm3 import bandpass, ring_remove
AX = json.load(open('out/axes2.json'))
for n in sys.argv[1:]:
    g, tex = load(n); P, C, N = sample(g, tex, 800000, seed=21)
    p, a = np.array(AX[n]['p']), np.array(AX[n]['a'])
    X = ring_remove(P, bandpass(P, C), p, a)
    th, h, r, _ = cyl(P, p, a)
    radial = (P - p) - np.outer(h, a); radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-12
    outer = (N * radial).sum(1) > 0.3
    nb_t, dh = 360, 0.002; hb = np.floor((h - h.min()) / dh).astype(int); tb = ((th + np.pi) / (2 * np.pi) * nb_t).astype(int) % nb_t
    H = hb.max() + 1; img = np.zeros((H, nb_t, 3)); cnt = np.zeros((H, nb_t)); col = np.zeros((H, nb_t, 3))
    m = outer; np.add.at(img, (hb[m], tb[m]), X[m]); np.add.at(col, (hb[m], tb[m]), C[m]); np.add.at(cnt, (hb[m], tb[m]), 1)
    img = img / np.maximum(cnt, 1)[..., None]; col = col / np.maximum(cnt, 1)[..., None]
    vis = np.clip(0.5 + 8 * img, 0, 1); vis[cnt == 0] = 0.5
    both = np.concatenate([col[::-1], np.full((4, nb_t, 3), 1.0), vis[::-1]], 0)
    save(np.repeat(np.repeat(both, 2, 0), 2, 1), f'out/{n}_aniso_unrolled.png')
    rms = np.sqrt((img[cnt > 0] ** 2).sum(-1).mean())
    print(n, 'outer-wall aniso rms per 1 deg x 2 mm cell %.4f (RGB 0-1)' % rms)
