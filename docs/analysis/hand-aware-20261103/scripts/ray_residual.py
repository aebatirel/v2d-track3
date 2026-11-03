"""GT-FREE measurement (inference-safe: reads the track, the depth cache, our meshes, our hand fits, calibration; no
mocap): per object and frame, the robust depth residual between the stereo depth and the template rendered at the
tracked pose, over visible object pixels with hand pixels and pixels of other objects in front removed.
  r(t) = median over valid pixels of (z_obs - z_render), metres; + = the observed surface lies farther than the track.
Rendering: dense template surface samples splatted into a z-buffer at 1/DS resolution of the rectified-left image.
Valid pixel: inside the eroded rendered silhouette, own surface nearest (no other object in front), observed depth > 0,
not in the hand mask (MediaPipe joints projected as capsules of radius HAND_R, when a hand fit is given), and
|z_obs - z_render| < BAND.
Also writes n_valid and the silhouette pixel count (visible fraction).
Usage: ray_residual.py --t3 T3 --track DIR(poses.npz) --depth depths.npy --lib LIBDIR --out OUT.npz [--hands hands.npz]
"""
import argparse, json, numpy as np, cv2, trimesh, pyarrow.parquet as pq

p = argparse.ArgumentParser()
p.add_argument('--t3', required=True); p.add_argument('--ep', type=int, required=True)
p.add_argument('--track', required=True); p.add_argument('--depth', required=True); p.add_argument('--lib', required=True)
p.add_argument('--hands'); p.add_argument('--out', required=True)
p.add_argument('--ds', type=int, default=4); p.add_argument('--band', type=float, default=0.08)
p.add_argument('--hand_r', type=float, default=0.015); p.add_argument('--npts', type=int, default=30000)
p.add_argument('--erode', type=int, default=1)
a = p.parse_args()

# rectification exactly as pipeline/perc2.py (left = ego_cam_c)
C = json.load(open(f'{a.t3}/calib.json')); cam = C['cameras']
sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800),
                                            E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=(1600, 1000),
                                            flags=cv2.CALIB_ZERO_DISPARITY)
KR = P1[:3, :3].copy(); K = KR.copy(); K[:2] /= a.ds; Wd, Hd = 1600 // a.ds, 1000 // a.ds

tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet', columns=['observation.objects']).slice(0, 1).to_pylist()
names = [o['name'] for o in tab[0]['observation.objects']]                 # names / slot order only
Z = np.load(a.track + '/poses.npz'); WC = Z['world_T_cam']; N = len(WC)
PTS = {n: np.asarray(trimesh.load(f'{a.lib}/{n}.glb', force='mesh').sample(a.npts, seed=1)) for n in names}
dep = np.load(a.depth, mmap_mode='r')
HJ = None
if a.hands:
    h = np.load(a.hands); HJ = [(h[f'joints_{s}'], h[f'valid_{s}']) for s in ('right', 'left')]
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14),
         (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17)]


def render(n, T):
    X = PTS[n] @ T[:3, :3].T + T[:3, 3]; X = X[X[:, 2] > 0.05]
    uv = X @ K.T; u = (uv[:, 0] / uv[:, 2]).astype(int); v = (uv[:, 1] / uv[:, 2]).astype(int)
    ok = (u >= 0) & (u < Wd) & (v >= 0) & (v < Hd); zb = np.full((Hd, Wd), np.inf, np.float32)
    np.minimum.at(zb, (v[ok], u[ok]), X[ok, 2].astype(np.float32))
    m = np.isfinite(zb).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))   # fill splat holes
    zf = np.where(np.isfinite(zb), zb, 0); zc = cv2.dilate(zf, np.ones((3, 3), np.uint8))   # hole fill (max of neighbours ~ ok for small holes)
    zb = np.where(np.isfinite(zb), zb, np.where(m > 0, zc, np.inf)).astype(np.float32)
    return zb


def hand_mask(i):
    m = np.zeros((Hd, Wd), np.uint8)
    if HJ is None: return m.astype(bool)
    Wi = np.linalg.inv(WC[i])
    for J, V in HJ:
        if not V[i]: continue
        X = J[i] @ Wi[:3, :3].T + Wi[:3, 3]
        if (X[:, 2] < 0.05).any(): continue
        uv = X @ K.T; uv = uv[:, :2] / uv[:, 2:]
        for b0, b1 in BONES:
            rpx = int(np.ceil(a.hand_r * K[0, 0] / min(X[b0, 2], X[b1, 2])))
            cv2.line(m, tuple(np.round(uv[b0]).astype(int)), tuple(np.round(uv[b1]).astype(int)), 1, 2 * rpx + 1)
        for j in range(21):
            rpx = int(np.ceil(a.hand_r * K[0, 0] / X[j, 2])); cv2.circle(m, tuple(np.round(uv[j]).astype(int)), rpx, 1, -1)
    return m.astype(bool)


out = {f'r_{n}': np.full(N, np.nan) for n in names}
out.update({f'nvalid_{n}': np.zeros(N, int) for n in names}); out.update({f'nsil_{n}': np.zeros(N, int) for n in names})
out.update({f'nhand_{n}': np.zeros(N, int) for n in names})
for i in range(N):
    D = cv2.resize(np.asarray(dep[i]), (Wd, Hd), interpolation=cv2.INTER_NEAREST)
    zbs = {n: render(n, Z[f'cam_T_{n}'][i]) for n in names}; hm = hand_mask(i)
    for n in names:
        zb = zbs[n]; sil = np.isfinite(zb)
        if a.erode: sil = cv2.erode(sil.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=a.erode).astype(bool)
        front = np.ones_like(sil)
        for o in names:
            if o != n: front &= ~(zbs[o] < zb - 0.005)
        v = sil & front & (D > 0) & ~hm
        d = np.where(v, D - zb, np.nan); v &= np.abs(np.nan_to_num(d, nan=9)) < a.band
        out[f'nsil_{n}'][i] = int(sil.sum()); out[f'nhand_{n}'][i] = int((sil & hm).sum()); out[f'nvalid_{n}'][i] = int(v.sum())
        if v.sum() >= 20: out[f'r_{n}'][i] = float(np.median(d[v]))
np.savez(a.out, names=np.array(names), **out)
print('done', a.ep, {n: round(float(np.nanmedian(out[f'r_{n}']) * 100), 2) for n in names})
