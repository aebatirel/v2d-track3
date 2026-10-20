import sys, numpy as np, cv2
import lib17 as L, camfit as F
ep, fr = 12, 0
gt = L.load_gt(ep); R, C = L.s25_cam(ep)
for c in 'abc':
    G = F.gray(L.Video(ep, c).get(fr)); vis = L.visibility(gt, fr, R, C, c)
    for j, n in enumerate(gt['names']):
        for k in range(len(vis[j]['uv'])):
            uv = vis[j]['uv'][k]; rpx = vis[j]['rpx'][k]; s = rpx / np.sqrt(2)
            win = 60 if c == 'a' else 30
            x0, y0 = int(uv[0]) - win, int(uv[1]) - win
            if x0 < 0 or y0 < 0: continue
            P = G[y0:y0 + 2 * win, x0:x0 + 2 * win]
            resp = []
            for f in (1 / 1.5, 1.0, 1.5):
                B = cv2.GaussianBlur(P, (0, 0), s * f); resp.append(-cv2.Laplacian(B, cv2.CV_32F, ksize=3) * (s * f) ** 2)
            v, u = np.unravel_index(np.argmax(resp[1]), resp[1].shape)
            print(c, n[:6], k, 'vis %d frac %.2f rpx %.1f' % (vis[j]['vis'][k], vis[j]['frac'][k], rpx), 'max LoG %.3f at off (%d,%d), scales %.3f %.3f' % (resp[1].max(), u - win, v - win, resp[0][v, u], resp[2][v, u]))
