"""GT-free census of the observed-point files (obs_all/ep<N>_<obj>.npz). Reads only allowed keys.

Per file: points, frames, crop args (roi / others / hands), robust extents in the points' PCA frame, camera-direction
coverage on the view sphere, angular coverage of the points from their centre, PCA-side visibility, and the 4 mm
hits/free vote grids (observed-surface, seen-free and never-observed voxel shares).
Usage: python -I obs_census2.py OBS_DIR OUT.jsonl
"""
import glob, json, os, sys
import numpy as np

ALLOWED = ('pts', 'cam', 'frame', 'hits', 'free', 'lo', 'hi', 'vox', 'args')


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


def main():
    d, out = sys.argv[1], sys.argv[2]
    S = fib(2000)
    rows = []
    for f in sorted(glob.glob(os.path.join(d, 'ep*_*.npz'))):
        if 'align' in f or 'scan' in f:
            continue
        z = np.load(f, allow_pickle=False)
        a = json.loads(str(z['args']))
        P = z['pts'].astype(np.float64); C = z['cam'].astype(np.float64); fr = z['frame']
        lo, hi, vox = z['lo'], z['hi'], float(z['vox'])
        rng = np.random.default_rng(0)
        sub = rng.choice(len(P), min(len(P), 200000), replace=False) if len(P) else np.arange(0)
        Ps = P[sub]
        c = np.median(Ps, 0)
        # PCA frame of the points
        X = Ps - c
        w, V = np.linalg.eigh(np.cov(X.T)); V = V[:, ::-1]
        Y = X @ V
        ext = (np.percentile(Y, 99, 0) - np.percentile(Y, 1, 0)) * 100
        # cameras: one per frame
        uf, idx = np.unique(fr, return_index=True)
        Cf = C[idx]
        dv = Cf - c; dist = np.linalg.norm(dv, axis=1); u = dv / dist[:, None]
        cosmax = (S @ u.T).max(1) if len(u) else np.full(len(S), -1.0)
        cap30 = float(np.mean(cosmax > np.cos(np.radians(30))))
        cap60 = float(np.mean(cosmax > np.cos(np.radians(60))))
        worst = S[np.argmin(cosmax)]; worst_ang = float(np.degrees(np.arccos(np.clip(cosmax.min(), -1, 1))))
        m = u.mean(0); mn = m / max(np.linalg.norm(m), 1e-9)
        spread = np.degrees(np.arccos(np.clip(u @ mn, -1, 1)))
        # which PCA sides are seen: share of frames whose camera lies within 60 deg of +/- PCk
        uP = u @ V
        sides = {}
        for k in range(3):
            for sgn, nm in ((1, '+'), (-1, '-')):
                sides[f'{nm}pc{k+1}'] = round(float(np.mean(sgn * uP[:, k] > np.cos(np.radians(60)))), 3)
        # angular coverage of the points from their centre (crude: outer surface directions with points)
        pd = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
        lab = np.argmax(pd @ fib(500).T, axis=1)
        cnt = np.bincount(lab, minlength=500)
        angcov = float(np.mean(cnt >= 20))
        # vote grids
        H = z['hits']; F = z['free']
        surf = (H >= 3) & (H >= 0.5 * (H + F))
        seen_free = (F >= 1) & ~surf
        never = (H == 0) & (F == 0)
        # crop tightness: points within 5 mm of the ROI box faces (the box = roi mesh bounds + margin)
        dbox = np.minimum(Ps - lo, hi - Ps).min(1)
        near_box = float(np.mean(dbox < 0.005))
        # per-frame point counts
        pf = np.bincount(np.searchsorted(uf, fr[sub]))
        log = f[:-4] + '.log'
        lg = json.loads(open(log).read().strip().splitlines()[-1]) if os.path.exists(log) else {}
        row = dict(file=os.path.basename(f), obj=a.get('obj'), n_pts=int(len(P)), frames_with_pts=int(len(uf)),
                   frames_processed=lg.get('frames'), raw=lg.get('raw'), kept=lg.get('kept'),
                   frame_span=[int(uf.min()), int(uf.max())] if len(uf) else None,
                   roi=a.get('roi'), others=a.get('others'), hands=a.get('hands'), margin=a.get('margin'),
                   ext_pca_cm=np.round(ext, 1).tolist(), cam_dist_m_med=round(float(np.median(dist)), 3),
                   cam_spread_deg_p50_p90_max=[round(float(np.percentile(spread, q)), 1) for q in (50, 90, 100)],
                   view_cap30=round(cap30, 3), view_cap60=round(cap60, 3), unseen_dir_angle_deg=round(worst_ang, 1),
                   unseen_dir_pca=np.round(worst @ V, 2).tolist(), sides_pca=sides,
                   point_dir_cov=round(angcov, 3), grid_shape=list(H.shape), vox_mm=vox * 1000,
                   vox_surface=int(surf.sum()), vox_seen_free=int(seen_free.sum()),
                   vox_never_share=round(float(never.mean()), 3), near_roi_box_5mm=round(near_box, 4),
                   pts_per_frame_med=int(np.median(pf)) if len(pf) else 0)
        rows.append(row)
        print(json.dumps(row), flush=True)
    with open(out, 'w') as fo:
        for r in rows:
            fo.write(json.dumps(r) + '\n')


if __name__ == '__main__':
    main()
