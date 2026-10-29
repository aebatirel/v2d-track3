"""GT-free identity and in-plane symmetry check for two near-identical objects (boards): approach-1 study, 2026-10-25.

Our board meshes carry their marker knobs (wooden_piece_1: corner knobs on +x; wooden_piece_2: three knobs on -x),
which make the two boards and their in-plane orientation distinguishable in the image while the boards lie flat.
For each assignment (as tracked / names swapped) and each of the 4 in-plane symmetries F of each board
(I, 180 deg about x, y, z; the plate is symmetric under all of them), the mesh is posed at T_track @ F, its knob
vertices on the camera-facing side are projected into the rectified ego_cam_c frame, and the score is the mean
intensity at the knob points minus the mean over the plate's own camera-facing points (knobs are darker than the
wood; lower is better). Summed over FRAMES. The best (assignment, F1, F2) is reported with the margin to the
as-tracked choice. Inputs: video, calibration, our poses and our meshes only.
Usage: python identity_rule.py VIDEO_C.mp4 CALIB.json POSES.npz MESH_1 MESH_2 f1,f2,..."""
import itertools, json, sys

import cv2
import numpy as np
import trimesh

vid, calib, poses, m1, m2, frs = sys.argv[1:7]
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
        imgs[i] = cv2.GaussianBlur(cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR), (3, 3), 0).astype(float)
    i += 1
names = ['wooden_piece_1', 'wooden_piece_2']
P = np.load(poses); TT = {n: P[f'cam_T_{n}'] for n in names}
M = {}
for n, p in zip(names, (m1, m2)):
    V = np.asarray(trimesh.load(p, force='mesh').vertices); xm = np.median(V[:, 0])
    M[n] = (V[np.abs(V[:, 0] - xm) > 0.009], V[np.abs(V[:, 0] - xm) < 0.003], xm)
FL = {'I': np.eye(4), 'Rx': np.diag([1., -1, -1, 1]), 'Ry': np.diag([-1., 1, -1, 1]), 'Rz': np.diag([-1., -1, 1, 1])}


def score(mesh, T, img):
    knobs, plate, xm = M[mesh]
    cam_side = np.sign((np.linalg.inv(T) @ np.r_[0, 0, 0, 1.0])[0] - xm)     # which face sees the camera
    k = knobs[np.sign(knobs[:, 0] - xm) == cam_side]
    if len(k) < 5:
        return 0.0
    def sample(X):
        Y = X @ T[:3, :3].T + T[:3, 3]; u = Y @ KR.T; uv = np.round(u[:, :2] / u[:, 2:3]).astype(int)
        ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0])
        return img[uv[ok, 1], uv[ok, 0]]
    a, b = sample(k), sample(plate)
    return float(a.mean() - b.mean()) if len(a) and len(b) else 0.0


res = []
for assign in ('as tracked', 'swapped'):
    src = {names[0]: names[0], names[1]: names[1]} if assign == 'as tracked' else {names[0]: names[1], names[1]: names[0]}
    for f1, f2 in itertools.product(FL, FL):
        s = 0.0
        for t in F:
            s += score(names[0], TT[src[names[0]]][t] @ FL[f1], imgs[t]) + score(names[1], TT[src[names[1]]][t] @ FL[f2], imgs[t])
        res.append((round(s / len(F), 1), assign, f1, f2))
res.sort()
base = [r for r in res if r[1] == 'as tracked' and r[2] == 'I' and r[3] == 'I'][0]
print('best 5 (score, assignment, F board1, F board2):', res[:5])
print('as tracked, no flip:', base, ' rank', res.index(base) + 1, 'of', len(res))
