# GT-free: stereo depth noise from table planarity in our own FoundationStereo depth (depths_fs0.5). For sampled frames:
# RANSAC support plane (recon_mesh.table_plane, thin SVD), then a local plane refit in 10 cm patches to remove any
# global tilt/curvature, residual robust std (1.4826 MAD) binned by depth. Prints sigma_z(d) and a fit sigma0*(d/0.6)^2.
import sys, json, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
_svd = np.linalg.svd
np.linalg.svd = lambda A, full_matrices=False, **k: _svd(A, full_matrices=False, **k)
import recon_mesh as rm
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
K = rm.rectified_K(f'{SP}/loc/t3/calib.json')
out = {}
for ep in sys.argv[1:]:
    D = np.load(f'{SP}/loc/depth/ep{ep}/depths_fs0.5.npy', mmap_mode='r'); P = np.load(f'{SP}/loc/perc/ep{ep}/poses.npz')
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    o0 = (P['world_T_cam'][0] @ P[f'cam_T_{names[0]}'][0])[:3, 3]
    rows = []
    for t in np.linspace(0, len(D) - 1, 8).astype(int):
        Dt = np.array(D[t]); C_W = np.linalg.inv(P['world_T_cam'][t]); oc = (C_W @ P['world_T_cam'][0])[:3, 3] * 0 + (np.linalg.inv(P['world_T_cam'][t]) @ P['world_T_cam'][0] @ np.r_[o0, 1])[:3]
        try:
            n, c, fr = rm.table_plane(Dt, K, oc)
        except SystemExit:
            continue
        vv, uu = np.mgrid[0:1000:2, 0:1600:2]; d = Dt[vv, uu]; ok = np.isfinite(d) & (d > 0.2) & (d < 1.5)
        X = np.stack([(uu[ok] - K[0, 2]) * d[ok] / K[0, 0], (vv[ok] - K[1, 2]) * d[ok] / K[1, 1], d[ok]], 1)
        h = X @ n + c; sel = np.abs(h) < 0.02; X = X[sel]
        # 10 cm patches in the plane: local LSQ plane, residuals
        e1 = np.cross(n, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        a = np.floor(X @ e1 / 0.1).astype(int); b = np.floor(X @ e2 / 0.1).astype(int)
        key = a * 100000 + b
        for k in np.unique(key):
            m = key == k
            if m.sum() < 400:
                continue
            Q = X[m]; q0 = Q.mean(0); nn = _svd(Q - q0, full_matrices=False)[2][2]
            r = (Q - q0) @ nn; r = r[np.abs(r) < 0.015]
            if len(r) < 300:
                continue
            s = 1.4826 * np.median(np.abs(r - np.median(r)))
            rows.append((float(Q[:, 2].mean()), float(s), float(abs(nn @ (q0 / np.linalg.norm(q0))))))
    R = np.array(rows)
    bins = [(0.3, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.8), (0.8, 1.2)]
    res = {}
    for lo, hi in bins:
        m = (R[:, 0] >= lo) & (R[:, 0] < hi)
        if m.sum():
            res[f'{lo}-{hi}m'] = dict(n_patches=int(m.sum()), sigma_mm=round(float(np.median(R[m, 1])) * 1e3, 2),
                                     cos_view=round(float(np.median(R[m, 2])), 2))
    s0 = float(np.median(R[:, 1] / (R[:, 0] / 0.6) ** 2))
    out[ep] = dict(bins=res, sigma0_at_0p6m_mm=round(s0 * 1e3, 2))
    print(ep, json.dumps(out[ep]), flush=True)
json.dump(out, open(f'{SP}/interact/obs/noise.json', 'w'), indent=1)
