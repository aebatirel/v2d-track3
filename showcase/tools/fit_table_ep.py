"""Real table disc (centre, radius) in an episode's sim/table frame, measured from its head-camera colour video
(generalises fit_table.py, which was written for ep27; same method): wood-coloured pixels -> outer boundary (white
objects and skin masked) -> rays through the calibrated camera a at the VO pose -> intersection with the tabletop
plane -> RANSAC circle + algebraic refit. Our own perception files only (no ground truth). Rendering only.
  fit_table_ep.py --video EP_a.mp4 --hands hands.npz --table_frame table_frame.npz --poses poses.npz --ztop 0.60
                  [--frames 0,50,100] [--radius 0.230] [--out fit.json] [--vis DIR]
--radius fixes the radius (the same table in every Track 3 episode: 0.230 m measured on ep27) and fits only the centre:
robust when spoons, boards or a partial view add other wood-coloured contours.
"""
import argparse, json, os

import cv2
import numpy as np

p = argparse.ArgumentParser(); p.add_argument('--video', required=True); p.add_argument('--hands', required=True)
p.add_argument('--table_frame', required=True); p.add_argument('--poses', required=True); p.add_argument('--ztop', type=float, default=0.60)
p.add_argument('--frames', default=''); p.add_argument('--out', default=''); p.add_argument('--vis', default='')
p.add_argument('--rmin', type=float, default=0.15); p.add_argument('--rmax', type=float, default=0.6)
p.add_argument('--radius', type=float, default=0, help='fixed radius (m): fit the centre only')
p.add_argument('--area', action='store_true', help='with --radius: choose the centre whose projected disc best overlaps the '
               'wood-coloured pixels (objects and skin ignored) instead of fitting the rim; for episodes where the rim is '
               'mostly hidden or merged with the skin mask')
a = p.parse_args()
h = np.load(a.hands); K, D, T_ra2rect = h['Ka'], h['Da'], h['T_rect_a'].astype(float)
Tt = np.load(a.table_frame)['T_table_from_world']; WC = np.load(a.poses)['world_T_cam'].astype(float)
cap = cv2.VideoCapture(a.video); n_vid = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); n = min(n_vid, len(WC))
frames = [int(x) for x in a.frames.split(',')] if a.frames else sorted({int(x) for x in np.linspace(0, n - 1, 6)})
imgs = {}; i = 0
while True:
    ok, im = cap.read()
    if not ok or i > max(frames):
        break
    if i in frames:
        imgs[i] = im
    i += 1
