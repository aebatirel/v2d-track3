# Stage B1: automatic spoon marker detection (cam a, colour), 3-D sphere centres (cam a ray + b/c NCC depth sweep),
# table plane (b/c LK stereo), spoon wood mask (cam a) -> JSON per (episode, b-frame k). Cam a frame used = a[k+1]
# (Stage A pairing for all 10 spoon clips). No GT, no hand labels: thresholds are generic and fixed for all episodes.
# Usage: b_meas.py <ep> <k1,k2,...> [dbg]
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
SPL = 'public' if sys.argv[1].startswith('p') else 'evaluation'; TAG = sys.argv[1] if sys.argv[1][0] in 'pe' else 'e' + sys.argv[1]; ep = int(sys.argv[1].lstrip('pe')); ks = [int(x) for x in sys.argv[2].split(',')]; DBG = len(sys.argv) > 3
fa = read_frames(SPL, ep, 'a', [k + 1 for k in ks]); fb = read_frames(SPL, ep, 'b', ks); fc = read_frames(SPL, ep, 'c', ks)
# full chain cam a -> rectified-left (c) frame
R_a2c = R.T @ Rab; t_a2c = R.T @ (tab - T.ravel())          # X_c = R^T (X_b - T), X_b = Rab X_a + tab
R_a2r = R1 @ R_a2c; t_a2r = R1 @ t_a2c
A_centre_r = t_a2r                                           # cam a centre in rect frame


def a_ray_r(uv):
    d = undist_a_pts(uv) @ R_a2r.T; return d / np.linalg.norm(d, axis=1, keepdims=True)


def proj_rect(Xr, dy, which):
    """Rectified pixel of a rect-frame point in c (left) or b (right; includes per-episode dy)."""
    x = FR * Xr[..., 0] / Xr[..., 2] + CXR; y = FR * Xr[..., 1] / Xr[..., 2] + CYR
    if which == 'b': x = x - FR * BASE / Xr[..., 2]; y = y + dy
    return x, y


def patch(img, x, y, h):
    M = np.array([[1, 0, x - h], [0, 1, y - h]], np.float64)
    return cv2.warpAffine(img, M, (2 * h + 1, 2 * h + 1), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)


def ncc(p, q):
    p = p - p.mean(); q = q - q.mean(); return float((p * q).sum() / (np.sqrt((p * p).sum() * (q * q).sum()) + 1e-9))


def detect_a(img, whole=False):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); H, S, V = [hsv[..., i].astype(int) for i in range(3)]
    # table: saturated orange; hull of the largest component
    tab_m = ((S > 150) & (V > 90) & (H < 30)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(tab_m); j = 1 + np.argmax(st[1:, 4])
    cnt = cv2.findContours((lab == j).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    hull = np.zeros_like(tab_m); cv2.fillPoly(hull, [cv2.convexHull(np.vstack(cnt))], 1)
    near = cv2.dilate(hull, np.ones((81, 81), np.uint8)) if not whole else np.ones_like(hull)
    spoon = None
    grey = ((S < 45) & (V > 60) & (V < 235) & (near > 0)).astype(np.uint8)
    dark = ((V < 60) & (near > 0)).astype(np.uint8)
    grey = cv2.morphologyEx(grey, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(grey); cands = []
    darkd = cv2.dilate(dark, np.ones((9, 9), np.uint8))
    for i in range(1, n):
        a = st[i, 4]
        if a < 150 or a > 2500: continue
        m = (lab == i).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        cs = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]; c = max(cs, key=len).reshape(-1, 2).astype(float)
        # algebraic circle fit (Kasa) then 2 rounds of residual trimming
        keep = np.ones(len(c), bool)
        for _ in range(3):
            A = np.c_[2 * c[keep], np.ones(keep.sum())]; bb = (c[keep] ** 2).sum(1)
            sol = np.linalg.lstsq(A, bb, rcond=None)[0]; xc, yc = sol[:2]; r = np.sqrt(sol[2] + xc * xc + yc * yc)
            res = np.abs(np.linalg.norm(c - [xc, yc], axis=1) - r); keep = res < max(2.5 * np.median(res[keep]), 1.0)
        fill = a / (np.pi * r * r); dk = darkd[m > 0].mean()
        circ = 4 * np.pi * a / (cv2.arcLength(max(cs, key=len), True) ** 2)
        if 7 <= r <= 26 and fill > 0.55 and circ > 0.55 and dk > 0.05:
            cands.append(dict(uv=[float(xc), float(yc)], r=float(r), area=int(a), fill=float(fill), circ=float(circ),
                              dark=float(dk), rms=float(np.sqrt(np.mean(res[keep] ** 2)))))
    return hull, spoon, cands, (H, S, V)


LK = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))


