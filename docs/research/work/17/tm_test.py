import sys, numpy as np, cv2, time
import lib17 as L, rend17 as RD, camfit as F
ep, fr = int(sys.argv[1]), int(sys.argv[2])
gt = L.load_gt(ep); R, C = L.s25_cam(ep); t0 = time.time()
for c in 'abc':
    G = F.gray(L.Video(ep, c).get(fr)); vis = L.visibility(gt, fr, R, C, c)
    for j, n in enumerate(gt['names']):
        for k in range(len(L.CAT[n])):
            r = RD.render_patch(n, k, gt['R'][fr, j], gt['t'][fr, j], R, C, c)
            if r is None: print(c, n[:6], k, 'no render'); continue
            x0, y0, T, Mk = r; win = 70 if c == 'a' else 35
            m = RD.match(G, x0, y0, T, Mk, win)
            print(c, n[:6], k, 'vis %.2f' % vis[j]['frac'][k], 'tmpl', T.shape, None if m is None else {a: round(b, 2) for a, b in m.items()})
            if c == 'a' and m is not None:
                cv2.imwrite(f'out/tm_{ep}_{n[:4]}{k}.png', np.concatenate([(T * 255).astype(np.uint8), (G[y0 + int(round(m["dy"])):y0 + int(round(m["dy"])) + T.shape[0], x0 + int(round(m["dx"])):x0 + int(round(m["dx"])) + T.shape[1]] * 255).astype(np.uint8)], 1))
print('time', time.time() - t0)
