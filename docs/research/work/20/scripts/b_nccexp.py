# Experiment: marker depth estimator variants vs GT heights (public eps). Usage: b_nccexp.py p23 k
import sys, json, numpy as np, cv2
tag, kk = sys.argv[1], int(sys.argv[2]); sys.argv = ['x', tag, str(kk)]
exec(open('b_meas.py').read().split("out = []\nfor k in ks:")[0])


def sweep2(cd, rcf, rbf, dy, cen, nrm, h, disc=None):
    d = a_ray_r(np.array([cd['uv']]))[0]
    tt = lambda hgt: (hgt - (A_centre_r - cen) @ nrm) / (d @ nrm)
    t0, t1 = sorted([tt(-0.010), tt(0.060)]); ts = np.arange(t0, t1, 0.0002)
    X = A_centre_r[None] + ts[:, None] * d[None]; xl, yl = proj_rect(X, dy, 'c'); xr, yr = proj_rect(X, dy, 'b')
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    sc = []
    for i in range(len(ts)):
        p, q = patch(rcf, xl[i], yl[i], h), patch(rbf, xr[i], yr[i], h)
        if disc is not None:
            rp = FR * disc / X[i, 2]; w = np.exp(-0.5 * (np.maximum(np.hypot(xx, yy) - rp, 0) / 1.5) ** 2)
            pm, qm = (w * p).sum() / w.sum(), (w * q).sum() / w.sum(); p_, q_ = p - pm, q - qm
            sc.append((w * p_ * q_).sum() / np.sqrt((w * p_ ** 2).sum() * (w * q_ ** 2).sum() + 1e-9))
        else: sc.append(ncc(p, q))
    sc = np.array(sc); i = int(np.argmax(sc)); ii = np.clip([i - 1, i, i + 1], 0, len(ts) - 1); s3 = sc[ii]
    den = s3[0] - 2 * s3[1] + s3[2]; off = 0.5 * (s3[0] - s3[2]) / den if den < 0 else 0.0
    Xr = A_centre_r + (ts[i] + off * 0.0002) * d
    return float((Xr - cen) @ nrm * 1e3), float(sc[i])


rec = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r['k'] == kk][0]
k = kk; gb = cv2.cvtColor(fb[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(fc[k], cv2.COLOR_BGR2GRAY)
rc, rb = rect(gc, 'c'), rect(gb, 'b'); rcf, rbf = rc.astype(np.float32), rb.astype(np.float32)
cen, nrm, dy = np.array(rec['plane_g_c']), np.array(rec['plane_g_n']), rec['dy']
V = [('h10', 10, None), ('h7', 7, None), ('h5', 5, None), ('h4', 4, None), ('disc+0', 9, 0.0065), ('disc+2mm', 9, 0.0085), ('disc-1mm', 9, 0.0055)]
res = {}
for c in rec['cands']:
    if c['ncc'] < 0.8 or c['edge']: continue
    res[tuple(np.round(c['uv']).astype(int))] = [sweep2(c, rcf, rbf, dy, cen, nrm, h, dsc) for _, h, dsc in V]
json.dump({f'{u[0]},{u[1]}': v for u, v in res.items()}, open(f'{OUT}/nccexp_{tag}_k{kk}.json', 'w'))
print('variants', [v[0] for v in V])
for u, v in res.items(): print(u, ' '.join(f'{a:6.1f}/{b:.2f}' for a, b in v))
