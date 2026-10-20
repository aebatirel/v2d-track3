"""DIG 20 Stage C re-run: GT-FREE frame-0 slot-0 pose (x, y, yaw on the table) and mask by a 2.5-D template search.
Observed: b/c SGBM at index 0 -> table plane (RANSAC) -> per 1 cm cell of the table plane the 90th-percentile height of
the points whose foot falls in it (object cell), or 'table' (< 8 mm), or unknown.
Template: the slot-0 mesh in each public rest tilt of that object (public GT of OTHER episodes = prior), rotated by yaw
(5 deg steps); per cell the height of the VISIBLE surface (z-buffer along the camera->table view direction, so cup and
pot interiors look like the camera sees them). Score = mean over template cells of a height-agreement term
(1 - min(|dh| / tol, 2)) on object cells and -1 on table cells; then a colour tie-break (cam-a Lab of the rendered mask
vs the public colour prior) among the top peaks. The best pose's mesh silhouette is rendered into cam a at a[n]
(a[n] ~ b[0]) and warped to a[0]. Reads no GT of the episode (validation numbers are computed after, flagged 'val').
usage: r_pose0.py <public|evaluation> <ep> [ep ...] -> out/c2/pose0_<p|e><ep>.json, mask0_<p|e><ep>.png, _dbg.jpg"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import b_lib as B
import c_lib as L
import c11
from r_mask import stereo, plane_ransac, VALID, prior, pairing0, OUT2
from scipy.spatial.transform import Rotation as Rot
CELL = 0.01
CW = float(os.environ.get('CW', '0.01'))     # colour tie-break weight per Lab ab unit


def rest_tilts(name, excl):
    """distinct rest tilts (yaw removed) of the object at row 0 of public eps other than excl."""
    out = []
    for ep in L.PUB + [45]:
        if ep == excl: continue
        e = c11.load_episode(ep)
        if name not in e['names']: continue
        q = e['pose'][0, e['names'].index(name), 3:]
        if not np.isfinite(q).all(): continue
        psi = np.radians(c11.yaw_tilt(q, name)[0])
        Rt = Rot.from_euler('z', -psi).as_matrix() @ c11.R_of(q)
        if all(np.degrees(Rot.from_matrix(Rt @ r.T).magnitude()) > 15 for r, _ in out): out.append((Rt, ep))
    return out


def obs_grid(X, ok, hgt, cen, n, e1, e2, lo, shape):
    m = ok & np.isfinite(hgt) & (hgt > -0.01) & (hgt < 0.45) & (X[..., 2] < 1.1)
    P = X[m]; h = hgt[m]
    u = np.c_[(P - cen) @ e1, (P - cen) @ e2]
    gi = np.floor((u - lo) / CELL).astype(int); GH, GW = shape
    inb = (gi[:, 0] >= 0) & (gi[:, 0] < GW) & (gi[:, 1] >= 0) & (gi[:, 1] < GH)
    gi, h = gi[inb], h[inb]; cid = gi[:, 1] * GW + gi[:, 0]
    o = np.lexsort((h, cid)); cid, h = cid[o], h[o]
    uc, st, cnt = np.unique(cid, return_index=True, return_counts=True)
    q = h[st + np.floor(0.9 * (cnt - 1)).astype(int)]
    Ho = np.full(GH * GW, np.nan); C = np.zeros(GH * GW, int); Ho[uc] = q; C[uc] = cnt
    return Ho.reshape(GH, GW), C.reshape(GH, GW)


def template(Pobj, R, v, cell=CELL):
    """visible-surface height template of points Pobj (object frame) rotated by R (plane frame, z up), view dir v."""
    P = Pobj @ R.T; z0 = P[:, 2].min(); P[:, 2] -= z0
    a = np.cross(v, [0, 0, 1.0]); a /= np.linalg.norm(a); b = np.cross(v, a)
    pa = np.floor(np.c_[P @ a, P @ b] / 0.004).astype(int); d = P @ v
    key = (pa[:, 0] - pa[:, 0].min()) * 100000 + (pa[:, 1] - pa[:, 1].min())
    o = np.lexsort((d, key)); ks, st = np.unique(key[o], return_index=True)
    dmin = np.empty(len(P)); idx = np.searchsorted(ks, key); dmin = d[o][st][idx]
    vis = d <= dmin + 0.006
    lo = P[:, :2].min(0); gi = np.floor((P[:, :2] - lo) / cell).astype(int); GH, GW = gi[:, 1].max() + 1, gi[:, 0].max() + 1
    Ht = np.full((GH, GW), -1.0); np.maximum.at(Ht, (gi[vis, 1], gi[vis, 0]), P[vis, 2])
    return Ht, lo, z0


def build(split, ep, dbg=True):
    key = f'{"p" if split == "public" else "e"}{ep}'
    name = L.slot0_name(ep) if split == 'public' else c11.EVAL[ep][0]
    excl = ep if split == 'public' else None
    pr = prior(name, excl)
    rc, disp, info = stereo(split, ep, 0)
    H, W = disp.shape; yy, xx = np.mgrid[0:H, 0:W]
    ok = (disp > 24.5) & (VALID > 0)
    X = np.full((H, W, 3), np.nan, np.float32)
    X[ok] = B.tri_rect(xx[ok].astype(float), yy[ok].astype(float), xx[ok] - disp[ok], yy[ok].astype(float))
    Z = X[..., 2]; rng = np.random.default_rng(0)
    cand = ok & (Z < 0.85) & (yy > 0.3 * H)       # table candidates: near (the floor is >= ~1 m away)
    S_ = X[cand]; S_ = S_[rng.choice(len(S_), min(30000, len(S_)), replace=False)]
    cen, n = plane_ransac(S_, rng)
    hgt = np.where(ok, (X - cen) @ n, np.nan)
    e1 = np.cross(n, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1); E = np.c_[e1, e2, n]
    # local table level: robust quadratic surface h_t(u, v) over near-plane points (absorbs a slightly tilted/warped
    # stereo table of ~1 cm across the table, which matters for flat objects: planks 2 cm, dust pan 4.5 cm, spoon 3 cm)
    QF = os.environ.get('QFIT', '1') == '1'
    if QF:
        Uall = np.stack([(X[..., 0] - cen[0]) * e1[0] + (X[..., 1] - cen[1]) * e1[1] + (X[..., 2] - cen[2]) * e1[2],
                         (X[..., 0] - cen[0]) * e2[0] + (X[..., 1] - cen[1]) * e2[1] + (X[..., 2] - cen[2]) * e2[2]], -1)
        Af = lambda U: np.c_[np.ones(len(U)), U[:, 0], U[:, 1], U[:, 0] ** 2, U[:, 0] * U[:, 1], U[:, 1] ** 2]
        sel = ok & (np.abs(hgt) < 0.006) & (Z < 1.0)
        Us, hs = Uall[sel], hgt[sel]
        if len(hs) > 40000: ii = rng.choice(len(hs), 40000, replace=False); Us, hs = Us[ii], hs[ii]
        cf = np.zeros(6)
        for thr in (0.006, 0.004, 0.003):
            r = hs - Af(Us) @ cf; keep = np.abs(r) < thr
            cf = np.linalg.lstsq(Af(Us[keep]), hs[keep], rcond=None)[0]
        corr = np.full(hgt.shape, np.nan); corr[ok] = Af(Uall[ok]) @ cf
        hgt = np.where(ok, hgt - corr, np.nan)
        qfit_info = dict(coef=cf.tolist(), rms_mm=float(np.sqrt(np.mean((hs - Af(Us) @ cf)[np.abs(hs - Af(Us) @ cf) < 0.003] ** 2)) * 1000))
    else:
        qfit_info = None
    tab = ok & (np.abs(hgt) < 0.006) & (Z < 1.0)
    T2 = np.c_[(X[tab] - cen) @ e1, (X[tab] - cen) @ e2]
    lo_t = T2.min(0); g_ = np.floor((T2 - lo_t) / 0.02).astype(int); G = np.zeros(g_.max(0)[::-1] + 1, np.int32)
    np.add.at(G, (g_[:, 1], g_[:, 0]), 1)
    G = cv2.morphologyEx((G >= 2).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, lg_, sg_, _ = cv2.connectedComponentsWithStats(G, connectivity=8)
    T2 = T2[lg_[g_[:, 1], g_[:, 0]] == 1 + int(np.argmax(sg_[1:, cv2.CC_STAT_AREA]))]
    lo = T2.min(0) - 0.25; hi = T2.max(0) + 0.25
    shape = tuple((np.ceil((hi - lo) / CELL).astype(int) + 1)[::-1])
    Ho, Cn = obs_grid(X, ok, hgt, cen, n, e1, e2, lo, shape)
    known = Cn >= 2
    tabc = known & (Ho < 0.008); objc = known & (Ho >= 0.008)
    hull = cv2.convexHull(T2.astype(np.float32)); hg = np.zeros(shape, np.uint8)
    cv2.fillPoly(hg, [np.round((hull.reshape(-1, 2) - lo) / CELL).astype(np.int32)], 1)
    near = cv2.dilate(hg, np.ones((11, 11), np.uint8)) > 0          # table hull + 5 cm
    objc &= near
    # camera in plane coordinates and the view direction toward the table centre
    Cp = np.array([(-cen) @ e1, (-cen) @ e2, (-cen) @ n]); tc = np.r_[T2.mean(0), 0.0]
    v = tc - Cp; v /= np.linalg.norm(v)
    # templates
    Vm, Fm = L.mesh(name); Ps = c11.surface_points(name, 20000)
    others = (c11.load_episode(ep)['names'] if split == 'public' else c11.EVAL[ep])
    if name == 'white_pot' and 'white_pot_lid' in others:      # lid on the pot at frame 0 (pot-with-lid task): composite
        Rl = []
        for e2_ in L.PUB:
            if e2_ == excl: continue
            ee = c11.load_episode(e2_)
            if 'white_pot_lid' not in ee['names'] or 'white_pot' not in ee['names']: continue
            pp, pl = ee['pose'][0, ee['names'].index('white_pot')], ee['pose'][0, ee['names'].index('white_pot_lid')]
            Rp_, Rl_ = c11.R_of(pp[3:]), c11.R_of(pl[3:]); Rl.append((Rp_.T @ Rl_, Rp_.T @ (pl[:3] - pp[:3])))
        if Rl:
            Rrel, trel = Rl[0]
            Ps = np.r_[Ps, c11.surface_points('white_pot_lid', 8000) @ Rrel.T + trel]
            composite = 'pot+lid (relative pose from public ep, LOO)'
    tilts = rest_tilts(name, excl)
    composite = locals().get('composite')
    best = []
    Smax = np.full(shape, -9.0); Sarg = {}
    for ti, (Rt, tep) in enumerate(tilts):
        for yaw in range(0, 360, 5):
            R = Rot.from_euler('z', yaw, degrees=True).as_matrix() @ Rt
            Ht, tlo, zmin = template(Ps, R, v)
            valid = Ht >= 0
            if valid.sum() < 4: continue
            th, tw = Ht.shape
            if th >= shape[0] or tw >= shape[1]: continue
            Ssum = np.zeros((shape[0] - th + 1, shape[1] - tw + 1), np.float32)
            levels = np.unique(np.round(Ht[valid] / 0.01).astype(int))
            for k in levels:
                Tk = (valid & (np.round(Ht / 0.01).astype(int) == k)).astype(np.float32)
                hk = k * 0.01; tol = max(0.25 * hk, 0.012)
                dHk = np.nan_to_num(Ho) - hk
                # observed HIGHER than the template = something on top / in front (lid, pot in the rack, a hand): neutral;
                # observed lower (table or low surface where the object should be) = evidence against
                Wk = np.where(objc, np.where(dHk > tol, 0.0, 1 - np.minimum(np.abs(dHk) / tol, 2)), 0) - 1.0 * tabc
                if hk < 0.012: Wk = np.where(tabc, 0.3, Wk)               # flat template parts may sit on 'table' cells
                Ssum += cv2.matchTemplate(Wk.astype(np.float32), Tk, cv2.TM_CCORR)
            Ssum /= valid.sum()
            iy, ix = np.unravel_index(np.argmax(Ssum), Ssum.shape)
            best.append((float(Ssum[iy, ix]), ti, yaw, iy, ix, th, tw, tlo, zmin))
            # per-location max for peak listing (location = template centre)
            cy, cx = iy + th // 2, ix + tw // 2
            if Ssum[iy, ix] > Smax[cy, cx]: Smax[cy, cx] = Ssum[iy, ix]; Sarg[(cy, cx)] = best[-1]
            # also keep the best few other locations of this yaw
            S2 = Ssum.copy(); S2[max(iy - 6, 0):iy + 7, max(ix - 6, 0):ix + 7] = -9
            for _ in range(3):
                jy, jx = np.unravel_index(np.argmax(S2), S2.shape)
                if S2[jy, jx] < 0: break
                cy, cx = jy + th // 2, jx + tw // 2
                rec = (float(S2[jy, jx]), ti, yaw, jy, jx, th, tw, tlo, zmin)
                if S2[jy, jx] > Smax[cy, cx]: Smax[cy, cx] = S2[jy, jx]; Sarg[(cy, cx)] = rec
                S2[max(jy - 6, 0):jy + 7, max(jx - 6, 0):jx + 7] = -9
    if os.environ.get('RGT') and split == 'public':   # DEBUG (validation only): score of the GT pose under this model
        g = L.gt_ref(ep); Rw, Cw = L.cam0(ep); pg = g['e']['pose'][0, g['j']]
        def w2rect(Xw):
            Xa = (Xw - Cw) @ Rw; Xb = B.a_to_b(Xa); Xc = (Xb - B.T.ravel()) @ B.R; return B.c_to_rect(Xc)
        Rg_w = c11.R_of(pg[3:]); og = w2rect(pg[:3][None])[0]
        Rr = np.c_[[w2rect(pg[:3][None] + Rg_w[:, i][None])[0] - og for i in range(3)]].T     # columns = body axes in rect
        Rp = E.T @ Rr; op = E.T @ (og - cen)
        Ht, tlo, zmin = template(Ps, Rp, v); valid = Ht >= 0
        P2 = Ps @ Rp.T
        print('DEBUG GT body z-min in plane', float((P2[:, 2] + op[2]).min()), 'GT origin plane', op)
        ix, iy = np.round((op[:2] + tlo - lo) / CELL).astype(int)
        th, tw = Ht.shape; sc = 0.0
        for k in np.unique(np.round(Ht[valid] / 0.01).astype(int)):
            Tk = (valid & (np.round(Ht / 0.01).astype(int) == k)); hk = k * 0.01; tol = max(0.25 * hk, 0.012)
            Wk = np.where(objc, 1 - np.minimum(np.abs(np.nan_to_num(Ho) - hk) / tol, 2), 0) - 1.0 * tabc
            if hk < 0.012: Wk = np.where(tabc, 0.3, Wk)
            sc += float((Wk[iy:iy + th, ix:ix + tw] * Tk).sum())
        crop = np.nan_to_num(Ho[iy:iy + th, ix:ix + tw], nan=-0.05); crop[~known[iy:iy + th, ix:ix + tw]] = -0.05
        f = lambda A: cv2.resize(cv2.applyColorMap(np.clip((A + 0.05) / 0.3 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET), None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
        Htv = Ht.copy(); Htv[~valid] = -0.05
        cv2.imwrite(f'{OUT2}/dbg/gtcmp_{key}.png', np.hstack([f(crop), f(Htv)]))
        Pg = (Ps @ Rp.T) + op                       # GT body points in plane coords, directly
        gg = np.floor((Pg[:, :2] - lo) / CELL).astype(int)
        occ = np.zeros(shape, bool); occ[gg[:, 1].clip(0, shape[0] - 1), gg[:, 0].clip(0, shape[1] - 1)] = True
        print('DEBUG direct GT points: grid cols', gg[:, 0].min(), gg[:, 0].max(), 'rows', gg[:, 1].min(), gg[:, 1].max(),
              '| template placement cols', ix, ix + tw - 1, 'rows', iy, iy + th - 1)
        occ = np.zeros(shape, bool); occ[gg[:, 1].clip(0, shape[0] - 1), gg[:, 0].clip(0, shape[1] - 1)] = True
        mm_ = ok & np.isfinite(hgt); PP = X[mm_]; hh = hgt[mm_]
        uu = np.c_[(PP - cen) @ e1, (PP - cen) @ e2]; gq = np.floor((uu - lo) / CELL).astype(int)
        inn = (gq[:, 0] >= 0) & (gq[:, 0] < shape[1]) & (gq[:, 1] >= 0) & (gq[:, 1] < shape[0])
        fo = np.zeros(len(hh), bool); fo[inn] = occ[gq[inn, 1], gq[inn, 0]] if 'occ' in dir() else False
        ring = cv2.dilate(occ.astype(np.uint8), np.ones((15, 15), np.uint8)) > cv2.dilate(occ.astype(np.uint8), np.ones((5, 5), np.uint8))
        fr = np.zeros(len(hh), bool); fr[inn] = ring[gq[inn, 1], gq[inn, 0]]
        print('DEBUG heights (mm) of points in a 2-7 cm ring around the GT footprint: pct 10/50/90', np.percentile(hh[fr] * 1000, [10, 50, 90]), 'n', int(fr.sum()))
        allh = hh[(hh > -0.05) & (hh < 0.05)]; hist, edges = np.histogram(allh * 1000, bins=np.arange(-30, 31, 3)); print('DEBUG hist all near-plane heights', dict(zip(edges[:-1].astype(int).tolist(), hist.tolist())))
        print('DEBUG heights (mm) of points with feet in GT footprint: pct 10/50/90', np.percentile(hh[fo] * 1000, [10, 50, 90]) if fo.any() else None, 'n', int(fo.sum()))
        print('DEBUG frac of GT footprint cells observed as object', float((objc & occ).sum() / occ.sum()), 'as table', float((tabc & occ).sum() / occ.sum()))
        Hm = np.full(shape, -1.0); np.maximum.at(Hm, (gg[:, 1].clip(0, shape[0] - 1), gg[:, 0].clip(0, shape[1] - 1)), Pg[:, 2])
        cv2.imwrite(f'{OUT2}/dbg/gtcmp2_{key}.png', np.hstack([f(crop), f(Hm[iy:iy + th, ix:ix + tw]), f(Htv)]))
        for rr in range(iy, iy + th, 2):
            print('DEBUG ' + ''.join(('#' if occ[rr, cc] else '+') if objc[rr, cc] else ('o' if occ[rr, cc] else ('.' if tabc[rr, cc] else ' ')) for cc in range(ix - 5, ix + tw + 5)))
        for rr in range(0, th, 1):
            row = ''
            for cc in range(0, tw):
                if not valid[rr, cc]: row += '   '; continue
                gy, gx = iy + rr, ix + cc
                if not known[gy, gx]: row += '  ?'; continue
                row += f'{int(round((Ho[gy, gx] - Ht[rr, cc]) * 100)):+3d}'[-3:]
            print('DH ' + row)
        print('DEBUG Ht max', Ht.max(), 'Ho max in window', np.nanmax(Ho[iy:iy + th, ix:ix + tw]))
        b0 = max(best); Rb = Rot.from_euler('z', b0[2], degrees=True).as_matrix() @ tilts[b0[1]][0]
        Ht2, _, _ = template(Ps, Rb, v); v2 = Ht2 >= 0; jy, jx = b0[3], b0[4]
        print('DEBUG best placement rows', jy, 'cols', jx, 'vs GT', iy, ix)
        for rr in range(-2, Ht2.shape[0] + 2):
            row = ''
            for cc in range(-2, Ht2.shape[1] + 2):
                gy, gx = jy + rr, jx + cc
                inT = 0 <= rr < Ht2.shape[0] and 0 <= cc < Ht2.shape[1] and v2[rr, cc]
                if not known[gy, gx]: row += '  ?' if inT else '  .'; continue
                row += (f'{int(round((Ho[gy, gx] - Ht2[rr, cc]) * 100)):+3d}'[-3:]) if inT else f'{int(round(Ho[gy, gx] * 100)):3d}'[-3:].replace(' 0', ' _')
            print('DB ' + row)
        b0 = max(best)
        print(f'DEBUG GT-pose score {sc / valid.sum():.3f} at cell ({ix},{iy}); best found {b0[0]:.3f} at ({b0[4]},{b0[3]}) yaw {b0[2]} tilt {b0[1]}')
        tilt_gt = [np.degrees(Rot.from_matrix(Rp @ (Rot.from_euler('z', y, degrees=True).as_matrix() @ Rt).T).magnitude()) for Rt, _ in tilts for y in range(0, 360, 5)]
        print('DEBUG min angle GT vs any template rotation', min(tilt_gt))
    # peaks: distinct locations (>= 6 cm apart)
    cands = sorted(Sarg.values(), key=lambda r: -r[0]); peaks = []
    for r in cands:
        c = np.array([r[3] + r[5] / 2, r[4] + r[6] / 2])
        if all(np.linalg.norm(c - np.array([p[3] + p[5] / 2, p[4] + p[6] / 2])) > 6 for p in peaks): peaks.append(r)
        if len(peaks) >= int(os.environ.get("NPEAK", "8")): break
    npair = pairing0(key)
    FA = L.frames(split, ep, 'a', n_max=npair + 1)
    labA = cv2.cvtColor(FA[npair], cv2.COLOR_BGR2LAB).astype(float)
    Ka = L.newK('a'); wa, ha, fa = L.NEW['a']

    def render(r):
        s, ti, yaw, iy, ix, th, tw, tlo, zmin = r
        R = Rot.from_euler('z', yaw, degrees=True).as_matrix() @ tilts[ti][0]
        P = Vm @ R.T
        xy0 = lo + np.array([ix, iy]) * CELL - tlo                 # plane coords of the object origin
        Pp = P + np.r_[xy0, -zmin]
        Xr = cen + Pp @ E.T
        Xa = B.b_to_a(B.c_to_b(B.rect_to_c(Xr)))
        okz = Xa[:, 2] > 0.05
        uv = Xa[:, :2] / np.maximum(Xa[:, 2:3], 1e-3) * fa + Ka[:2, 2]
        M = np.zeros((ha, wa), np.uint8); good = okz[Fm].all(1)
        cv2.fillPoly(M, list(np.round(uv[Fm[good]] * 4).astype(np.int32)), 255, lineType=cv2.LINE_8, shift=2)
        org = B.b_to_a(B.c_to_b(B.rect_to_c((cen + np.r_[xy0, -zmin] @ E.T)[None])))[0]
        return M, float(np.median(Xa[okz, 2])), R, org
    rows = []
    for r in peaks:
        M, z, R, org = render(r)
        mm = cv2.erode(M, np.ones((7, 7), np.uint8)) > 0
        lab = labA[mm] if mm.sum() > 50 else labA[M > 0] if (M > 0).sum() else np.full((1, 3), 128.0)
        Lab = np.median(lab, 0)
        dcol = float(np.hypot(*(Lab[1:] - pr['ab']))) if pr['ab'] is not None else 0.0
        rows.append(dict(score=r[0], tilt=r[1], tilt_src_ep=tilts[r[1]][1], yaw=r[2], dcol=dcol, Lab=Lab.tolist(),
                         final=r[0] - CW * dcol, depth=z, org_a=org.tolist(), M=M, R=R))
    rows.sort(key=lambda d: -d['final'])
    side_rule = None
    TWIN = {'wooden_piece_1': ('wooden_piece_2', 'left'), 'wooden_piece_2': ('wooden_piece_1', 'right')}
    if os.environ.get('SIDE', '1') == '1' and name in TWIN and TWIN[name][0] in others:
        # twin planks: identical shape, colour too close. Staging prior (note 11 s2.2, public 23/24): piece_2 at +y =
        # image right of piece_1. Among peaks within 0.08 of the best that are >= 10 cm apart, take the left/right one.
        near = [d for d in rows if d['final'] >= rows[0]['final'] - 0.08]
        xs = [float(np.argwhere(d['M'] > 0)[:, 1].mean()) if (d['M'] > 0).any() else np.nan for d in near]
        if len(near) > 1 and np.nanmax(xs) - np.nanmin(xs) > 60:
            pick = near[int(np.nanargmin(xs) if TWIN[name][1] == 'left' else np.nanargmax(xs))]
            rows.remove(pick); rows.insert(0, pick); side_rule = dict(applied=True, side=TWIN[name][1], n_near=len(near))
    b = rows[0]; Mn = b['M']; M0 = Mn
    meta = dict(split=split, ep=ep, name=name, npair=npair, qfit=qfit_info, composite=locals().get('composite'), side_rule=side_rule, n_tilts=len(tilts), view_dir=v.tolist(), cam_h=float(Cp[2]),
                peaks=[{k: v_ for k, v_ in d.items() if k not in ('M', 'R')} for d in rows], depth_m=b['depth'])
    if npair > 0:
        g0 = cv2.cvtColor(FA[0], cv2.COLOR_BGR2GRAY); gn = cv2.cvtColor(FA[npair], cv2.COLOR_BGR2GRAY)
        p = cv2.goodFeaturesToTrack(gn, 1500, 0.003, 8)
        q, s1, _ = cv2.calcOpticalFlowPyrLK(gn, g0, p, None, winSize=(21, 21), maxLevel=4); k1 = s1[:, 0] == 1
        Hn, _ = cv2.findHomography(p[k1].reshape(-1, 2), q[k1].reshape(-1, 2), cv2.RANSAC, 2.0)
        M0 = cv2.warpPerspective(Mn, Hn, (wa, ha), flags=cv2.INTER_NEAREST)
        meta['warp_px'] = float(np.linalg.norm(cv2.perspectiveTransform(np.float32([[[wa / 2, ha / 2]]]), Hn)[0, 0] - [wa / 2, ha / 2]))
    cv2.imwrite(f'{OUT2}/mask0_{key}.png', M0)
    Mg = None
    if split == 'public' and ep in L.PUB:     # validation only (after inference): GT-rendered mask and GT origin in cam a
        g = L.gt_ref(ep); Rw, Cw = L.cam0(ep); Mg, zg = L.silhouette(g['name'], g['e']['pose'][0, g['j']], Rw, Cw)
        A_, Bm = M0 > 0, Mg > 0
        og = (g['e']['pose'][0, g['j'], :3] - Cw) @ Rw
        meta['val'] = dict(iou=float((A_ & Bm).sum() / max((A_ | Bm).sum(), 1)), gt_depth=zg,
                           cdist_px=float(np.linalg.norm(np.argwhere(A_).mean(0) - np.argwhere(Bm).mean(0))) if A_.any() else None,
                           org_err_cm=float(np.linalg.norm(np.array(b['org_a']) - og) * 100))
    if dbg:
        o = FA[0].copy()
        cnt, _ = cv2.findContours(M0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 255, 0), 2)
        for d in rows[1:]:
            cnt, _ = cv2.findContours(d['M'], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (0, 0, 255), 1)
        if Mg is not None:
            cnt, _ = cv2.findContours(Mg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 0, 255), 1)
        cv2.putText(o, f"{key} {name} s{b['score']:.2f} dcol{b['dcol']:.0f}", (10, 25), 0, 0.7, (255, 255, 0), 2)
        hv = np.clip(np.nan_to_num(Ho, nan=0) / 0.25 * 255, 0, 255).astype(np.uint8); hv = cv2.applyColorMap(hv, cv2.COLORMAP_JET)
        hv[~known] = 0; hv[tabc] = (60, 60, 60); hv = cv2.resize(hv, (int(hv.shape[1] * 380 / hv.shape[0]), 380), interpolation=cv2.INTER_NEAREST)
        o = cv2.resize(o, (507, 380))
        cv2.imwrite(f'{OUT2}/mask0_{key}_dbg.jpg', np.hstack([o, hv]))
    json.dump(meta, open(f'{OUT2}/pose0_{key}.json', 'w'), indent=1, default=float)
    return meta


if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        try:
            nm = L.slot0_name(ep) if split == 'public' else c11.EVAL[ep][0]
            if not os.path.exists(f'{c11.PUB}/mesh/{nm}'):      # no scan (wooden_spoon): blob fallback of r_mask.py
                import r_mask, shutil
                mb = r_mask.build(split, ep); key = f'{"p" if split == "public" else "e"}{ep}'
                shutil.copy(f'{OUT2}/mask_{key}.png', f'{OUT2}/mask0_{key}.png')
                mb['fallback'] = 'r_mask blob (no mesh)'; json.dump(mb, open(f'{OUT2}/pose0_{key}.json', 'w'), indent=1, default=float)
                b = mb['blobs'][0]
                print(f"{split[0]}{ep} {nm}: BLOB fallback, {len(mb['blobs'])} blobs; pick score {b['score']:.2f} h {b['h'] * 100:.1f} l1 {b['l1'] * 100:.1f} "
                      f"l2 {b['l2'] * 100:.1f} cm | depth {mb['depth_m']:.2f}", flush=True)
                continue
            m = build(split, ep)
            p = m['peaks']
            print(f"{split[0]}{ep} {m['name']}: tilts {m['n_tilts']} | " + ' ; '.join(f"s{d['score']:.2f} yaw{d['yaw']} dcol{d['dcol']:.0f} f{d['final']:.2f}" for d in p)
                  + f" | depth {m['depth_m']:.2f} | val {m.get('val')}", flush=True)
        except Exception as ex:
            import traceback; traceback.print_exc(); print(f'{split[0]}{ep} FAILED {ex}', flush=True)
