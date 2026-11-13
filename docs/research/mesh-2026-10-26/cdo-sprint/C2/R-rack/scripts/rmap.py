#!/usr/bin/env python
"""C2 track R: raster maps (PIL, no matplotlib) of resid_diag.py point dumps in rack coordinates.

rmap.py DUMP.npz OUT.png --view xy|xh|yh [--color d|h|y|x] [--hlim lo,hi] [--xlim lo,hi] [--ylim lo,hi] [--eps 0,1]
          [--px 1.0] [--sel all|out|in|res]
Coordinates in mm. Colour: signed distance (blue inside, red outside, clipped +-12 mm) or a coordinate (viridis-like).
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw


def ramp(t):
    t = np.clip(t, 0, 1)
    r = np.clip(1.5 - np.abs(4 * t - 3), 0, 1); g = np.clip(1.5 - np.abs(4 * t - 2), 0, 1); b = np.clip(1.5 - np.abs(4 * t - 1), 0, 1)
    return (np.c_[r, g, b] * 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dump'); ap.add_argument('out'); ap.add_argument('--view', default='xy')
    ap.add_argument('--color', default='d'); ap.add_argument('--px', type=float, default=1.0)
    for k in ('xlim', 'ylim', 'hlim'):
        ap.add_argument('--' + k, default=None)
    ap.add_argument('--eps', default=None); ap.add_argument('--sel', default='all'); ap.add_argument('--thr', type=float, default=6)
    a = ap.parse_args()
    Z = np.load(a.dump)
    q = Z['q'].astype(np.float64) * 1e3; d = Z['d'] * 1e3; side = Z['side']; e = Z['e']
    sd = np.where(side, d, -d)
    m = np.ones(len(q), bool)
    for k, i in (('xlim', 0), ('ylim', 1), ('hlim', 2)):
        v = getattr(a, k)
        if v:
            lo, hi = map(float, v.split(','))
            m &= (q[:, i] >= lo) & (q[:, i] <= hi)
    if a.eps:
        m &= np.isin(e, [int(v) for v in a.eps.split(',')])
    if a.sel == 'out':
        m &= sd > a.thr
    elif a.sel == 'in':
        m &= sd < -a.thr
    elif a.sel == 'res':
        m &= np.abs(sd) > a.thr
    i, j = {'xy': (0, 1), 'xh': (0, 2), 'yh': (1, 2)}[a.view]
    Q = q[m]; S = sd[m]
    if a.color == 'd':
        col = np.zeros((len(Q), 3), np.uint8)
        t = np.clip(S / 12.0, -1, 1)
        col[:, 0] = (255 * np.clip(1 + np.minimum(t, 0), 0, 1)).astype(np.uint8)
        col[:, 2] = (255 * np.clip(1 - np.maximum(t, 0), 0, 1)).astype(np.uint8)
        col[:, 1] = (255 * (1 - np.abs(t))).astype(np.uint8)
    else:
        c = Q[:, {'x': 0, 'y': 1, 'h': 2}[a.color]]
        lo, hi = np.percentile(c, [1, 99])
        col = ramp((c - lo) / max(hi - lo, 1e-9))
    x0, x1 = Q[:, i].min() - 5, Q[:, i].max() + 5; y0, y1 = Q[:, j].min() - 5, Q[:, j].max() + 5
    W = int((x1 - x0) / a.px) + 1; H = int((y1 - y0) / a.px) + 1
    img = np.full((H, W, 3), 30, np.uint8)
    u = ((Q[:, i] - x0) / a.px).astype(int); v = (H - 1 - (Q[:, j] - y0) / a.px).astype(int)
    order = np.argsort(np.abs(S)) if a.color == 'd' else np.argsort(Q[:, 3 - i - j])
    img[v[order], u[order]] = col[order]
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    for g in range(int(np.ceil(x0 / 50)) * 50, int(x1), 50):
        uu = int((g - x0) / a.px); dr.line([(uu, 0), (uu, 6)], fill=(255, 255, 255)); dr.text((uu + 1, 7), str(g), fill=(200, 200, 200))
    for g in range(int(np.ceil(y0 / 10)) * 10, int(y1), 10):
        vv = int(H - 1 - (g - y0) / a.px); dr.line([(0, vv), (6, vv)], fill=(255, 255, 255))
        if g % 20 == 0:
            dr.text((8, vv - 5), str(g), fill=(200, 200, 200))
    im.save(a.out)
    print(a.out, im.size, int(m.sum()))


if __name__ == '__main__':
    main()
