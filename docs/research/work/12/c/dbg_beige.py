import numpy as np, sys, cv2
sys.argv = ['x', '0', 'comb']
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c')
import real_ep11 as R, mc_spin as mc
im = R.frame(0); G = R.gt(0); rv, tv, _ = R.cam_from_gt(im, G); Rc = cv2.Rodrigues(rv)[0]; tc = tv.ravel(); Ccam = -Rc.T @ tc
n = 'beige_cup'; P, cR, Pu, Mu = R.setup2(n); T = mc.vis_table(Pu, Mu)
C, th, g = R.upright_gauge(n, G[n], cR); pos = Ccam - C
az = np.degrees(np.arctan2(pos[1], pos[0])); el = np.degrees(np.arcsin(pos[2] / np.linalg.norm(pos)))
print('az %.1f el %.1f th_gt %.1f' % (az, el, np.degrees(th)), 'vis table at gt:', mc.vis_lookup(T, az - np.degrees(th), el))
for dth in (0, -131, 120):
    t = th + np.radians(dth); X = mc.pose_pts(Mu, t, np.zeros(3), g); uv, _ = mc.project(X, Rc, pos, mc.CAMS['a'][0])
    print('branch %+d' % dth, 'vis', mc.vis_lookup(T, az - np.degrees(t), el).astype(int), 'proj (undist px)', np.round(uv).astype(int).tolist())