def stereo_pts(rc, rb, dy, mask=None, nmax=4000, q=0.003):
    p = cv2.goodFeaturesToTrack(rc, nmax, q, 5, mask=mask, blockSize=7); init = p.copy(); init[:, 0, 0] -= 60
    pb, s1, _ = cv2.calcOpticalFlowPyrLK(rc, rb, p, init, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **LK)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(rb, rc, pb, None, **LK)
    q_, qb, qc = p.reshape(-1, 2), pb.reshape(-1, 2), pc.reshape(-1, 2)
    ok = (s1[:, 0] & s2[:, 0]).astype(bool) & (np.linalg.norm(qc - q_, axis=1) < 0.3) & (np.abs(qb[:, 1] - q_[:, 1] - dy) < 1.5) \
         & (q_[:, 0] - qb[:, 0] > 5)
    return tri_rect(q_[ok, 0], q_[ok, 1], qb[ok, 0], qb[ok, 1] - dy)


def in_hull(Xr, hull):
    Xa = (Xr - t_a2r) @ R_a2r; uva = proj_a(Xa).round().astype(int)
    ins = (uva[:, 0] >= 0) & (uva[:, 0] < 2028) & (uva[:, 1] >= 0) & (uva[:, 1] < 1520) & (Xa[:, 2] > 0)
    sel = np.zeros(len(Xr), bool); sel[ins] = hull[uva[ins, 1], uva[ins, 0]] > 0; return sel


def fit_plane(P, thr=0.003, it=500, seed=0):
    rng = np.random.default_rng(seed); best = None
    for _ in range(it):
        s3 = P[rng.choice(len(P), 3, replace=False)]; nrm = np.cross(s3[1] - s3[0], s3[2] - s3[0])
        if np.linalg.norm(nrm) < 1e-9: continue
        nrm /= np.linalg.norm(nrm); inl = np.abs((P - s3[0]) @ nrm) < thr
        if best is None or inl.sum() > best.sum(): best = inl
    Q = P[best]; cen = Q.mean(0); _, _, vt = np.linalg.svd(Q - cen); nrm = vt[2]
    if nrm @ (-cen) < 0: nrm = -nrm                                  # normal toward the cameras (up)
    return cen, nrm, best, float(np.sqrt(np.mean(((Q - cen) @ nrm) ** 2)))


