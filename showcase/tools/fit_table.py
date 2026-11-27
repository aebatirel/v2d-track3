"""Estimate the real table disc (centre, radius) in the sim/table frame from the ep27 colour video: wood-coloured pixels
-> outer boundary -> back-projected rays (camera a, calibrated, VO pose) -> intersection with the table plane z=0.60 ->
robust circle fit. Diagnostic for rendering only."""
import sys, json, numpy as np, cv2
S = sys.argv[1]; frames = [int(x) for x in sys.argv[2].split(',')]
h = np.load(f'{S}/ep27/ref_vc/hands.npz'); K, D, T_ra2rect = h['Ka'], h['Da'], h['T_rect_a'].astype(float)
Tt = np.load(f'{S}/ep27/ref_vc/table_frame.npz')['T_table_from_world']; WC = np.load(f'{S}/ep27/perc2/poses.npz')['world_T_cam'].astype(float)
cap = cv2.VideoCapture('/content/t3/videos/ep27_a.mp4'); imgs = {}
i = 0
while True:
    ok, im = cap.read()
    if not ok: break
    if i in frames: imgs[i] = im
    i += 1
pts_all = []
for f, im in imgs.items():
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 5) & (hsv[..., 0] <= 22) & (hsv[..., 1] >= 110) & (hsv[..., 2] >= 60)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    H, W = im.shape[:2]
    white = ((hsv[..., 2] >= 200) & (hsv[..., 1] <= 50)).astype(np.uint8)        # white objects (rack, pot)
    white = cv2.dilate(white, np.ones((25, 25), np.uint8))
    skin = ((hsv[..., 0] <= 20) & (hsv[..., 1] >= 40) & (hsv[..., 1] < 110)).astype(np.uint8)   # hands / arms
    skin = cv2.dilate(skin, np.ones((25, 25), np.uint8))
    P = []
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] < 3000: continue
        comp = (lab == k).astype(np.uint8) * 255
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            c = c[:, 0, :]
            ok = (c[:, 0] > 8) & (c[:, 0] < W - 8) & (c[:, 1] > 8) & (c[:, 1] < H - 8)
            ok &= (white[c[:, 1], c[:, 0]] == 0) & (skin[c[:, 1], c[:, 0]] == 0)
            P.append(c[ok].astype(np.float64))
    P = np.concatenate(P)
    vis = im.copy()
    for x, y in P[::3].astype(int): cv2.circle(vis, (x, y), 3, (0, 255, 0), -1)
    cv2.imwrite(f'{S}/table/mask_f{f}.jpg', cv2.resize(vis, (1014, 760)))
    un = cv2.undistortPoints(P.reshape(-1, 1, 2), K, D).reshape(-1, 2)
    rays = np.c_[un, np.ones(len(un))]
    T = Tt @ WC[f] @ T_ra2rect                       # camera a -> sim/table frame
    o = T[:3, 3]; d = rays @ T[:3, :3].T
    s = (0.60 - o[2]) / d[:, 2]; X = o + s[:, None] * d
    X = X[s > 0]
    pts_all.append(X[:, :2])
    print(f'frame {f}: {len(X)} boundary points, camera at {np.round(o, 3)}', flush=True)
Q = np.concatenate(pts_all)
best = None; rng = np.random.default_rng(0)
for _ in range(3000):
    a, b, c = Q[rng.choice(len(Q), 3, replace=False)]
    A = np.array([[b[0] - a[0], b[1] - a[1]], [c[0] - a[0], c[1] - a[1]]]) * 2
    y = np.array([b @ b - a @ a, c @ c - a @ a])
    if abs(np.linalg.det(A)) < 1e-9: continue
    ctr = np.linalg.solve(A, y); r = np.linalg.norm(a - ctr)
    if not 0.15 < r < 0.6: continue
    inl = np.abs(np.linalg.norm(Q - ctr, axis=1) - r) < 0.008
    if best is None or inl.sum() > best[2].sum(): best = (ctr, r, inl)
ctr, r, inl = best
# refine (algebraic fit on inliers)
q = Q[inl]; A = np.c_[2 * q, np.ones(len(q))]; sol = np.linalg.lstsq(A, (q ** 2).sum(1), rcond=None)[0]
ctr = sol[:2]; r = float(np.sqrt(sol[2] + ctr @ ctr))
res = np.linalg.norm(q - ctr, axis=1) - r
out = dict(center_xy=[float(ctr[0]), float(ctr[1])], radius=r, inliers=int(inl.sum()), points=int(len(Q)), residual_mm_p50=float(np.median(np.abs(res)) * 1000), residual_mm_p90=float(np.percentile(np.abs(res), 90) * 1000))
print(json.dumps(out)); json.dump(out, open(f'{S}/table/table_fit.json', 'w'), indent=1)
