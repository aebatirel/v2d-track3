import sys, json, numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tracker-fix/T5/scripts')
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import vo_t5 as V, det_rules
S = sys.argv[1]
MC, MB, FR, BASE, KR = V.rect_setup(f'{S}/hfds/track_3/public/meta/camera_calibration.json')
rc, rb = V.frames(f'{S}/leak/t5/v/ep24_c.mp4', MC), V.frames(f'{S}/leak/t5/v/ep24_b.mp4', MB)
D0 = np.load(f'{S}/refine/in/ep24/depth0.npy')
pfs = V.plane_fit(D0, KR, np.ones_like(D0, bool))
print('FS depth0 plane', np.round(pfs['n'], 4), round(pfs['c'], 4), pfs['n_inl'], round(pfs['rms_mm'], 2))
sgbm = cv2.StereoSGBM_create(minDisparity=0, numDisparities=192, blockSize=5, P1=8 * 25, P2=32 * 25, disp12MaxDiff=1,
                             uniquenessRatio=10, speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
tiles = []
for t in (0, 36, 40, 44, 49, 61, 100):
    d = sgbm.compute(rc[t], rb[t]).astype(np.float32) / 16.0
    D = np.where(d > 1, FR * BASE / np.maximum(d, 1e-6), 0).astype(np.float32)
    v = (D > 0).mean(); inr = ((D > 0.2) & (D < 1.0)).mean()
    if t == 0:
        ok = (D > 0) & (D0 > 0); print('SGBM vs FS f0: median |dz| mm', round(float(np.median(np.abs(D[ok] - D0[ok])) * 1000), 2), 'median dz', round(float(np.median(D[ok] - D0[ok])) * 1000, 2), 'median FS z', round(float(np.median(D0[ok])), 3))
    p = V.plane_fit(D, KR, np.ones_like(D, bool))
    print(t, 'valid', round(v, 3), 'in 0.2-1m', round(inr, 3), 'plane', None if p is None else (np.round(p['n'], 3).tolist(), round(p['c'], 3), p['n_inl'], round(p['rms_mm'], 2)))
    vis = cv2.applyColorMap(np.clip(D / 1.5 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
    img = cv2.cvtColor(rc[t], cv2.COLOR_GRAY2BGR)
    tiles.append(np.hstack([cv2.resize(img, (400, 250)), cv2.resize(vis, (400, 250))]))
cv2.imwrite(f'{S}/leak/t5/dbg/planes.jpg', np.vstack(tiles))
