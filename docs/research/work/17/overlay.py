"""Overlay predicted markers (green visible / red occluded by z-buffer) on a frame, given a camera json or s25."""
import sys, json, numpy as np, cv2
import lib17 as L
ep, fr, src, c = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else 'a'
gt = L.load_gt(ep)
if src == 's25': R, C = L.s25_cam(ep)
else: q = json.load(open(src)); R, C = np.array(q['Rwc']), np.array(q['C'])
im = L.Video(ep, c).get(fr); vis = L.visibility(gt, fr, R, C, c)
for j, n in enumerate(gt['names']):
    for k, (u, v) in enumerate(vis[j]['uv']):
        if not np.isfinite(u): continue
        cv2.circle(im, (int(u), int(v)), max(int(vis[j]['rpx'][k]), 2), (0, 255, 0) if vis[j]['vis'][k] else (0, 0, 255), 2 if c == 'a' else 1)
        cv2.putText(im, f'{n[:4]}{k}', (int(u) + 12, int(v)), cv2.FONT_HERSHEY_SIMPLEX, 0.8 if c == 'a' else 0.4, (0, 255, 255), 2 if c == 'a' else 1)
out = sys.argv[5] if len(sys.argv) > 5 else f'out/ov_{ep}_{fr}_{c}.jpg'
cv2.imwrite(out, cv2.resize(im, None, fx=0.5, fy=0.5) if c == 'a' else im); print(out)
