# Height-above-table map from the SGBM disparity (rect c view) for inspection.
import sys, json, cv2, numpy as np
sys.path.insert(0, '.'); from b_lib import *
ep, k = int(sys.argv[1]), int(sys.argv[2])
D_ = np.load(f'{OUT}/disp_e{ep}_k{k}.npy'); pl = json.load(open(f'{OUT}/plane_e{ep}_k{k}.json')); c, n = np.array(pl['c']), np.array(pl['n'])
yy, xx = np.mgrid[0:RSZ[1], 0:RSZ[0]]; ok = D_ > 32
X = tri_rect(xx[ok].astype(float), yy[ok].astype(float), xx[ok] - D_[ok], yy[ok].astype(float))
h = np.full(D_.shape, np.nan); h[ok] = (X - c) @ n * 1e3
m = json.load(open(f'{OUT}/meas_e{ep}.json'))[0]
pts = np.array([[cd['xl'], cd['yl']] for cd in m['cands']])
x0, y0 = pts.mean(0).astype(int); W = 260
sub = h[y0 - W:y0 + W, x0 - W:x0 + W]
vis = np.clip((sub + 5) / 40 * 255, 0, 255); vis[np.isnan(sub)] = 0
vis = cv2.applyColorMap(vis.astype(np.uint8), cv2.COLORMAP_JET); vis[np.isnan(sub)] = 0
for cd in m['cands']: cv2.circle(vis, (int(cd['xl'] - x0 + W), int(cd['yl'] - y0 + W)), 8, (255, 255, 255), 1)
cv2.imwrite(f'{OUT}/hmap_e{ep}_k{k}.png', vis)
# print a coarse profile of heights along rows through the middle
for r in range(-60, 61, 20):
    row = h[y0 + r, x0 - W:x0 + W:20]; print(r, ' '.join('  . ' if np.isnan(v) else f'{v:4.0f}' for v in row))
