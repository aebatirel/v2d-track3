"""DIG 20 Stage C re-run: GT-FREE frame-0 slot-0 mask for the anchor-window detector (inference-safe).
b/c stereo at index 0 (rectified pair + dy field, SGBM) -> 3-D points; table plane by RANSAC (normal toward the camera
and image-up); above-table points over the table hull -> blobs; slot-0 blob chosen by a size/colour prior for the
slot-0 object NAME (public-GT prior table `prior_obj.json`, leave-own-episode-out); blob points projected into the D18
undistorted pinhole cam a at a[n] (n = Stage A pairing, a[n] ~ b[0]) and warped to a[0] by a whole-frame KLT homography.
Reads: videos, calibration, prior table, object name. No GT pose of the episode.
usage: r_mask.py <public|evaluation> <ep> [ep ...]  -> out/c2/mask_<p|e><ep>.png, .json, _dbg.jpg"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import b_lib as B
import c_lib as L
import c11
OUT2 = f'{L.ROOT}/work/20/out/c2'
PRI = json.load(open(f'{OUT2}/prior_obj.json'))
SYNC = json.load(open(f'{L.ROOT}/work/20/out/sync_table.json'))['episodes']
VALID = cv2.erode((B.rect(np.full((800, 1280), 255, np.uint8), 'c') > 0).astype(np.uint8), np.ones((17, 17), np.uint8))


def prior(name, excl):
    r = [x for x in PRI[name] if x['ep'] != excl] or PRI[name]
    ab = [x['ab'] for x in r if 'ab' in x]
    return dict(h=float(np.median([x['h'] for x in r])), l1=float(np.median([x['l1'] for x in r])),
                l2=float(np.median([x['l2'] for x in r])), ab=np.median(ab, 0) if ab else None)


def pairing0(key):
    return SYNC[key]['pairing_a_to_b'][0]['n'] if key in SYNC else 1


def stereo(split, ep, k=0):
    gc = cv2.cvtColor(B.read_frames(split, ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(B.read_frames(split, ep, 'b', [k])[k], cv2.COLOR_BGR2GRAY)
    rc, rbw, f, info = B.rect_pair(gc, gb)
    sg = cv2.StereoSGBM_create(minDisparity=24, numDisparities=160, blockSize=7, P1=8 * 49, P2=32 * 49, disp12MaxDiff=1,
                               uniquenessRatio=8, speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    disp = sg.compute(rc, rbw).astype(np.float32) / 16.0
    return rc, disp, info


def plane_ransac(X, rng, it=500, thr=0.006):
    best = (-10 ** 9, None); wA = X[:, 2] ** 2
    for _ in range(it):
        P = X[rng.choice(len(X), 3, replace=False)]
        n = np.cross(P[1] - P[0], P[2] - P[0]); nn = np.linalg.norm(n)
        if nn < 1e-9: continue
        n /= nn
        if n @ (-P[0]) < 0: n = -n                       # toward the camera
        if -n[1] < 0.3: continue                          # roughly image-up (y down): rejects walls
        dd = (X - P[0]) @ n
        # the table is the LOWEST large plane: penalise planes with many points just below them (e.g. a plane through
        # the front table and the tops of flat objects at the back, tilted by a few degrees)
        # area-weighted (pixel footprint ~ Z^2) so that a near flat face (an upside-down pot bottom close to the camera,
        # p27) cannot outvote the table
        cnt = float((wA * (np.abs(dd) < thr)).sum()) - 2 * float((wA * ((dd < -1.5 * thr) & (dd > -0.04))).sum())
        if cnt > best[0]: best = (cnt, (P[0], n))
    c, n = best[1]
    inl = np.abs((X - c) @ n) < thr
    cen = X[inl].mean(0); _, _, vt = np.linalg.svd(X[inl] - cen, full_matrices=False); n = vt[2]
    if n @ (-cen) < 0: n = -n
    return cen, n


def build(split, ep, dbg=True):
    key = f'{"p" if split == "public" else "e"}{ep}'
    name = L.slot0_name(ep) if split == 'public' else c11.EVAL[ep][0]
    pr = prior(name, ep if split == 'public' else None)
    rc, disp, info = stereo(split, ep, 0)
    H, W = disp.shape
    yy, xx = np.mgrid[0:H, 0:W]
    ok = (disp > 24.5) & (VALID > 0)
    X = np.full((H, W, 3), np.nan, np.float32)
    X[ok] = B.tri_rect(xx[ok].astype(float), yy[ok].astype(float), xx[ok] - disp[ok], yy[ok].astype(float))
    Z = X[..., 2]
    rng = np.random.default_rng(0)
    cand = ok & (Z < 0.85) & (yy > 0.3 * H)       # table candidates: near (the floor is >= ~1 m away)
    S = X[cand]; S = S[rng.choice(len(S), min(30000, len(S)), replace=False)]
    cen, n = plane_ransac(S, rng)
    hgt = np.where(ok, (X - cen) @ n, np.nan)
    # table support hull in plane coordinates
    e1 = np.cross(n, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    # table support: near-plane points (Z < 1.0 m), largest connected region of a 2 cm grid on the plane, then its hull
    tab = ok & (np.abs(hgt) < 0.006) & (Z < 1.0)
    T2 = np.c_[(X[tab] - cen) @ e1, (X[tab] - cen) @ e2].astype(np.float32)
    lo_t = T2.min(0); gt_ = np.floor((T2 - lo_t) / 0.02).astype(int); G = np.zeros(gt_.max(0)[::-1] + 1, np.int32)
    np.add.at(G, (gt_[:, 1], gt_[:, 0]), 1)
    G = cv2.morphologyEx((G >= 2).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    ng_, lg_, sg_, _ = cv2.connectedComponentsWithStats(G, connectivity=8)
    big = 1 + int(np.argmax(sg_[1:, cv2.CC_STAT_AREA]))
    keep = lg_[gt_[:, 1], gt_[:, 0]] == big; T2 = T2[keep]
    hull = cv2.convexHull(T2[rng.choice(len(T2), min(20000, len(T2)), replace=False)])
    obj = ok & (hgt > 0.012) & (hgt < 0.40) & (Z < 1.1)
    # objects = connected components of the above-table points' FOOTPRINT on the table plane (1 cm grid): objects that
    # touch in the image but stand apart on the table separate; sparse disparity on textureless faces does not fragment
    oy, ox = np.nonzero(obj)
    F2 = np.c_[(X[oy, ox] - cen) @ e1, (X[oy, ox] - cen) @ e2]
    CELL = 0.01; lo = np.minimum(F2.min(0), T2.min(0)) - 0.05; hi = np.maximum(F2.max(0), T2.max(0)) + 0.05
    GW, GH = (np.ceil((hi - lo) / CELL).astype(int) + 1)
    gi = np.floor((F2 - lo) / CELL).astype(int)
    hullg = np.zeros((GH, GW), np.uint8); hc = np.round((hull.reshape(-1, 2) - lo) / CELL).astype(np.int32)
    cv2.fillPoly(hullg, [hc], 1); hullg = cv2.dilate(hullg, np.ones((7, 7), np.uint8))   # +3 cm (overhangs)
    inside = hullg[gi[:, 1], gi[:, 0]] > 0
    occ = np.zeros((GH, GW), np.int32); np.add.at(occ, (gi[inside, 1], gi[inside, 0]), 1)
    occ = cv2.morphologyEx((occ >= 3).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    nlab, lg = cv2.connectedComponents(occ, connectivity=8)
    lab = np.zeros((H, W), np.int32); lab[oy[inside], ox[inside]] = lg[gi[inside, 1], gi[inside, 0]]
    area = np.bincount(lab.ravel(), minlength=nlab)
    if os.environ.get('RDBG'):
        v = np.clip(np.nan_to_num(hgt, nan=-1) / 0.2 * 255, 0, 255).astype(np.uint8); v = cv2.applyColorMap(v, cv2.COLORMAP_JET)
        v[~ok] = 0; v2 = cv2.applyColorMap((lab * 37 % 255).astype(np.uint8), cv2.COLORMAP_HSV); v2[lab == 0] = 0
        t3 = cv2.cvtColor((tab * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        cv2.imwrite(f'{OUT2}/dbg/hgt_{key}.jpg', np.hstack([cv2.resize(x, (640, 400)) for x in (v, v2, t3)]))
    # cam a frame a[n] for colour; the mask is built in a[n] and warped to a[0]
    npair = pairing0(key)
    FA = L.frames(split, ep, 'a', n_max=npair + 1)
    Ka = L.newK('a'); wa, ha, fa = L.NEW['a']
    labA = cv2.cvtColor(FA[npair], cv2.COLOR_BGR2LAB).astype(float)
    edge = (VALID == 0)
    edge = cv2.dilate(edge.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    blobs = []
    for i in range(1, nlab):
        if area[i] < 400: continue
        m = (lab == i) & ok & np.isfinite(hgt)
        P = X[m]; h = hgt[m]
        u = np.c_[(P - cen) @ e1, (P - cen) @ e2]
        uc = u - u.mean(0); _, _, vt = np.linalg.svd(uc, full_matrices=False); uu = uc @ vt.T
        ext = np.percentile(uu, 99, 0) - np.percentile(uu, 1, 0)
        h95 = float(np.percentile(h, 97))
        Pa = B.b_to_a(B.c_to_b(B.rect_to_c(P)))
        uv = Pa[:, :2] / Pa[:, 2:3] * fa + Ka[:2, 2]
        inA = (uv[:, 0] >= 0) & (uv[:, 0] < wa - 1) & (uv[:, 1] >= 0) & (uv[:, 1] < ha - 1)
        if inA.sum() < 50: continue
        q = uv[inA].astype(int)
        ab = np.median(labA[q[:, 1], q[:, 0], 1:], 0); Lm = float(np.median(labA[q[:, 1], q[:, 0], 0]))
        my, mx = np.nonzero(lab == i)
        bot = bool((edge[my, mx] & (my > 0.6 * H)).any()); side = bool((edge[my, mx] & (my <= 0.6 * H)).any())
        s_sz = abs(np.log(max(h95, 0.005) / pr['h'])) + abs(np.log(max(ext[0], 0.01) / pr['l1'])) + 0.5 * abs(np.log(max(ext[1], 0.005) / pr['l2']))
        s_col = (np.hypot(*(ab - pr['ab'])) / 12.0) if pr['ab'] is not None else 0.0
        s = s_sz + s_col + (1.0 if bot else 0.0) + (0.5 if side else 0.0)
        blobs.append(dict(i=i, area=int(area[i]), h=h95, l1=float(ext[0]), l2=float(ext[1]), ab=ab.tolist(), L=Lm,
                          bottom=bot, side=side, s_size=float(s_sz), s_col=float(s_col), score=float(s), zA=float(np.median(Pa[inA, 2])),
                          uv=uv[inA]))
    blobs.sort(key=lambda b: b['score'])
    meta = dict(split=split, ep=ep, name=name, prior=dict(h=pr['h'], l1=pr['l1'], l2=pr['l2'], ab=None if pr['ab'] is None else list(pr['ab'])),
                plane_n=n.tolist(), dy_info=dict(n=info['n'], rms=info['rms']), npair=npair,
                blobs=[{k: v for k, v in b.items() if k != 'uv'} for b in blobs])
    if not blobs:
        meta['empty'] = True; json.dump(meta, open(f'{OUT2}/mask_{key}.json', 'w'), indent=1, default=float); return meta
    b = blobs[0]
    Mn = np.zeros((ha, wa), np.uint8)
    for (x, y) in b['uv'].astype(int): cv2.circle(Mn, (int(x), int(y)), 3, 255, -1)
    Mn = cv2.morphologyEx(Mn, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    ff = Mn.copy(); cv2.floodFill(ff, None, (0, 0), 255); Mn = Mn | (255 - ff)          # fill holes
    # warp a[n] -> a[0] (whole-frame KLT homography)
    M0 = Mn
    if npair > 0:
        g0 = cv2.cvtColor(FA[0], cv2.COLOR_BGR2GRAY); gn = cv2.cvtColor(FA[npair], cv2.COLOR_BGR2GRAY)
        p = cv2.goodFeaturesToTrack(gn, 1500, 0.003, 8)
        q, s1, _ = cv2.calcOpticalFlowPyrLK(gn, g0, p, None, winSize=(21, 21), maxLevel=4)
        okk = s1[:, 0] == 1
        Hn, _ = cv2.findHomography(p[okk].reshape(-1, 2), q[okk].reshape(-1, 2), cv2.RANSAC, 2.0)
        M0 = cv2.warpPerspective(Mn, Hn, (wa, ha), flags=cv2.INTER_NEAREST)
        meta['warp_px'] = float(np.linalg.norm(cv2.perspectiveTransform(np.float32([[[wa / 2, ha / 2]]]), Hn)[0, 0] - [wa / 2, ha / 2]))
    meta['depth_m'] = b['zA']; meta['mask_area'] = int((M0 > 0).sum())
    cv2.imwrite(f'{OUT2}/mask_{key}.png', M0)
    if split == 'public' and ep in L.PUB:      # validation only: IoU vs the GT-rendered mask (D18 frame-0 camera)
        g = L.gt_ref(ep); R, C = L.cam0(ep); Mg, z = L.silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
        A, Bm = M0 > 0, Mg > 0
        meta['val'] = dict(iou=float((A & Bm).sum() / max((A | Bm).sum(), 1)), gt_depth=z,
                           cdist_px=float(np.linalg.norm(np.argwhere(A).mean(0) - np.argwhere(Bm).mean(0))) if A.any() else None)
    if dbg:
        o = FA[0].copy()
        for bb in blobs:
            c = (0, 255, 0) if bb is b else (0, 0, 255)
            for (x, y) in bb['uv'][::7].astype(int): o[y, x] = c
            x, y = bb['uv'].mean(0).astype(int); cv2.putText(o, f"{bb['score']:.2f} h{bb['h'] * 100:.0f} l{bb['l1'] * 100:.0f}", (x, y), 0, 0.45, c, 1)
        cnt, _ = cv2.findContours(M0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 255, 0), 2)
        if 'val' in meta:
            cnt, _ = cv2.findContours(Mg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 0, 255), 1)
        cv2.imwrite(f'{OUT2}/mask_{key}_dbg.jpg', cv2.resize(o, (676, 507)))
    json.dump(meta, open(f'{OUT2}/mask_{key}.json', 'w'), indent=1, default=float)
    return meta


if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        try:
            m = build(split, ep)
            b = m['blobs'][0] if m['blobs'] else {}
            print(f"{split[0]}{ep} {m['name']}: {len(m['blobs'])} blobs; pick score {b.get('score', np.nan):.2f} h {b.get('h', 0) * 100:.1f} "
                  f"l1 {b.get('l1', 0) * 100:.1f} l2 {b.get('l2', 0) * 100:.1f} cm ab {np.round(b.get('ab', [0, 0]), 0)} bot {b.get('bottom')} "
                  f"| prior h {m['prior']['h'] * 100:.1f} l1 {m['prior']['l1'] * 100:.1f} | depth {m.get('depth_m', np.nan):.2f} "
                  f"| val {m.get('val')}", flush=True)
        except Exception as ex:
            import traceback; traceback.print_exc(); print(f'{split[0]}{ep} FAILED {ex}', flush=True)
