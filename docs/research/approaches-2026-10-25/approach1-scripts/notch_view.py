"""Which half of board 2 holds the real notch? Video check of a suspected end-flip (GT-free): approach-1 study, 2026-10-25.

Each board's cross-lap notch is a through-cut about 8.5 mm wide along the board's width axis y, at mid-length (z = 0),
on one half of the width. Our track says where the board is. We project two candidate notch centre lines of board 2
into the rectified ego_cam_c image (as perc2.py rectifies it): '+y' (green) and '-y' (red), plus wood control lines
2.5 cm to either side along z. The real notch shows background through the board, so its line's intensity profile
differs from the wood controls. Writes a montage of crops for visual inspection and prints the line statistics.
Usage: python notch_view.py VIDEO_C.mp4 VIDEO_B_or_none CALIB.json POSES.npz MESH_B.glb f1,f2,... OUT.jpg"""
import json, sys

import cv2
import numpy as np
import trimesh

vid, _, calib, poses, meshp, frs, out = sys.argv[1:8]
F = [int(x) for x in frs.split(',')]
C = json.load(open(calib)); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
SZ, RSZ = (1280, 800), (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), SZ, E[:3, :3].copy(),
                                            E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, RSZ, cv2.CV_32FC1); KR = P1[:3, :3]
cap = cv2.VideoCapture(vid); imgs = {}; i = 0
while True:
    ok, f = cap.read()
    if not ok or i > max(F):
        break
    if i in F:
        imgs[i] = cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR)
    i += 1
import os
OBJ = os.environ.get('OBJ', 'wooden_piece_2')                 # which board to test (default board 2)
P = np.load(poses); TB = P[f'cam_T_{OBJ}']
m = trimesh.load(meshp, force='mesh'); V = np.asarray(m.vertices)
ys = np.linspace(0.006, 0.060, 40)
lines = {'+y': np.c_[0 * ys, ys, 0 * ys], '-y': np.c_[0 * ys, -ys, 0 * ys]}
ctrl = {k: [v + [0, 0, dz] for dz in (-0.025, 0.025)] for k, v in lines.items()}


def proj(T, X):
    Y = X @ T[:3, :3].T + T[:3, 3]; u = Y @ KR.T
    return u[:, :2] / u[:, 2:3], Y[:, 2]


def sample(img, uv):
    uv = np.round(uv).astype(int); ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0])
    return img[uv[ok, 1], uv[ok, 0]].astype(float)


tiles = []
for t in F:
    if t not in imgs:
        continue
    g = imgs[t]; T = TB[t]; vis = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    uvV, _ = proj(T, V); hull = cv2.convexHull(uvV.astype(np.float32)).astype(int)
    cv2.polylines(vis, [hull], True, (255, 200, 0), 1)
    stats = {}
    for k, col in (('+y', (0, 255, 0)), ('-y', (0, 0, 255))):
        uv, _ = proj(T, lines[k]); cv2.polylines(vis, [uv.astype(int)], False, col, 1)
        line = sample(g, uv); wood = np.concatenate([sample(g, proj(T, c)[0]) for c in ctrl[k]])
        stats[k] = (round(float(line.mean()), 1), round(float(wood.mean()), 1), round(float(abs(line.mean() - wood.mean())), 1)) if len(line) and len(wood) else None
    # board-2 normal (x axis) toward the camera: |cos| near 1 means seen face-on
    face = abs(float(T[:3, 0] @ (-T[:3, 3] / np.linalg.norm(T[:3, 3]))))
    print(f'f{t}: face-on |cos| {face:.2f}; line mean / wood mean / |diff|: +y {stats["+y"]}  -y {stats["-y"]}', flush=True)
    x0, y0 = np.clip(hull.reshape(-1, 2).min(0) - 30, 0, None); x1, y1 = hull.reshape(-1, 2).max(0) + 30
    crop = vis[y0:y1, x0:x1]
    if crop.size:
        crop = cv2.resize(crop, (360, int(360 * crop.shape[0] / max(crop.shape[1], 1))))
        cv2.putText(crop, f'f{t}', (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        tiles.append(crop)
h = max(c.shape[0] for c in tiles); tiles = [cv2.copyMakeBorder(c, 0, h - c.shape[0], 0, 4, cv2.BORDER_CONSTANT) for c in tiles]
rows = [np.hstack(tiles[i:i + 4] + [np.zeros_like(tiles[0])] * (4 - len(tiles[i:i + 4]))) for i in range(0, len(tiles), 4)]
cv2.imwrite(out, np.vstack(rows))
