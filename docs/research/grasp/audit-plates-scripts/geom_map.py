"""Thickness map of a plate-like mesh in its PCA plane (axis1 x axis2), 1 cm cells: max-min along axis 3 (mm),
and a picture (top + two side projections)."""
import sys
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, axs = plt.subplots(2, 3, figsize=(15, 9))
for r, name in enumerate(['mini_sweeper', 'mini_dust_pan']):
    m = trimesh.load(f'{sys.argv[1]}/{name}.glb', force='mesh'); V = m.vertices; c = V.mean(0)
    _, S, W = np.linalg.svd(V - c, full_matrices=False)
    pts, _ = trimesh.sample.sample_surface_even(m, 60000, seed=0); P = (pts - c) @ W.T
    # also report in the object frame (glb axes) to relate to the reference
    print(name, 'PCA axes rows (object frame):', np.round(W, 3).tolist())
    g = 0.01; xs = np.arange(P[:, 0].min(), P[:, 0].max() + g, g); ys = np.arange(P[:, 1].min(), P[:, 1].max() + g, g)
    print(f'{name}: thickness (mm) per 1 cm cell; rows = axis2 (cm), cols = axis1 (cm) from {100*xs[0]:.1f}')
    for y0 in ys[::-1]:
        row = []
        for x0 in xs:
            k = (P[:, 0] >= x0) & (P[:, 0] < x0 + g) & (P[:, 1] >= y0) & (P[:, 1] < y0 + g)
            row.append('  .' if k.sum() < 5 else f'{int(round(1000 * (P[k, 2].max() - P[k, 2].min()))):3d}')
        print(f'{100 * y0:6.1f} ' + ' '.join(row))
    for k_, (i, j) in enumerate([(0, 1), (0, 2), (1, 2)]):
        a = axs[r, k_]; a.scatter(P[::5, i] * 100, P[::5, j] * 100, s=0.3, c=P[::5, 3 - i - j] * 100, cmap='viridis'); a.set_aspect('equal')
        a.set_xlabel(f'PCA axis {i+1} (cm)'); a.set_ylabel(f'PCA axis {j+1} (cm)'); a.set_title(name)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=80)
