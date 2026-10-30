"""ORACLE DISPLAY: frame-0 rectified (half-res) crop around the sweeper with our sweeper mask (yellow) and the rendered
visible silhouettes (z-buffered with the rack) of the sweeper at truth (green), P_s (magenta) and P_o (red, scan mesh at
X*_geom). Inputs: label maps written by f0render.py. Usage: python -I f0crop.py OUT_PNG"""
import sys, numpy as np, cv2
D = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
det = np.load(f'{D}/refine/in/ep31/det_f0.npz', allow_pickle=True)
img = cv2.cvtColor(det['image'], cv2.COLOR_GRAY2BGR)
masks = np.unpackbits(det['masks'], axis=-1)[:, :, :800].astype(np.uint8)
msw = masks[det['chosen'][0]]; mrk = masks[det['chosen'][1]]
lab = {k: np.load(f'{D}/leak/diag_31/f0render_{k}_lab.npy') for k in ('truth', 'Ps', 'Po_scanframe')}
ys, xs = np.where(lab['truth'] == 0); cy, cx = int(ys.mean()), int(xs.mean())
y0, y1, x0, x1 = max(0, cy - 70), cy + 70, max(0, cx - 90), cx + 90
def outline(m, col, im, th=1):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(im, cs, -1, col, th)
tiles = []
for title, layers in [('mask (yellow) + rack mask (cyan)', [(msw, (0, 255, 255)), (mrk, (255, 255, 0))]),
                      ('truth sweeper visible (green)', [(lab['truth'] == 0, (0, 220, 0)), (msw, (0, 255, 255))]),
                      ('P_s (magenta) vs truth (green)', [(lab['truth'] == 0, (0, 220, 0)), (lab['Ps'] == 0, (255, 0, 255))]),
                      ('P_o (red) vs truth (green)', [(lab['truth'] == 0, (0, 220, 0)), (lab['Po_scanframe'] == 0, (0, 0, 255))])]:
    im = img.copy()
    for m, col in layers:
        outline(m, col, im)
    c = cv2.resize(im[y0:y1, x0:x1], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.rectangle(c, (0, 0), (c.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(c, title, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(c)
top = np.hstack(tiles[:2]); bot = np.hstack(tiles[2:])
out = np.vstack([top, bot])
cv2.putText(out, 'ep31 f0 rectified (half res), public; ORACLE DIAGNOSTIC (truth = mocap mapped by the P_s rack fit)', (5, out.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
cv2.imwrite(sys.argv[1], out); print('wrote', sys.argv[1], out.shape)
