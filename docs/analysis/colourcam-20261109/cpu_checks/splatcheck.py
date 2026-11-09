"""Compare perc2's torch splat (copied, device cpu) with the numpy splat of geomcheck.py on ep12 frames."""
import sys, json, numpy as np, cv2, torch
CC = sys.argv[1]
C = json.load(open(f'{CC}/ds/track_3/public/meta/camera_calibration.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800),
                                            E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
KR = P1[:3, :3]; RSZ = (1600, 1000)
ext = lambda n: np.array(cam[n]['extrinsics_to_stereo_left'], float)
T_a_c = np.linalg.inv(ext('ego_cam_a')) @ ext('ego_cam_c')
T_a_rc = np.eye(4); T_a_rc[:3, :3] = T_a_c[:3, :3] @ R1.T; T_a_rc[:3, 3] = T_a_c[:3, 3]
A_SCALE = 0.5; AW, AH = 1014, 760; KA = K_('ego_cam_a').copy(); KA[:2] *= A_SCALE
depths = np.load(f'{CC}/store/cache/depth/public/ep12/depths_fs0.5.npy', mmap_mode='r')
dev = 'cpu'
# ---- copied from perc2 (device cuda -> cpu) ----
_vv, _uu = np.mgrid[0:RSZ[1], 0:RSZ[0]]
_RAY = torch.as_tensor(np.stack([(_uu - KR[0, 2]) / KR[0, 0], (_vv - KR[1, 2]) / KR[1, 1], np.ones(_uu.shape)], -1).reshape(-1, 3), dtype=torch.float32, device=dev)
_RA = torch.as_tensor(T_a_rc[:3, :3], dtype=torch.float32, device=dev); _TA = torch.as_tensor(T_a_rc[:3, 3], dtype=torch.float32, device=dev)
def a_depth(i):
    z = torch.as_tensor(np.asarray(depths[i]), device=dev).reshape(-1); ok = z > 0
    Xa = (_RAY[ok] * z[ok, None]) @ _RA.T + _TA; za = Xa[:, 2]
    fa_, ca_, fb_, cb_ = float(KA[0, 0]), float(KA[0, 2]), float(KA[1, 1]), float(KA[1, 2])
    u = torch.round(fa_ * Xa[:, 0] / za + ca_).long(); v = torch.round(fb_ * Xa[:, 1] / za + cb_).long()
    k = (za > 0.05) & (u >= 0) & (u < AW) & (v >= 0) & (v < AH)
    Dz = torch.full((AH * AW,), float('inf'), device=dev).scatter_reduce_(0, v[k] * AW + u[k], za[k], reduce='amin').reshape(AH, AW)
    mn = -torch.nn.functional.max_pool2d(-Dz[None, None], 3, 1, 1)[0, 0]
    Dz = torch.where(torch.isinf(Dz), mn, Dz); Dz[torch.isinf(Dz)] = 0
    return Dz.cpu().numpy().astype(np.float32)
def a_mask(m, i):
    dep = depths[i]; v, u = np.nonzero(m & (dep > 0))
    if len(v) < 20: return None
    z = dep[v, u]; X = np.stack([(u - KR[0, 2]) * z / KR[0, 0], (v - KR[1, 2]) * z / KR[1, 1], z], 1)
    Xa = X @ T_a_rc[:3, :3].T + T_a_rc[:3, 3]; ok = Xa[:, 2] > 0.05; Xa = Xa[ok]
    uu = np.round(KA[0, 0] * Xa[:, 0] / Xa[:, 2] + KA[0, 2]).astype(int); vv = np.round(KA[1, 1] * Xa[:, 1] / Xa[:, 2] + KA[1, 2]).astype(int)
    k = (uu >= 0) & (uu < AW) & (vv >= 0) & (vv < AH)
    M = np.zeros((AH, AW), np.uint8); M[vv[k], uu[k]] = 1
    M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return M.astype(bool) if M.sum() >= 50 else None
# ---- numpy reference ----
def ref(i):
    z = np.asarray(depths[i]); ok = z > 0
    X = np.stack([(_uu[ok] - KR[0, 2]) / KR[0, 0] * z[ok], (_vv[ok] - KR[1, 2]) / KR[1, 1] * z[ok], z[ok]], 1)
    Xa = X @ T_a_rc[:3, :3].T + T_a_rc[:3, 3]; za = Xa[:, 2]
    u = np.round(KA[0, 0] * Xa[:, 0] / za + KA[0, 2]).astype(int); v = np.round(KA[1, 1] * Xa[:, 1] / za + KA[1, 2]).astype(int)
    k = (za > .05) & (u >= 0) & (u < AW) & (v >= 0) & (v < AH)
    Dz = np.full((AH, AW), np.inf); o = np.argsort(-za[k]); Dz[v[k][o], u[k][o]] = za[k][o]; return Dz
for i in (0, 90):
    t = a_depth(i); r = ref(i); both = np.isfinite(r) & (t > 0)
    print(f'f{i}: torch valid {(t > 0).mean():.3f}, numpy valid (no fill) {np.isfinite(r).mean():.3f}, '
          f'max |diff| where both raw-valid {np.abs(t[both] - r[both]).max():.2e}, filled px {((t > 0) & ~np.isfinite(r)).sum()}')
# mask transfer: a box region in rectified c around the image centre-bottom (where the cup/rack are)
m = np.zeros((1000, 1600), bool); m[600:900, 500:1100] = True
ma = a_mask(m, 0); print('mask rc px', m.sum(), '-> a px', None if ma is None else int(ma.sum()), 'bbox a', None if ma is None else (np.nonzero(ma)[1].min(), np.nonzero(ma)[0].min(), np.nonzero(ma)[1].max(), np.nonzero(ma)[0].max()))
