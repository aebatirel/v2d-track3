import numpy as np
from PIL import Image, ImageDraw
def lineplot(series, path, W=720, H=260, title='', ymax=None, xs=None):
    """series: list of (label, y, rgb). x = 0..359 by index spacing."""
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    L, R, T, B = 50, 10, 22, 25
    ys = np.concatenate([np.asarray(s[1], float) for s in series]); ys = ys[np.isfinite(ys)]
    ymax = ymax or ys.max() * 1.05
    d.rectangle([L, T, W - R, H - B], outline='black'); d.text((L, 4), title, fill='black')
    for t in range(0, 361, 45):
        x = L + (W - L - R) * t / 360; d.line([x, H - B, x, H - B + 4], fill='black'); d.text((x - 8, H - B + 6), str(t), fill='black')
    d.text((2, T), '%.3g' % ymax, fill='black'); d.text((2, H - B - 10), '0', fill='black')
    for k, (lab, y, c) in enumerate(series):
        y = np.asarray(y, float); n = len(y)
        x = np.arange(n) * 360 / n if xs is None else xs
        pts = [(L + (W - L - R) * xi / 360, T + (H - T - B) * (1 - yi / ymax)) for xi, yi in zip(x, y) if np.isfinite(yi)]
        d.line(pts, fill=c, width=2); d.text((W - 200, T + 4 + 12 * k), lab, fill=c)
    im.save(path)