def table_plane(rc, rb, dy, hull):
    """Dense table points: rough plane from corner matches, then SGBM disparities inside the table mask (rect c)."""
    X1 = stereo_pts(rc, rb, dy); er = cv2.erode(hull, np.ones((31, 31), np.uint8))
    cen, nrm, _, _ = fit_plane(X1[in_hull(X1, er)], thr=0.006)
    gy, gx = np.mgrid[0:RSZ[1]:4, 0:RSZ[0]:4]; d = np.stack([(gx - CXR) / FR, (gy - CYR) / FR, np.ones_like(gx, float)], -1).reshape(-1, 3)
    t = (cen @ nrm) / (d @ nrm); X = d * t[:, None]; ok = t > 0
    m = np.zeros(len(X), bool); m[ok] = in_hull(X[ok], er)
    mask = cv2.resize(m.reshape(gy.shape).astype(np.uint8), RSZ, interpolation=cv2.INTER_NEAREST)
    rbs = cv2.warpAffine(rb, np.float32([[1, 0, 0], [0, 1, -dy]]), RSZ, flags=cv2.INTER_LINEAR)
    sg = cv2.StereoSGBM_create(minDisparity=32, numDisparities=112, blockSize=9, P1=8 * 81, P2=32 * 81, disp12MaxDiff=1,
                               uniquenessRatio=10, speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_HH)
    disp = sg.compute(rc, rbs).astype(np.float32) / 16.0
    yy, xx = np.nonzero((mask > 0) & (disp > 32)); yy, xx = yy[::3], xx[::3]; dd = disp[yy, xx]
    return tri_rect(xx.astype(float), yy.astype(float), xx - dd, yy.astype(float)), disp


RDISC = 0.006
import os; HMAX = float(os.environ.get('HMAX', '0.060'))


def ncc_sweep(cd, rcf, rbf, dy, cen, nrm, h=9):
    d = a_ray_r(np.array([cd['uv']]))[0]
    # t where height above plane = hgt: (A + t d - cen).n = hgt
    tt = lambda hgt: (hgt - (A_centre_r - cen) @ nrm) / (d @ nrm)
    t0, t1 = sorted([tt(-0.010), tt(HMAX)]); ts = np.arange(t0, t1, 0.0002)
    X = A_centre_r[None] + ts[:, None] * d[None]
    xl, yl = proj_rect(X, dy, 'c'); xr, yr = proj_rect(X, dy, 'b')
    # disc-weighted NCC: sphere disc (radius RDISC at the hypothesised depth) with a 1.5 px Gaussian falloff (validated on p23)
    yy_, xx_ = np.mgrid[-h:h + 1, -h:h + 1]; sc = []
    for i in range(len(ts)):
        p_, q_ = patch(rcf, xl[i], yl[i], h), patch(rbf, xr[i], yr[i], h)
        w = np.exp(-0.5 * (np.maximum(np.hypot(xx_, yy_) - FR * RDISC / X[i, 2], 0) / 1.5) ** 2)
        p_ = p_ - (w * p_).sum() / w.sum(); q_ = q_ - (w * q_).sum() / w.sum()
        sc.append((w * p_ * q_).sum() / np.sqrt((w * p_ ** 2).sum() * (w * q_ ** 2).sum() + 1e-9))
    sc = np.array(sc)
    i = int(np.argmax(sc)); ii = np.clip([i - 1, i, i + 1], 0, len(ts) - 1); s3 = sc[ii]
    den = s3[0] - 2 * s3[1] + s3[2]; off = 0.5 * (s3[0] - s3[2]) / den if den < 0 else 0.0
    t = ts[i] + off * 0.0002; Xr = A_centre_r + t * d
    far = np.abs(ts - ts[i]) > 0.008; sc2 = sc[far].max() if far.any() else -1
    # curvature-based 1-sigma depth width (NCC drop of 0.02)
    w = np.abs(ts - ts[i])[sc > sc[i] - 0.02].max()
    return dict(X_r=Xr.tolist(), ncc=float(sc[i]), ncc2=float(sc2), xl=float(xl[i]), yl=float(yl[i]), disp=float(FR * BASE / Xr[2]),
                edge=bool(i in (0, len(ts) - 1)), wdepth_mm=float(w * 1e3))


EXP = np.array([55.0, 152.0, 192.0])   # note 13 model M1-M2, M2-M3, M1-M3 (mm), for triple ranking only


