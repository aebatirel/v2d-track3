import numpy as np, json
from meshlib import *; from axis import *
from scipy.ndimage import uniform_filter1d
out = {}
def unroll(name, a0, nb_t=360, dh=0.002, outer=True):
    g, tex = load(name); P, C, N = sample(g, tex, 1500000, seed=1)
    p, a, Cs = fit_axis(P, np.array(a0, float), p0=np.zeros(3))
    th, h, r, (e1, e2, a) = cyl(P, p, a)
    radial = (P - p) - np.outer(h, a); radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-12
    out_m = (N * radial).sum(1) > 0.2 if outer else np.ones(len(P), bool)
    hb = np.floor((h - h.min()) / dh).astype(int); nb_h = hb.max() + 1
    tb = ((th + np.pi) / (2 * np.pi) * nb_t).astype(int) % nb_t
    img = np.zeros((nb_h, nb_t, 3)); cnt = np.zeros((nb_h, nb_t)); rmax = np.full((nb_h, nb_t), np.nan)
    m = out_m
    np.add.at(img, (hb[m], tb[m]), C[m]); np.add.at(cnt, (hb[m], tb[m]), 1)
    rr = np.full((nb_h, nb_t), -1.0); np.maximum.at(rr, (hb[m], tb[m]), r[m])
    img = img / np.maximum(cnt, 1)[..., None]
    rr[cnt == 0] = np.nan
    return dict(P=P, C=C, N=N, p=p, a=a, e1=e1, e2=e2, th=th, h=h, r=r, img=img, cnt=cnt, rmax=rr, hmin=h.min())
if __name__ == '__main__':
    from PIL import Image
    for name in ['blue_cup', 'beige_cup']:
        U = unroll(name, [0, 0, 1])
        im = U['img']; im = np.clip(im / np.percentile(im[U['cnt'] > 0], 99), 0, 1)
        save(np.repeat(np.repeat(im, 2, 0), 2, 1), f'out/{name}_unrolled_colour.png')
        r = U['rmax']; prof = np.nanmedian(r, 1)
        dev = r - prof[:, None]
        dv = np.clip((dev + 0.002) / 0.016, 0, 1); dv[np.isnan(dv)] = 0
        save(np.repeat(np.repeat(np.stack([dv] * 3, -1), 2, 0), 2, 1), f'out/{name}_unrolled_radius.png')
        print(name, im.shape, 'max protrusion mm', np.nanmax(dev) * 1000)
