"""Visual check: frame-0 slot-0 silhouette (D18 cam) over cam-a frames around the GT first perturbation.
usage: c_sheet.py <ep> ...  -> out/c/sheet_p<ep>.jpg  (analysis only)"""
import sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
os.makedirs(OUT, exist_ok=True)
for ep in map(int, sys.argv[1:]):
    g = gt_ref(ep); n0 = slot0_name(ep)
    assert n0 == g['name'], (n0, g['name'])
    R, C = cam0(ep)
    sil, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
    p = g['pert']; ks = sorted(set([0, max(p - 12, 0), max(p - 6, 0), max(p - 3, 0), p, min(p + 3, g['n'] - 1), min(g['on'], g['n'] - 1)]))
    F = frames('public', ep, 'a', n_max=max(ks) + 1)
    ys, xs = np.nonzero(sil); cx, cy = int(xs.mean()), int(ys.mean()); r = int(max(np.ptp(xs), np.ptp(ys)) * 0.9 + 60)
    x0, x1, y0, y1 = max(cx - r, 0), min(cx + r, 1014), max(cy - r, 0), min(cy + r, 760)
    cnt, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    tiles = []
    for k in ks:
        im = F[k].copy(); cv2.drawContours(im, cnt, -1, (0, 255, 0), 1)
        t = cv2.resize(im[y0:y1, x0:x1], (300, int(300 * (y1 - y0) / (x1 - x0))))
        cv2.putText(t, f'f{k} d{g["d"][k]:.1f}mm a{g["a"][k]:.1f}', (4, 16), 0, 0.45, (0, 0, 255), 1)
        tiles.append(t)
    full = cv2.resize(F[0], (300, 225)); cv2.drawContours(full, [ (c * 300 / 1014).astype(np.int32) for c in cnt], -1, (0, 255, 0), 1)
    hmax = max(t.shape[0] for t in tiles + [full])
    row = np.hstack([np.pad(t, ((0, hmax - t.shape[0]), (0, 0), (0, 0))) for t in [full] + tiles])
    cv2.imwrite(f'{OUT}/sheet_p{ep}.jpg', row)
    print(f'p{ep} {g["name"]} pert f{p} on f{g["on"]} n{g["n"]} depth {z:.2f} m bbox {xs.min()}-{xs.max()} x {ys.min()}-{ys.max()}', flush=True)
