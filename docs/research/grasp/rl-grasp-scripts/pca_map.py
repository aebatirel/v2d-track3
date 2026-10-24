"""Top view (PCA axis1 x axis2, 1 cm cells) of a plate mesh: thickness along axis3 in mm ('.' = empty).
Ring handle at negative axis1 (same convention as audit-plates robot_where.py)."""
import sys, numpy as np, trimesh
for glb in sys.argv[1:]:
    m = trimesh.load(glb, force='mesh'); V = m.vertices; c = V.mean(0)
    W = np.linalg.svd(V - c, full_matrices=False)[2]; P = (V - c) @ W.T
    lo = P[P[:, 0] < np.percentile(P[:, 0], 15)]; hi = P[P[:, 0] > np.percentile(P[:, 0], 85)]
    if np.ptp(lo[:, 1]) > np.ptp(hi[:, 1]):
        W[0] *= -1; W[1] *= -1
    pts, _ = trimesh.sample.sample_surface_even(m, 40000, seed=0); P = (pts - c) @ W.T
    print(glb.split('/')[-2], glb.split('/')[-1], 'c', np.round(c * 100, 2), 'W', np.round(W, 3).tolist())
    print('axis3 range cm', np.round(100 * P[:, 2].min(), 1), np.round(100 * P[:, 2].max(), 1))
    g = 0.01; xs = np.arange(np.floor(P[:, 0].min() * 100) / 100, P[:, 0].max() + g, g); ys = np.arange(np.floor(P[:, 1].min() * 100) / 100, P[:, 1].max() + g, g)
    print('cols axis1 cm:', ' '.join(f'{100*x:3.0f}' for x in xs))
    for y0 in ys[::-1]:
        row = []
        for x0 in xs:
            k = (P[:, 0] >= x0) & (P[:, 0] < x0 + g) & (P[:, 1] >= y0) & (P[:, 1] < y0 + g)
            row.append('  .' if k.sum() < 5 else f'{int(round(1000 * (P[k, 2].max() - P[k, 2].min()))):3d}')
        print(f'{100 * y0:5.0f} ' + ' '.join(row))
