"""DIG 20 Stage C round 3: GT-FREE frame-0 mask for FLAT slot-0 objects (twin planks wooden_piece_1/2, wooden_spoon) by
2-D colour segmentation on the stereo table, instead of the height template (flat objects read only a few mm above the
stereo table, so r_pose0's height score cannot separate them).
Steps (inference reads video + calibration + object name + public mesh extents / note-13 spoon size only):
 1. b/c SGBM at index 0 -> table plane (r_mask.plane_ransac) -> table inliers (|h| < 6 mm), largest plane-grid component.
 2. Table inliers projected into the D18 pinhole cam a at a[n] (a[n] ~ b[0], Stage A pairing) -> convex hull = table
    region; eroded by ER px (rim excluded).
 3. 'object' = (bright and hue yellower than the orange table) OR (brighter than the local table median by > CON);
    open, close, fill holes. (A global Lab distance to the table median failed: table shading and the specular
    highlight dominate; see the round-3 notes.)
 4. Components inside the region -> metric footprint on the plane (pixels back-projected through cam a onto the plane):
    PCA extents l1 >= l2 (5-95 % range). Size score = |ln(l1/L1)| + |ln(l2/L2)| vs the expected footprint
    (planks 22.7 x 13.9 cm from the public mesh; spoon 30 x 5.2 cm from note 13).
 5. Pick: spoon = best size score; twin planks = among candidates with size score < 0.5 the left one for piece_1 and the
    right one for piece_2 (staging side rule, note 11 s2.2, derived from public 23/24 = in-sample).
 6. Mask warped a[n] -> a[0] by a whole-frame KLT homography. Depth = median cam-a Z of the footprint.
 Ego-arm rejection: a component touching the image bottom border is an ego arm and is never a candidate.
usage: r3_flat.py <public|evaluation> <ep> [ep ...] -> out/c3/mask0_<key>.png, pose0_<key>.json, _dbg.jpg"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import b_lib as B
import c_lib as L
import c11
from r_mask import stereo, plane_ransac, VALID, pairing0
O3 = f'{L.ROOT}/work/20/out/c3'
EXPECT = {'wooden_piece_1': (0.227, 0.139), 'wooden_piece_2': (0.227, 0.139), 'wooden_spoon': (0.30, 0.052)}
TWIN = {'wooden_piece_1': ('wooden_piece_2', 'left'), 'wooden_piece_2': ('wooden_piece_1', 'right')}
TAU = 50.0; ER = int(os.environ.get('ER', '9')); WIN = int(os.environ.get('WIN', '101')); CON = float(os.environ.get('CON', '35'))


def to_a(Xr):
    return B.b_to_a(B.c_to_b(B.rect_to_c(Xr)))


def build(split, ep, name=None, others=None, dbg=True):
    key = f'{"p" if split == "public" else "e"}{ep}'
    if name is None: name = L.slot0_name(ep) if split == 'public' else c11.EVAL[ep][0]
    if others is None: others = c11.load_episode(ep)['names'] if split == 'public' else c11.EVAL[ep]
    rc, disp, info = stereo(split, ep, 0)
    H, W = disp.shape; yy, xx = np.mgrid[0:H, 0:W]
    ok = (disp > 24.5) & (VALID > 0)
    X = np.full((H, W, 3), np.nan, np.float32)
    X[ok] = B.tri_rect(xx[ok].astype(float), yy[ok].astype(float), xx[ok] - disp[ok], yy[ok].astype(float))
    Z = X[..., 2]; rng = np.random.default_rng(0)
    cand = ok & (Z < 0.85) & (yy > 0.3 * H)
    S_ = X[cand]; S_ = S_[rng.choice(len(S_), min(30000, len(S_)), replace=False)]
    cen, n = plane_ransac(S_, rng)
    hgt = np.where(ok, (X - cen) @ n, np.nan)
    e1 = np.cross(n, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    tab = ok & (np.abs(hgt) < 0.006) & (Z < 1.0)
    T3 = X[tab]; T2 = np.c_[(T3 - cen) @ e1, (T3 - cen) @ e2]
    lo_t = T2.min(0); g_ = np.floor((T2 - lo_t) / 0.02).astype(int); G = np.zeros(g_.max(0)[::-1] + 1, np.int32)
    np.add.at(G, (g_[:, 1], g_[:, 0]), 1)
    G = cv2.morphologyEx((G >= 2).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    _, lg_, sg_, _ = cv2.connectedComponentsWithStats(G, connectivity=8)
    T3 = T3[lg_[g_[:, 1], g_[:, 0]] == 1 + int(np.argmax(sg_[1:, cv2.CC_STAT_AREA]))]
    # plane and table region in cam a
    Ka = L.newK('a'); wa, ha, fa = L.NEW['a']
    ca = to_a(cen[None])[0]; na = to_a((cen + n)[None])[0] - ca; na /= np.linalg.norm(na)
    e1a = to_a((cen + e1)[None])[0] - ca; e2a = to_a((cen + e2)[None])[0] - ca
    Ta = to_a(T3); Ta = Ta[Ta[:, 2] > 0.1]
    uv = Ta[:, :2] / Ta[:, 2:3] * fa + Ka[:2, 2]
    inb = (uv[:, 0] >= 0) & (uv[:, 0] < wa) & (uv[:, 1] >= 0) & (uv[:, 1] < ha)
    hull = cv2.convexHull(uv[inb].astype(np.float32))
    Tm = np.zeros((ha, wa), np.uint8); cv2.fillPoly(Tm, [np.round(hull.reshape(-1, 2)).astype(np.int32)], 255)
    Tme = cv2.erode(Tm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ER + 1,) * 2))
    npair = pairing0(key)
    FA = L.frames(split, ep, 'a', n_max=npair + 1)
    I = FA[npair]; lab = cv2.cvtColor(I, cv2.COLOR_BGR2LAB).astype(np.float32)
    tl = np.median(lab[Tme > 0], 0)
    # object cue (design from public 23/24 + the look of the table): (a) hue clearly yellower than the orange table and
    # bright (planks; L > 160, hue angle atan2(a*, b*) < 18 deg, chroma > 6); (b) brighter than the LOCAL table by > CON
    # (median over WIN px; catches the pale spoon whose hue equals the table's, but not the broad specular highlight)
    aa = lab[..., 1] - 128; bb = lab[..., 2] - 128
    hue_obj = (lab[..., 0] > 160) & (np.degrees(np.arctan2(aa, bb)) < 18) & (np.hypot(aa, bb) > 6)
    Lm = cv2.medianBlur(lab[..., 0].astype(np.uint8), WIN).astype(np.float32)
    con_obj = (lab[..., 0] - Lm) > CON
    d = (hue_obj | con_obj).astype(np.float32) * 100
    obj = ((d > 50) & (Tme > 0)).astype(np.uint8)
    obj = cv2.morphologyEx(obj, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    obj = cv2.morphologyEx(obj, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    # fill holes (marker bases, slots)
    ff = obj.copy(); m2 = np.zeros((ha + 2, wa + 2), np.uint8); cv2.floodFill(ff, m2, (0, 0), 1)
    obj = obj | (1 - ff)
    # ego-arm rejection: anything 'object-coloured' connected (through the full frame) to the bottom border
    full = ((d > 50)).astype(np.uint8)
    full = cv2.morphologyEx(full, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nF, labF, _, _ = cv2.connectedComponentsWithStats(full, connectivity=8)
    bottom_ids = set(np.unique(labF[-3:, :])) - {0}
    ncc, lab_, st, _ = cv2.connectedComponentsWithStats(obj, connectivity=8)
    L1, L2 = EXPECT[name]
    cands = []
    for i in range(1, ncc):
        if st[i, cv2.CC_STAT_AREA] < 150: continue
        comp = lab_ == i
        ys, xs = np.nonzero(comp)
        ego = len(set(np.unique(labF[comp])) & bottom_ids) > 0 and (full[comp].mean() > 0.5)
        rays = np.c_[(xs - Ka[0, 2]) / fa, (ys - Ka[1, 2]) / fa, np.ones(len(xs))]
        t = (na @ ca) / (rays @ na); P = rays * t[:, None]
        U = np.c_[(P - ca) @ e1a, (P - ca) @ e2a]
        Uc = U - np.median(U, 0); w_, v_ = np.linalg.eigh(np.cov(Uc.T)); pc1 = v_[:, 1]; pc2 = v_[:, 0]
        a1, a2 = Uc @ pc1, Uc @ pc2
        l1 = float(np.percentile(a1, 97.5) - np.percentile(a1, 2.5)); l2 = float(np.percentile(a2, 97.5) - np.percentile(a2, 2.5))
        sz = abs(np.log(max(l1, 1e-3) / L1)) + abs(np.log(max(l2, 1e-3) / L2))
        cands.append(dict(i=i, area=int(st[i, cv2.CC_STAT_AREA]), cx=float(xs.mean()), cy=float(ys.mean()), l1=l1, l2=l2,
                          size_score=float(sz), ego=bool(ego), depth=float(np.median(P[:, 2])),
                          Lab=np.median(lab[comp], 0).tolist()))
    cands.sort(key=lambda c: c['size_score'])
    good = [c for c in cands if not c['ego'] and c['size_score'] < 0.5]
    pick = None; rule = None
    if name in TWIN and TWIN[name][0] in others and len(good) >= 2:
        g2 = sorted(good[:2], key=lambda c: c['cx'])
        pick = g2[0] if TWIN[name][1] == 'left' else g2[-1]; rule = f'side:{TWIN[name][1]} of {len(good)}'
    elif good:
        pick = good[0]; rule = 'best size'
    elif [c for c in cands if not c['ego']]:
        pick = [c for c in cands if not c['ego']][0]; rule = 'best size (no candidate < 0.5: LOW CONFIDENCE)'
    Mn = np.zeros((ha, wa), np.uint8)
    if pick is not None: Mn[lab_ == pick['i']] = 255
    M0 = Mn; warp = 0.0
    if npair > 0:
        g0 = cv2.cvtColor(FA[0], cv2.COLOR_BGR2GRAY); gn = cv2.cvtColor(FA[npair], cv2.COLOR_BGR2GRAY)
        p = cv2.goodFeaturesToTrack(gn, 1500, 0.003, 8)
        q, s1, _ = cv2.calcOpticalFlowPyrLK(gn, g0, p, None, winSize=(21, 21), maxLevel=4); k1 = s1[:, 0] == 1
        Hn, _ = cv2.findHomography(p[k1].reshape(-1, 2), q[k1].reshape(-1, 2), cv2.RANSAC, 2.0)
        M0 = cv2.warpPerspective(Mn, Hn, (wa, ha), flags=cv2.INTER_NEAREST)
        warp = float(np.linalg.norm(cv2.perspectiveTransform(np.float32([[[wa / 2, ha / 2]]]), Hn)[0, 0] - [wa / 2, ha / 2]))
    os.makedirs(O3, exist_ok=True)
    cv2.imwrite(f'{O3}/mask0_{key}.png', M0)
    meta = dict(split=split, ep=ep, name=name, npair=npair, table_Lab=tl.tolist(), tau=TAU, rule=rule,
                pick={k: v for k, v in pick.items() if k != 'i'} if pick else None,
                cands=[{k: v for k, v in c.items() if k != 'i'} for c in cands], depth_m=pick['depth'] if pick else None, warp_px=warp)
    if split == 'public' and ep in L.PUB:   # validation only (after inference)
        g = L.gt_ref(ep); Rw, Cw = L.cam0(ep); Mg, zg = L.silhouette(g['name'], g['e']['pose'][0, g['j']], Rw, Cw)
        A_, Bm = M0 > 0, Mg > 0
        meta['val'] = dict(iou=float((A_ & Bm).sum() / max((A_ | Bm).sum(), 1)), gt_depth=zg,
                           cdist_px=float(np.linalg.norm(np.argwhere(A_).mean(0) - np.argwhere(Bm).mean(0))) if A_.any() else None)
    else:
        Mg = None
    if dbg:
        o = FA[0].copy()
        cnt, _ = cv2.findContours(Tme, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (0, 255, 0), 1)
        for c in cands:
            col = (0, 0, 255) if c['ego'] else (255, 0, 0)
            cv2.putText(o, f"{c['size_score']:.2f}", (int(c['cx']), int(c['cy'])), 0, 0.5, col, 1)
        cnt, _ = cv2.findContours(M0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 255, 0), 2)
        if Mg is not None:
            cnt, _ = cv2.findContours(Mg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (255, 0, 255), 1)
        ov = cv2.cvtColor((obj * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        cv2.putText(o, f"{key} {name} {rule}", (10, 25), 0, 0.6, (0, 255, 255), 2)
        cv2.imwrite(f'{O3}/mask0_{key}_dbg.jpg', np.hstack([cv2.resize(o, (507, 380)), cv2.resize(ov, (507, 380))]))
    json.dump(meta, open(f'{O3}/pose0_{key}.json', 'w'), indent=1, default=float)
    return meta


if __name__ == '__main__':
    split = sys.argv[1]
    for ep in map(int, sys.argv[2:]):
        m = build(split, ep)
        pk = m['pick'] or {}
        print(f"{split[0]}{ep} {m['name']}: {m['rule']} | pick l1 {pk.get('l1', 0) * 100:.1f} l2 {pk.get('l2', 0) * 100:.1f} cm sz {pk.get('size_score', np.nan):.2f} "
              f"cx {pk.get('cx', np.nan):.0f} depth {pk.get('depth', np.nan):.2f} | cands " +
              ' ; '.join(f"{c['l1'] * 100:.0f}x{c['l2'] * 100:.0f}cm s{c['size_score']:.2f}{' EGO' if c['ego'] else ''} x{c['cx']:.0f}" for c in m['cands'][:6])
              + f" | val {m.get('val')}", flush=True)
