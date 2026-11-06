"""GT-free section plots (cv2): observed points (train, voxel-avg, grey) vs mesh cross-sections (red, blue, green)."""
import sys, numpy as np, trimesh, cv2
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts')
import fit
obsf, out = sys.argv[1], sys.argv[2]; meshes = sys.argv[3:]
cfg = dict(fit.DEFAULT)
obs, grid = fit.load_obs(obsf, cfg)
P = obs['train']['p']
ms = [trimesh.load(m, force='mesh', process=False) for m in meshes]
c = P.mean(0); w, Vv = np.linalg.eigh(np.cov((P - c).T)); ax = Vv[:, ::-1]
R = float(sys.argv[0] and __import__("os").environ.get("SL_R", np.quantile(np.abs(P - c), 0.995) * 1.05))
N = int(__import__("os").environ.get("SL_N", 420)); R = float(R); sc = N / (2 * R)
cols = [(0, 0, 255), (255, 0, 0), (0, 160, 0)]
tiles = []
for i in range(3):
    n = ax[:, i]; t = (P - c) @ n; row = []
    u, v = ax[:, (i + 1) % 3], ax[:, (i + 2) % 3]
    for q in [0.25, 0.5, 0.75]:
        z0 = np.quantile(t, q)
        img = np.full((N, N, 3), 255, np.uint8)
        s = np.abs(t - z0) < 0.0015
        xy = np.c_[(P[s] - c) @ u, (P[s] - c) @ v] * sc + N / 2
        for x, y in xy.astype(int):
            if 0 <= x < N and 0 <= y < N: img[N - 1 - y, x] = (120, 120, 120)
        for k, m in enumerate(ms):
            sec = m.section(plane_origin=c + z0 * n, plane_normal=n)
            if sec is None: continue
            for e in sec.discrete:
                pp = np.c_[(e - c) @ u, (e - c) @ v] * sc + N / 2
                pp[:, 1] = N - 1 - pp[:, 1]
                cv2.polylines(img, [pp.astype(np.int32)], False, cols[k], 1)
        cv2.putText(img, f'ax{i} q{q} 10mm bar', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.line(img, (5, 25), (5 + int(0.01 * sc), 25), (0, 0, 0), 2)
        row.append(img)
    tiles.append(np.hstack(row))
cv2.imwrite(out, np.vstack(tiles))
