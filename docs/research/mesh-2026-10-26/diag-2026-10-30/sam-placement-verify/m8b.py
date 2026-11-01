import numpy as np
from vlib import *
from scipy.spatial import cKDTree
sv, sf = load_scan('wooden_piece_1'); B = sample(sv, sf, 6000, 12); c, V, _ = pca_frame(B)
for ep in (24, 23):
    P = np.load(f'{SCR}/obs_all/ep{ep}_wooden_piece_1.npz')['pts']; rng = np.random.default_rng(0); O = P[rng.choice(len(P), min(8000, len(P)), replace=False)]
    tb = cKDTree(B); R = np.eye(3); t = np.zeros(3)
    for _ in range(60):
        X = O @ R.T + t; d, i = tb.query(X); k = d <= np.quantile(d, 0.9); _, R, t = umeyama(O[k], B[i[k]], scale=False)
    oc = O.mean(0); mv = (oc @ R.T + t) - oc
    print(f'ep{ep} points -> scan local rigid: rot {rot_angle(R):.1f} deg, centroid move {np.linalg.norm(mv)*1e3:.1f} mm, along scan PCA L/M/S {np.round(mv @ V * 1e3, 1)}; obs extent along L/M/S (mm) {np.round(np.ptp((O-c)@V,0)*1e3)} vs scan {np.round(np.ptp((B-c)@V,0)*1e3)}')
    for seed in (42, 7):
        v, f = load(f'{OUT}/b1_ep24/wooden_piece_1_ep{ep}_s{seed}.ply')
        tr, un, T = multi_start(sample(v, f, 4000, 11), B, scale=True)
        cm = centroid(v, f); off = apply(T, cm[None])[0] - cm
        print(f'   SAM s{seed} fitted to ep{ep}: offset L/M/S {np.round(off @ V * 1e3, 1)} mm; placed-mesh extent L/M/S {np.round(np.ptp((sample(v,f,20000,3)-c)@V,0)*1e3)}')