def pick_triple(cands):
    best = None; n = len(cands); P = [np.array(c['X_r']) * 1e3 for c in cands]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if len({i, j, k}) < 3 or i > j: continue
                d12 = np.linalg.norm(P[i] - P[j]); d1 = np.linalg.norm(P[i] - P[k]); d2 = np.linalg.norm(P[j] - P[k])
                if not (25 < d12 < 90 and 100 < min(d1, d2) and max(d1, d2) < 260): continue
                m1, m2 = (i, j) if d1 > d2 else (j, i)
                dd = np.array([d12, min(d1, d2), max(d1, d2)]); cost = np.abs(dd - EXP).sum() - 20 * sum(cands[x]['ncc'] for x in (i, j, k))
                if best is None or cost < best[0]: best = (cost, m1, m2, k, dd.tolist())
    return best


out = []
for k in ks:
    A = fa[k + 1]; gb = cv2.cvtColor(fb[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(fc[k], cv2.COLOR_BGR2GRAY)
    rc, rb, fdy, dinfo = rect_pair(gc, gb)          # b resampled by the local dy field -> residual dy = 0
    dy0, ndy, sdy = rect_dy(rc, rect(gb, 'b')); dy = 0.0
    hull, spoon, cands, (H, S, V) = detect_a(A)
    rcf, rbf = rc.astype(np.float32), rb.astype(np.float32)
    Xt, DISP = table_plane(rc, rb, dy, hull)
    cen, nrm, inl, rms = fit_plane(Xt)
    for cd in cands: cd.update(ncc_sweep(cd, rcf, rbf, dy, cen, nrm))
    tr = pick_triple([c for c in cands])
    rec = dict(ep=ep, k=k, ka=k + 1, dy=dy, dy_global=dy0, dy_field=dinfo, ndy=ndy, sdy=sdy, cands=cands, triple=tr, plane_g_c=cen.tolist(), plane_g_n=nrm.tolist(), plane_g_rms_mm=rms * 1e3)
    for cd in cands: cd['hg_mm'] = float((np.array(cd['X_r']) - cen) @ nrm * 1e3)
    if tr:
        M = np.array([cands[tr[x]]['X_r'] for x in (1, 2, 3)]); mc = M.mean(0)
        loc = np.linalg.norm(Xt - mc, axis=1) < 0.16
        cen, nrm, inl2, rms = fit_plane(Xt[loc], thr=0.003)
        rec.update(plane_c=cen.tolist(), plane_n=nrm.tolist(), plane_n_in=int(inl2.sum()), plane_n_pts=int(loc.sum()), plane_rms_mm=rms * 1e3,
                   M_r=M.tolist(), h_mm=((M - cen) @ nrm * 1e3).tolist())
    for cd in cands: cd['h_mm'] = float((np.array(cd['X_r']) - cen) @ nrm * 1e3)
    out.append(rec)
    if DBG: np.save(f'{OUT}/disp_{TAG}_k{k}.npy', DISP); json.dump(dict(c=cen.tolist(), n=nrm.tolist(), dy=dy), open(f'{OUT}/plane_{TAG}_k{k}.json', 'w'))
    print(f'{TAG} k{k}: dyg {dy0:+.2f} field rms {dinfo["rms"]:.2f} table pts {len(Xt)} local in {rec.get("plane_n_in")} rms {rms*1e3:.2f} mm | triple {tr} | h',
          np.round(rec.get('h_mm', []), 1), '|', ' '.join(f"({c['uv'][0]:.0f},{c['uv'][1]:.0f}) r{c['r']:.1f} ncc {c['ncc']:.2f}/{c['ncc2']:.2f} w{c['wdepth_mm']:.1f}{'E' if c['edge'] else ''} h {c['h_mm']:.1f}" for c in cands), flush=True)
    if DBG:
        im = A.copy()
        for c in cands: cv2.circle(im, (int(c['uv'][0]), int(c['uv'][1])), int(c['r']), (255, 0, 255), 1)
        cv2.imwrite(f'{OUT}/dbg_{TAG}_k{k}.jpg', im)
json.dump(out, open(f'{OUT}/meas_{TAG}.json', 'w'))
