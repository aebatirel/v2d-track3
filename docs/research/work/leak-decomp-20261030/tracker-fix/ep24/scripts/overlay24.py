"""ORACLE DIAGNOSTIC overlays for public ep24 (cam a). Points of the public scans drawn at:
  red    = P_o track (our camera-frame track, through our VO camera) -- what perception saw;
  green  = mocap, mapped into the perception world ONCE (rigid fit on frames 0-7, both boards at rest) and projected
           through our VO camera world_T_cam(t): where the truth lands if our camera were right;
  cyan   = mocap projected through the GT-free anchor-corrected camera C(t) world_T_cam(t) (rule B_T, vo_anchor_test.py).
If green drifts off the boards while red and cyan stay on them, the error is the camera (VO), not the object tracker.
Usage: python -I overlay24.py OUT_DIR
"""
import json, os, sys
import numpy as np, cv2, trimesh

sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
import vo_anchor_test as V  # noqa: E402
XF = V.XF; S = V.S
EP = 24
VID = f'{S}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000024.mp4'
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
names, gt = XF.mocap(V.T3D, EP, None)
H = [XF.host_geometry(V.T3D, n, s) for s, n in enumerate(names)]
hz = np.load(f'{S}/refine/in/ep{EP}/hands_refined.npz', allow_pickle=True)
Ka, Da, T_rect_a, aoff = hz['Ka'], hz['Da'], hz['T_rect_a'], int(hz['a_offset'])
PZ = np.load(f'{V.ROOT}/Po/ep{EP}/poses.npz'); W_C = PZ['world_T_cam'].astype(np.float64)
Vv = np.load(f'{V.ROOT}/Po/ep{EP}/poses_world_vo.npz')
T = {n: Vv[n].astype(np.float64) @ np.linalg.inv(np.asarray(V.XG[n]['X_scan_T_lib'])) for n in names}  # scan body frames
Tl = {n: Vv[n].astype(np.float64) for n in names}
N = len(W_C)
# GT-free correction (rule B_T) on the lib-frame track with our meshes
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(np.float64)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
P = {n: V.lib_pts(n) for n in names}
cand, dh, gap = V.windows(Tl, P, J, Jv, names, True)
C, act = V.correct(Tl, P, names, {n: cand[n].copy() for n in names}, gap, 'T')
# mocap -> perception world: rigid fit on frames 0-7 (scan points of both boards)
pts = {n: trimesh.sample.sample_surface(trimesh.load(XF.scan_path(V.T3D, n), force='mesh'), 1500, seed=1)[0] for n in names}
A, B = [], []
for n in names:
    for t in range(8):
        A.append(pts[n] @ gt[n][t, :3, :3].T + gt[n][t, :3, 3]); B.append(pts[n] @ T[n][t, :3, :3].T + T[n][t, :3, 3])
A = np.concatenate(A); B = np.concatenate(B); ma, mb = A.mean(0), B.mean(0)
U, _, Vt = np.linalg.svd((A - ma).T @ (B - mb)); Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
R = Vt.T @ Dg @ U.T; G = np.eye(4); G[:3, :3] = R; G[:3, 3] = mb - R @ ma
print('display fit residual cm median %.2f' % (np.median(np.linalg.norm(A @ R.T + G[:3, 3] - B, axis=1)) * 100))


def proj(Tw, n, cam):
    X = pts[n] @ Tw[:3, :3].T + Tw[:3, 3]
    M = np.linalg.inv(cam @ T_rect_a); Xa = X @ M[:3, :3].T + M[:3, 3]
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
    return uv.reshape(-1, 2)


cap = cv2.VideoCapture(VID); frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
print('cam a frames', len(frames), 'a_offset', aoff)
D = json.load(open(f'{S}/leak/diag_24/out/diag24.json'))['frames']
SEL = [int(x) for x in os.environ.get('SEL', '0,30,42,60,100,150,220,270').split(',')]
tiles = []
for i in SEL:
    img = frames[i + aoff].copy()
    for n in names:
        for Tw, cam, col in ((T[n][i], W_C[i], (0, 0, 255)), (G @ gt[n][i], W_C[i], (0, 200, 0)),
                             (G @ gt[n][i], C[i] @ W_C[i], (255, 255, 0))):
            for u, v in proj(Tw, n, cam).astype(int)[::2]:
                if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                    cv2.circle(img, (u, v), 2, col, -1)
    c = np.mean([proj(G @ gt[n][i], n, W_C[i]).mean(0) for n in names], 0).astype(int)
    x0, y0 = int(np.clip(c[0] - 420, 0, img.shape[1] - 840)), int(np.clip(c[1] - 330, 0, img.shape[0] - 660))
    crop = cv2.resize(img[y0:y0 + 660, x0:x0 + 840], (560, 440))
    r = D[i]
    txt = f"f{i}  kit ADD b1 {r[names[0]]['Po']['add']:.1f} b2 {r[names[1]]['Po']['add']:.1f} cm  corr {np.linalg.norm(C[i, :3, 3]) * 100:.1f} cm"
    cv2.rectangle(crop, (0, 0), (560, 26), (0, 0, 0), -1)
    cv2.putText(crop, txt, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(crop)
legend = np.zeros((440, 560, 3), np.uint8)
for k, (s, col) in enumerate([('P_o track (our camera-frame track)', (0, 0, 255)),
                              ('mocap via our VO camera (fit f0-7 only)', (0, 200, 0)),
                              ('mocap via GT-free anchor-corrected camera', (255, 255, 0))]):
    cv2.circle(legend, (30, 60 + 50 * k), 8, col, -1)
    cv2.putText(legend, s, (50, 66 + 50 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
cv2.putText(legend, 'ep24 cam a, public; ORACLE DIAGNOSTIC', (20, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
cv2.putText(legend, 'green off the boards = camera (VO) error', (20, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
tiles.append(legend)
while len(tiles) % 3:
    tiles.append(np.zeros_like(legend))
rows = [np.hstack(tiles[k:k + 3]) for k in range(0, len(tiles), 3)]
name = os.environ.get('NAME', 'ep24_vo_overlay_grid.png')
cv2.imwrite(f'{OUT}/{name}', np.vstack(rows))
print('wrote', f'{OUT}/{name}')
