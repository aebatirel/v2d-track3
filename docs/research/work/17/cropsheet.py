"""Full-res crops around predicted marker locations (green = visible by z-buffer, red = occluded)."""
import sys, json, numpy as np, cv2
import lib17 as L
ep, fr, src, c = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else 'a'
hw = int(sys.argv[5]) if len(sys.argv) > 5 else 90
gt = L.load_gt(ep)
if src == 's25': R, C = L.s25_cam(ep)
else: q = json.load(open(src)); R, C = np.array(q['Rwc']), np.array(q['C'])
im = L.Video(ep, c).get(fr); vis = L.visibility(gt, fr, R, C, c); H, W = im.shape[:2]
P = cv2.copyMakeBorder(im, hw, hw, hw, hw, cv2.BORDER_CONSTANT); tiles = []
for j, n in enumerate(gt['names']):
    for k, (u, v) in enumerate(vis[j]['uv']):
        if not (0 <= u < W and 0 <= v < H): continue
        cr = P[int(v):int(v) + 2 * hw, int(u):int(u) + 2 * hw].copy()
        cv2.circle(cr, (hw, hw), max(int(vis[j]['rpx'][k]), 2), (0, 255, 0) if vis[j]['vis'][k] else (0, 0, 255), 1)
        cv2.putText(cr, f'{n[:5]}{k}', (2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1); tiles.append(cr)
cv2.imwrite(f'out/cs_{ep}_{fr}_{c}.jpg', np.concatenate(tiles, 1)); print(len(tiles))
