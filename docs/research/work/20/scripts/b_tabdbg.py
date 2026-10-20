import sys, json, cv2, numpy as np
sys.argv = ['x', '37', '0']; exec(open('b_meas.py').read().split("out = []\nfor k in ks:")[0])
k = 0; A = fa[k + 1]; gb = cv2.cvtColor(fb[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(fc[k], cv2.COLOR_BGR2GRAY)
rc, rb = rect(gc, 'c'), rect(gb, 'b'); dy, _, _ = rect_dy(rc, rb)
hull, spoon, cands, _ = detect_a(A)
X1, _ = stereo_pts(rc, rb, dy); er = cv2.erode(hull, np.ones((31, 31), np.uint8)); sel = in_hull(X1, er)
print('pass1 pts', len(X1), 'in hull', sel.sum())
cen, nrm, inl, rms = fit_plane(X1[sel], thr=0.006); print('rough plane', cen, nrm, inl.sum(), rms)
gy, gx = np.mgrid[0:RSZ[1]:4, 0:RSZ[0]:4]; d = np.stack([(gx - CXR) / FR, (gy - CYR) / FR, np.ones_like(gx, float)], -1).reshape(-1, 3)
t = (cen @ nrm) / (d @ nrm); X = d * t[:, None]; ok = t > 0
m = np.zeros(len(X), bool); m[ok] = in_hull(X[ok], er); print('mask frac', m.mean())
mask = cv2.resize(m.reshape(gy.shape).astype(np.uint8), RSZ, interpolation=cv2.INTER_NEAREST)
cv2.imwrite(f'{OUT}/dbg_tabmask.jpg', cv2.resize(np.dstack([rc, rc, np.maximum(rc, mask * 255)]), None, fx=0.5, fy=0.5))
yy, xx = np.nonzero(mask[::6, ::6]); p = np.c_[xx * 6, yy * 6].astype(np.float32).reshape(-1, 1, 2)
t = (cen @ nrm) / (np.c_[(p[:, 0, 0] - CXR) / FR, (p[:, 0, 1] - CYR) / FR, np.ones(len(p))] @ nrm)
init = p.copy(); init[:, 0, 0] -= FR * BASE / t; init[:, 0, 1] += dy
for ws, lvl in ((31, 2), (31, 0), (21, 1), (41, 1)):
    lk = dict(winSize=(ws, ws), maxLevel=lvl, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.003))
    pb, s1, e1 = cv2.calcOpticalFlowPyrLK(rc, rb, p, init.copy(), flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(rb, rc, pb, p.copy(), flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    q_, qb, qc = p.reshape(-1, 2), pb.reshape(-1, 2), pc.reshape(-1, 2)
    fb_ = np.linalg.norm(qc - q_, axis=1); ddy = qb[:, 1] - q_[:, 1] - dy; dd = q_[:, 0] - qb[:, 0]
    st = (s1[:, 0] & s2[:, 0]).astype(bool)
    print(ws, lvl, 'n', len(p), 'status', st.mean().round(3), 'fb<0.15', (fb_ < 0.15).mean().round(3), 'fb<0.5', (fb_ < 0.5).mean().round(3),
          '|ddy|<1', (np.abs(ddy) < 1).mean().round(3), 'ddy pct', np.percentile(ddy[st], [10, 50, 90]).round(2),
          'disp-init', np.percentile((dd - (q_[:, 0] - init[:, 0, 0]))[st], [10, 50, 90]).round(2))
