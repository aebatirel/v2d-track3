"""Identity check for near-identical objects (GT-free): approach-1 study, 2026-10-25.

Projects each board mesh's protrusions (marker knobs and feet: vertices more than KNOB_X from the plate mid-plane)
into the rectified ego_cam_c frame at the given frames, as posed by our track. If the projected knobs of a mesh land
on the image knobs, that mesh's identity and in-plane orientation fit the board it tracks; if they land on bare wood,
the track carries the wrong identity or a flip. Writes one annotated full frame per requested frame (montage).
Usage: python identity_view.py VIDEO_C.mp4 CALIB.json POSES.npz MESH_1.glb MESH_2.glb f1,f2 OUT.jpg"""
import json, sys

import cv2
import numpy as np
import trimesh

vid, calib, poses, m1, m2, frs, out = sys.argv[1:8]
KNOB_X = 0.009
F = [int(x) for x in frs.split(',')]
C = json.load(open(calib)); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float); SZ, RSZ = (1280, 800), (1600, 1000)
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
P = np.load(poses)
meshes = {}
for n, p in (('wooden_piece_1', m1), ('wooden_piece_2', m2)):
    V = np.asarray(trimesh.load(p, force='mesh').vertices); xm = np.median(V[:, 0])
    meshes[n] = (V, V[np.abs(V[:, 0] - xm) > KNOB_X])
cols = {'wooden_piece_1': (0, 255, 255), 'wooden_piece_2': (255, 0, 255)}
tiles = []
for t in F:
    vis = cv2.cvtColor(imgs[t], cv2.COLOR_GRAY2BGR)
    for n, (V, Kn) in meshes.items():
        T = P[f'cam_T_{n}'][t]
        for X, r in ((V, None), (Kn, 3)):
            Y = X @ T[:3, :3].T + T[:3, 3]; u = Y @ KR.T; uv = (u[:, :2] / u[:, 2:3]).astype(int)
            if r is None:
                cv2.polylines(vis, [cv2.convexHull(uv.astype(np.float32)).astype(int)], True, cols[n], 1)
                cv2.putText(vis, n[-1], tuple(int(v) for v in uv.mean(0)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, cols[n], 2)
            else:
                for q in uv[::3]:
                    cv2.circle(vis, (int(q[0]), int(q[1])), 1, cols[n], -1)
    cv2.putText(vis, f'f{t}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    tiles.append(cv2.resize(vis, (800, 500)))
cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + 2]) if len(tiles[i:i + 2]) == 2 else np.hstack([tiles[i], np.zeros_like(tiles[i])])
                            for i in range(0, len(tiles), 2)]))
