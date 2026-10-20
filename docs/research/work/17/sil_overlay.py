"""Overlay GT-posed scan silhouettes (outline) + markers through a camera on cam a/b/c frames."""
import sys, json, numpy as np, cv2
import lib17 as L
ep, fr, src, c = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
gt = L.load_gt(ep)
if src == 's25': R, C = L.s25_cam(ep)
else:
    q = json.load(open(src))
    if 'Rwc' in q: R, C = np.array(q['Rwc']), np.array(q['C'])
    else: R, C = np.array(q['cams'][fr]['Rwc']), np.array(q['cams'][fr]['C'])
im = L.Video(ep, c).get(fr); H, W = im.shape[:2]
for j, n in enumerate(gt['names']):
    Xw = L.surf(n) @ gt['R'][fr, j].T + gt['t'][fr, j]; uv, z = L.project(Xw, R, C, c)
    m = np.zeros((H, W), np.uint8); u, v = uv[:, 0].astype(int), uv[:, 1].astype(int); k = (z > 0) & (u >= 0) & (u < W) & (v >= 0) & (v < H)
    m[v[k], u[k]] = 255; m = cv2.morphologyEx(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(im, cnts, -1, (0, 255, 0) if j == 0 else (255, 0, 255), 2 if c == 'a' else 1)
    Mw = L.markers_world(gt, fr, j); p, _ = L.project(Mw, R, C, c)
    for kk, (a, b) in enumerate(p): cv2.drawMarker(im, (int(a), int(b)), (0, 0, 255), cv2.MARKER_CROSS, 20 if c == 'a' else 10, 2 if c == 'a' else 1)
x0, y0, x1, y1 = [int(t) for t in sys.argv[5].split(',')] if len(sys.argv) > 5 else (0, 0, W, H)
cv2.imwrite(f'out/sil_{ep}_{fr}_{c}.jpg', im[y0:y1, x0:x1]); print('ok')
