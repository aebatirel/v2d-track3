"""CPU check of the camera-a geometry used by perc2 TRACK_CAM=a (numpy copy of the GPU code): project our stored ep12
control track (library_v3 meshes) and the stereo depth into the undistorted camera-a frame a[k+1]; save a montage."""
import sys, json, numpy as np, cv2, trimesh
CC, REPO = sys.argv[1], sys.argv[2]
sys.path.insert(0, f'{REPO}/pipeline'); import det_rules
C = json.load(open(f'{CC}/ds/track_3/public/meta/camera_calibration.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800),
                                            E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
KR = P1[:3, :3]
ext = lambda n: np.array(cam[n]['extrinsics_to_stereo_left'], float)
T_a_c = np.linalg.inv(ext('ego_cam_a')) @ ext('ego_cam_c')
T_a_rc = np.eye(4); T_a_rc[:3, :3] = T_a_c[:3, :3] @ R1.T; T_a_rc[:3, 3] = T_a_c[:3, 3]
S = 0.5; AW, AH = 1014, 760; KA = K_('ego_cam_a').copy(); KA[:2] *= S
MA = cv2.initUndistortRectifyMap(K_('ego_cam_a'), D_('ego_cam_a'), None, KA, (AW, AH), cv2.CV_32FC1)
cap = cv2.VideoCapture(f'{CC}/ds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000012.mp4'); FA = []
while True:
    ok, f = cap.read()
    if not ok: break
    FA.append(cv2.remap(f, MA[0], MA[1], cv2.INTER_LINEAR))
P = np.load(f'{CC}/store/runs/20261102-ptrkA-7fbc3215/results/ptrk/C/ep12/poses.npz')
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
D = np.load(f'{CC}/store/cache/depth/public/ep12/depths_fs0.5.npy', mmap_mode='r')
print('frames a', len(FA), 'depth', D.shape, 'objects', names, 'T_a_rc t', T_a_rc[:3, 3].round(4))
M = {n: trimesh.load(f'{REPO}/meshes/library_v3/{n}.glb', force='mesh') for n in names}
vv, uu = np.mgrid[0:1000, 0:1600]
def splat(i):
    z = np.asarray(D[i]); ok = z > 0
    X = np.stack([(uu[ok] - KR[0, 2]) / KR[0, 0] * z[ok], (vv[ok] - KR[1, 2]) / KR[1, 1] * z[ok], z[ok]], 1)
    Xa = X @ T_a_rc[:3, :3].T + T_a_rc[:3, 3]; za = Xa[:, 2]
    u = np.round(KA[0, 0] * Xa[:, 0] / za + KA[0, 2]).astype(int); v = np.round(KA[1, 1] * Xa[:, 1] / za + KA[1, 2]).astype(int)
    k = (za > .05) & (u >= 0) & (u < AW) & (v >= 0) & (v < AH)
    Dz = np.full((AH, AW), np.inf); o = np.argsort(-za[k]); Dz[v[k][o], u[k][o]] = za[k][o]
    hole = np.isinf(Dz); mn = cv2.erode(np.where(hole, 1e9, Dz).astype(np.float32), np.ones((3, 3), np.uint8))
    Dz = np.where(hole, np.where(mn < 1e8, mn, 0), Dz); return Dz.astype(np.float32)
tiles = []
for i in [int(x) for x in sys.argv[3].split(',')]:
    row = []
    for off in (0, 1):
        img = FA[min(i + off, len(FA) - 1)].copy()
        for j, n in enumerate(names):
            X = M[n].vertices @ P[f'cam_T_{n}'][i][:3, :3].T + P[f'cam_T_{n}'][i][:3, 3]
            Xa = X @ T_a_rc[:3, :3].T + T_a_rc[:3, 3]
            u = KA[0, 0] * Xa[:, 0] / Xa[:, 2] + KA[0, 2]; v = KA[1, 1] * Xa[:, 1] / Xa[:, 2] + KA[1, 2]
            for a, b in zip(u[::3].astype(int), v[::3].astype(int)):
                if 0 <= a < AW and 0 <= b < AH: img[b, a] = (0, 255, 0) if j == 0 else (255, 0, 255)
        cv2.putText(img, f'stereo f{i}  a f{i + off}', (10, 30), 0, 1, (0, 255, 255), 2); row.append(img)
    Dz = splat(i); valid = (Dz > 0).mean()
    dv = cv2.applyColorMap(np.clip((Dz - 0.3) / 0.6 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET); dv[Dz == 0] = 0
    row.append(cv2.addWeighted(FA[min(i + 1, len(FA) - 1)], 0.5, dv, 0.5, 0))
    cv2.putText(row[-1], f'depth into a, valid {valid:.2f}', (10, 30), 0, 1, (255, 255, 255), 2)
    tiles.append(np.hstack([cv2.resize(t, (507, 380)) for t in row]))
cv2.imwrite(sys.argv[4], np.vstack(tiles)); print('wrote', sys.argv[4])