pts_all = []; per_frame = {}; area_masks = {}
for f, im in imgs.items():
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 5) & (hsv[..., 0] <= 22) & (hsv[..., 1] >= 110) & (hsv[..., 2] >= 60)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    nl, lab, st, _ = cv2.connectedComponentsWithStats(m)
    H, W = im.shape[:2]
    white = cv2.dilate(((hsv[..., 2] >= 200) & (hsv[..., 1] <= 50)).astype(np.uint8), np.ones((25, 25), np.uint8))
    skin = cv2.dilate(((hsv[..., 0] <= 20) & (hsv[..., 1] >= 40) & (hsv[..., 1] < 110)).astype(np.uint8), np.ones((25, 25), np.uint8))
    sm = lambda x: cv2.resize(x, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST)
    area_masks[f] = (sm((m > 0).astype(np.uint8)), sm(((white > 0) | (skin > 0)).astype(np.uint8)), im)
    P = []
    for k in range(1, nl):
        if st[k, cv2.CC_STAT_AREA] < 3000:
            continue
        cs, _ = cv2.findContours((lab == k).astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            c = c[:, 0, :]
            ok = (c[:, 0] > 8) & (c[:, 0] < W - 8) & (c[:, 1] > 8) & (c[:, 1] < H - 8)
            ok &= (white[c[:, 1], c[:, 0]] == 0) & (skin[c[:, 1], c[:, 0]] == 0)
            P.append(c[ok].astype(np.float64))
    P = np.concatenate(P) if P else np.zeros((0, 2))
    if len(P) < 20:
        continue
    un = cv2.undistortPoints(P.reshape(-1, 1, 2), K, D).reshape(-1, 2)
    T = Tt @ WC[f] @ T_ra2rect                                  # camera a -> sim/table frame
    o = T[:3, 3]; d = np.c_[un, np.ones(len(un))] @ T[:3, :3].T
    s = (a.ztop - o[2]) / d[:, 2]; X = (o + s[:, None] * d)[s > 0]
    pts_all.append(X[:, :2]); per_frame[f] = (P, im)
Q = np.concatenate(pts_all) if pts_all else np.zeros((0, 2))
best = None; rng = np.random.default_rng(0)
ANG = np.linspace(0, 2 * np.pi, 120, endpoint=False)


def disc_px(f, ctr, r, scale=4):
    C = np.c_[ctr[0] + r * np.cos(ANG), ctr[1] + r * np.sin(ANG), np.full(len(ANG), a.ztop), np.ones(len(ANG))]
    Xc = (C @ np.linalg.inv(Tt @ WC[f] @ T_ra2rect).T)[:, :3]
    if (Xc[:, 2] < 0.05).any():
        return None
    uv, _ = cv2.projectPoints(Xc.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, D)
    return (uv.reshape(-1, 2) / scale).astype(np.int32)


def area_score(ctr, r):
    s = []
    for f, (wood, dc, _) in area_masks.items():
        poly = disc_px(f, ctr, r)
        if poly is None:
            continue
        dm = np.zeros_like(wood); cv2.fillPoly(dm, [poly], 1); care = dc == 0
        s.append(((dm & wood) & care).sum() / max(((dm | wood) & care).sum(), 1))
    return float(np.mean(s)) if s else 0.0


if a.area:
    assert a.radius, '--area needs --radius'
    r = a.radius; g = np.arange(-0.36, 0.3601, 0.02)
    sc = {(x, y): area_score((x, y), r) for x in g for y in g}
    c0 = max(sc, key=sc.get); g2 = np.arange(-0.03, 0.0301, 0.005)
    sc2 = {(c0[0] + x, c0[1] + y): area_score((c0[0] + x, c0[1] + y), r) for x in g2 for y in g2}
    ctr = np.array(max(sc2, key=sc2.get)); iou = sc2[tuple(ctr)]
    if len(Q):
        res = np.abs(np.linalg.norm(Q - ctr, axis=1) - r); inl = res < 0.008; res = res[inl]
    else:
        inl = np.zeros(0, bool); res = np.zeros(1)
    best = (ctr, r, inl)
for _ in range(4000 if not a.radius else 0):
    u, v, w = Q[rng.choice(len(Q), 3, replace=False)]
    A = np.array([[v[0] - u[0], v[1] - u[1]], [w[0] - u[0], w[1] - u[1]]]) * 2
    if abs(np.linalg.det(A)) < 1e-9:
        continue
    ctr = np.linalg.solve(A, np.array([v @ v - u @ u, w @ w - u @ u])); r = np.linalg.norm(u - ctr)
    if not a.rmin < r < a.rmax:
        continue
    inl = np.abs(np.linalg.norm(Q - ctr, axis=1) - r) < 0.008
    if best is None or inl.sum() > best[2].sum():
        best = (ctr, r, inl)
if a.area:
    pass
elif a.radius:                                                  # fixed radius: centres from point pairs
    r = a.radius
    for _ in range(6000):
        u, v = Q[rng.choice(len(Q), 2, replace=False)]; m = (u + v) / 2; dv = v - u; L = np.linalg.norm(dv)
        if not 0.02 < L < 2 * r:
            continue
        nrm = np.array([-dv[1], dv[0]]) / L; hgt = np.sqrt(r * r - (L / 2) ** 2)
        for ctr in (m + nrm * hgt, m - nrm * hgt):
            inl = np.abs(np.linalg.norm(Q - ctr, axis=1) - r) < 0.008
            if best is None or inl.sum() > best[2].sum():
                best = (ctr, r, inl)
    ctr, r, inl = best; q = Q[inl]
    for _ in range(20):                                         # Gauss-Newton on the centre, radius fixed
        dd = q - ctr; dist = np.linalg.norm(dd, axis=1); J = -dd / dist[:, None]
        ctr = ctr - np.linalg.lstsq(J, dist - r, rcond=None)[0]
    inl = np.abs(np.linalg.norm(Q - ctr, axis=1) - r) < 0.008; q = Q[inl]
    res = np.linalg.norm(q - ctr, axis=1) - r
else:
    ctr, r, inl = best
    q = Q[inl]; sol = np.linalg.lstsq(np.c_[2 * q, np.ones(len(q))], (q ** 2).sum(1), rcond=None)[0]
    ctr = sol[:2]; r = float(np.sqrt(sol[2] + ctr @ ctr)); res = np.linalg.norm(q - ctr, axis=1) - r
out = dict(center_xy=[float(ctr[0]), float(ctr[1])], radius=float(r), radius_fixed=bool(a.radius), inliers=int(inl.sum()), points=int(len(Q)), frames=list(imgs),
           ztop=a.ztop, method='area' if a.area else ('rim, fixed radius' if a.radius else 'rim'),
           **({'area_iou': iou} if a.area else {}), residual_mm_p50=float(np.median(np.abs(res)) * 1000), residual_mm_p90=float(np.percentile(np.abs(res), 90) * 1000))
print(json.dumps(out))
if a.out:
    json.dump(out, open(a.out, 'w'), indent=1)
if a.vis:                                                       # fitted circle projected back onto the first frame
    os.makedirs(a.vis, exist_ok=True)
    f0 = min(area_masks); im = area_masks[f0][2]; P = per_frame.get(f0, (np.zeros((0, 2)), None))[0]; vis = im.copy()
    for x, y in P[::4].astype(int):
        cv2.circle(vis, (x, y), 3, (0, 255, 0), -1)
    ang = np.linspace(0, 2 * np.pi, 200); C = np.c_[ctr[0] + r * np.cos(ang), ctr[1] + r * np.sin(ang), np.full(200, a.ztop), np.ones(200)]
    Tc = np.linalg.inv(Tt @ WC[f0] @ T_ra2rect); Xc = (C @ Tc.T)[:, :3]; Xc = Xc[Xc[:, 2] > 0.05]
    uv, _ = cv2.projectPoints(Xc.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, D)
    cv2.polylines(vis, [uv.reshape(-1, 2).astype(np.int32)], True, (0, 0, 255), 4, cv2.LINE_AA)
    cv2.imwrite(os.path.join(a.vis, 'table_fit.jpg'), cv2.resize(vis, (vis.shape[1] // 2, vis.shape[0] // 2)))
