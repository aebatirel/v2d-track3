import numpy as np, sys, cv2
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c')
import real_ep11 as R, mc_spin as mc
from scipy.ndimage import minimum_filter
im = R.frame(0); G = R.gt(0); rv, tv, _ = R.cam_from_gt(im, G); Rc = cv2.Rodrigues(rv)[0]; tc = tv.ravel(); Ccam = -Rc.T @ tc
for n in ['blue_cup', 'beige_cup']:
    g_, tex = mc.load(n); P, _, _ = mc.sample(g_, tex, 300000, seed=5)
    up = np.array(mc.AX[n]['gt_up']); up /= np.linalg.norm(up); R0 = mc.Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix(); c0 = P.mean(0)
    Pu = (P - c0) @ R0.T; Mu = (mc.good_markers(n) - c0) @ R0.T
    C, th, g = R.upright_gauge(n, G[n], (c0, R0)); pos = Ccam - C
    X = mc.pose_pts(Pu, th, np.zeros(3), g); Mx = mc.pose_pts(Mu, th, np.zeros(3), g)
    for sub, mf in [(1, 1), (1, 3), (2, 3), (4, 3)]:
        K = mc.CAMS['a'][0].copy(); K[:2] /= sub; Wd, Ht = 2028 // sub, 1520 // sub
        uv, z = mc.project(X, Rc, pos, K); ui, vi = uv[:, 0].astype(int), uv[:, 1].astype(int); ok = (ui >= 0) & (ui < Wd) & (vi >= 0) & (vi < Ht)
        zb = np.full((Ht, Wd), np.inf); np.minimum.at(zb, (vi[ok], ui[ok]), z[ok]); zb = minimum_filter(zb, mf) if mf > 1 else zb
        um, zm = mc.project(Mx, Rc, pos, K); fr = []
        for k in range(len(Mx)):
            rp = max(1, int(round(K[0, 0] * 0.0073 / zm[k]))); yy, xx = np.mgrid[-rp:rp + 1, -rp:rp + 1]; m = xx ** 2 + yy ** 2 <= rp ** 2
            xs, ys = int(um[k, 0]) + xx[m], int(um[k, 1]) + yy[m]
            fr.append(round(float((zb[ys, xs] >= zm[k] - 0.0073 - 0.004).mean()), 2))
        print(n, 'sub', sub, 'minfilt', mf, 'disk free fraction per marker', fr, 'img', np.round(um * sub).astype(int).tolist())
