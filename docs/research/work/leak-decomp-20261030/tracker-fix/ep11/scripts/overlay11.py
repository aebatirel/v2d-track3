"""ORACLE DIAGNOSTIC overlays for public ep11 (cam a): blue cup at mocap (green), P_s (magenta), P_o (red), and the mocap
beige cup (yellow), plus the frozen-blue P_o (white, rule F1) on the nested frames. Mocap is mapped into the perception
world by one rigid transform fitted to the P_s track on frames 0-39 (before the nest, where P_s is < 1 cm): display only.
Usage: python -I overlay11.py OUT_DIR
"""
import os, sys
import numpy as np, cv2, trimesh

sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_11/scripts')
import diag11 as D  # noqa: E402
XF = D.XF
S = D.S
VID = f'{S}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000011.mp4'
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
hz = np.load(f'{D.REF}/hands_refined.npz', allow_pickle=True)
Ka, Da, T_rect_a, aoff = hz['Ka'], hz['Da'], hz['T_rect_a'], int(hz['a_offset'])
W_C = np.load(f'{D.RUN}/perc2/poses.npz')['world_T_cam'].astype(np.float64)

# mocap -> perception world (display only): Kabsch on anchor + axis points of both cups, P_s frames 0-39
P, Q = [], []
for s, n in enumerate(names):
    for k in (-0.05, 0, 0.05):
        for T_, L in ((tr['Ps'][n][:40], P), (gt[n][:40], Q)):
            L.append(T_[:, :3, 3] + np.einsum('nij,j->ni', T_[:, :3, :3], H[s]['anchor'] + k * H[s]['axis']))
P = np.concatenate(P); Q = np.concatenate(Q); mp, mq = P.mean(0), Q.mean(0)
U, _, Vt = np.linalg.svd((Q - mq).T @ (P - mp)); Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
R = Vt.T @ Dg @ U.T; t = mp - R @ mq
G = np.eye(4); G[:3, :3] = R; G[:3, 3] = t
res = np.linalg.norm(Q @ R.T + t - P, axis=1)
print('display fit residual cm median %.2f max %.2f' % (np.median(res) * 100, res.max() * 100))
pts = {n: trimesh.sample.sample_surface(trimesh.load(XF.scan_path(D.T3D, n), force='mesh'), 1200, seed=1)[0] for n in names}


def proj(Tw, n, i):
    X = pts[n] @ Tw[:3, :3].T + Tw[:3, 3]
    A = np.linalg.inv(W_C[i] @ T_rect_a); Xa = X @ A[:3, :3].T + A[:3, 3]
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
    return uv.reshape(-1, 2)


# check: hand joints reproject onto the stored cam-a detections
errs = []
for side in ('left', 'right'):
    J = hz[f'joints_{side}'].astype(float); uv = hz[f'uv_a_{side}'].astype(float); m = hz[f'measured_{side}'] & hz[f'valid_{side}']
    for i in np.where(m)[0][:30]:
        A = np.linalg.inv(W_C[i] @ T_rect_a); Xa = J[i] @ A[:3, :3].T + A[:3, 3]
        u, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
        if np.all(np.isfinite(uv[i])):
            errs.append(np.median(np.linalg.norm(u.reshape(-1, 2) - uv[i], axis=1)))
print('hand reprojection px median %.1f' % np.median(errs))

cap = cv2.VideoCapture(VID); frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
print('cam a frames', len(frames))
blue_frozen = np.repeat(tr['Po']['blue_cup'][:1], N, 0)
SEL = [0, 30, 45, 63, 69, 90, 130]
tiles = []
for i in SEL:
    img = frames[i + aoff].copy()
    layers = [(G @ gt['beige_cup'][i], 'beige_cup', (0, 220, 255)), (G @ gt['blue_cup'][i], 'blue_cup', (0, 200, 0)),
              (tr['Ps']['blue_cup'][i], 'blue_cup', (255, 0, 255)), (tr['Po']['blue_cup'][i], 'blue_cup', (0, 0, 255))]
    for Tw, n, col in layers:
        for u, v in proj(Tw, n, i).astype(int):
            if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                cv2.circle(img, (u, v), 2, col, -1)
    # crop around the blue cup (mocap) for legibility
    c = proj(G @ gt['blue_cup'][i], 'blue_cup', i).mean(0).astype(int)
    x0, y0 = max(0, c[0] - 420), max(0, c[1] - 380); crop = img[y0:y0 + 700, x0:x0 + 840]
    crop = cv2.resize(crop, (560, 467))
    row = D.json.load(open(f'{S}/leak/diag_11/diag11.json'))['frames'][i]
    txt = f"f{i}  blue dz Po {row['blue_cup']['Po']['dz']:+.1f} Ps {row['blue_cup']['Ps']['dz']:+.1f} cm"
    cv2.rectangle(crop, (0, 0), (560, 26), (0, 0, 0), -1)
    cv2.putText(crop, txt, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(f'{OUT}/ep11_f{i:03d}_blue.png', crop)
    tiles.append(crop)
legend = np.zeros((467, 560, 3), np.uint8)
for k, (s, col) in enumerate([('mocap blue cup (true, static)', (0, 200, 0)), ('P_s blue (scan template)', (255, 0, 255)),
                              ('P_o blue (our mesh)', (0, 0, 255)), ('mocap beige cup (true)', (0, 220, 255))]):
    cv2.circle(legend, (30, 60 + 50 * k), 8, col, -1)
    cv2.putText(legend, s, (50, 66 + 50 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
cv2.putText(legend, 'ep11 cam a, public; ORACLE DIAGNOSTIC', (20, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
cv2.putText(legend, 'mocap mapped by a fit to P_s f0-39 (display)', (20, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
tiles.append(legend)
rows = [np.hstack(tiles[k:k + 4]) for k in (0, 4)]
cv2.imwrite(f'{OUT}/ep11_blue_lift_grid.png', np.vstack(rows))
print('wrote', OUT)
