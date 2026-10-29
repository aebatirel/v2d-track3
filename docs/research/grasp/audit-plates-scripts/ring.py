"""Handle-ring dimensions of a plate mesh: 2 mm occupancy grid of dense surface samples in the PCA plane; the hole =
largest free region enclosed near the narrow end; reports hole size (largest inscribed circle), outer ring size,
band width at the end, and the band thickness (axis-3 extent of samples in the band). Mesh path argument."""
import sys
import numpy as np, trimesh
from scipy import ndimage
m = trimesh.load(sys.argv[1], force='mesh'); V = m.vertices; c = V.mean(0)
W = np.linalg.svd(V - c, full_matrices=False)[2]; P = (V - c) @ W.T
lo = P[P[:, 0] < np.percentile(P[:, 0], 15)]; hi = P[P[:, 0] > np.percentile(P[:, 0], 85)]
if np.ptp(lo[:, 1]) > np.ptp(hi[:, 1]):
    W[0] *= -1; W[1] *= -1
S = (trimesh.sample.sample_surface(m, 400000, seed=0)[0] - c) @ W.T
g = 0.002; x0, y0 = S[:, 0].min() - 0.01, S[:, 1].min() - 0.01
ix = ((S[:, 0] - x0) / g).astype(int); iy = ((S[:, 1] - y0) / g).astype(int)
occ = np.zeros((ix.max() + 6, iy.max() + 6), bool); occ[ix, iy] = True
occ = ndimage.binary_closing(occ, iterations=2)
filled = ndimage.binary_fill_holes(occ); holes = filled & ~occ
lab, n = ndimage.label(holes)
sizes = ndimage.sum(holes, lab, range(1, n + 1))
print(sys.argv[1].split('/')[-1], f'outline extents axis1 {100 * np.ptp(S[:, 0]):.1f} cm, axis2 {100 * np.ptp(S[:, 1]):.1f} cm, axis3 {100 * np.ptp(S[:, 2]):.1f} cm')
for k in np.argsort(-sizes)[:2]:
    if sizes[k] * g * g < 1e-4:
        continue
    hm = lab == k + 1; dt = ndimage.distance_transform_edt(hm) * g
    cx, cy = np.argwhere(hm).mean(0) * g + [x0, y0]
    xs, ys = np.argwhere(hm)[:, 0] * g + x0, np.argwhere(hm)[:, 1] * g + y0
    print(f'  hole: area {sizes[k] * g * g * 1e4:.1f} cm2, inscribed diameter {200 * dt.max():.1f} cm, extent axis1 {100 * np.ptp(xs):.1f} x axis2 {100 * np.ptp(ys):.1f} cm, centre ({100 * cx:.1f}, {100 * cy:.1f}) cm')
    # band from hole edge to the outer end along -axis1 (the ring end), at the hole's axis2 centre
    lane = S[np.abs(S[:, 1] - cy) < 0.004]
    end = lane[:, 0].min(); hole_lo = xs.min()
    band = lane[(lane[:, 0] < hole_lo) & (lane[:, 0] >= end)]
    print(f'  ring end band (axis1 {100 * end:.1f}..{100 * hole_lo:.1f} cm): width {100 * (hole_lo - end):.1f} cm, thickness (axis3 extent) {100 * np.ptp(band[:, 2]) if len(band) else float("nan"):.1f} cm')
    side = S[(np.abs(S[:, 0] - cx) < 0.004)]
    yy = np.sort(side[:, 1]); print(f'  outer ring width across the hole centre (axis2): {100 * np.ptp(yy):.1f} cm; side band thickness {100 * np.ptp(side[np.abs(side[:, 1] - ys.min() + 0.006) < 0.004][:, 2]) if len(side) else float("nan"):.1f} cm')
