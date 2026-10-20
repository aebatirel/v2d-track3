import sys, numpy as np, cv2
import lib17 as L
ep, fr, c = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
gt = L.load_gt(ep); R, C = L.s25_cam(ep)
im = L.Video(ep, c).get(fr); G = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); vis = L.visibility(gt, fr, R, C, c)
win = 80 if c == 'a' else 40; tiles = []
for j, n in enumerate(gt['names']):
    for k in range(len(vis[j]['uv'])):
        u, v = vis[j]['uv'][k]; r = vis[j]['rpx'][k]
        x0, y0 = int(u) - win, int(v) - win
        if x0 < 0 or y0 < 0 or x0 + 2 * win > G.shape[1] or y0 + 2 * win > G.shape[0]: continue
        P = cv2.GaussianBlur(G[y0:y0 + 2 * win, x0:x0 + 2 * win], (0, 0), 1.0)
        cs = cv2.HoughCircles(P, cv2.HOUGH_GRADIENT_ALT, dp=1, minDist=max(r, 3), param1=60, param2=0.6, minRadius=max(int(0.7 * r), 2), maxRadius=int(1.35 * r) + 1)
        cs = [] if cs is None else cs[0]
        print(c, n[:6], k, 'rpx %.1f vis %.2f' % (r, vis[j]['frac'][k]), 'circles', [(round(a - win, 1), round(b - win, 1), round(rr, 1)) for a, b, rr in cs])
        t = cv2.cvtColor(P, cv2.COLOR_GRAY2BGR)
        for a, b, rr in cs: cv2.circle(t, (int(a), int(b)), int(rr), (0, 255, 0), 1)
        cv2.circle(t, (win, win), 2, (0, 0, 255), -1); cv2.putText(t, f'{n[:4]}{k}', (2, 12), 0, 0.4, (0, 255, 255), 1); tiles.append(t)
cv2.imwrite(f'out/hc_{ep}_{fr}_{c}.jpg', np.concatenate(tiles, 1))
