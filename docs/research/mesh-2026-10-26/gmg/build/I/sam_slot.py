"""Dev probe (GT-free; generator outputs of the 29 Oct probe, refused in clean mode): slot geometry of SAM 3D boards in
units of the generated board itself (thickness t, width W, length L along its own PCA axes). Raster of the face-on
view; the slot = the largest empty run inside the plate outline that touches one long edge."""
import sys, json, numpy as np, trimesh
from scipy import ndimage
G = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/gen/mesh-20261029-gen-f3fbeb0/results/gen'
out = {}
for f in ['sam3d/wooden_piece_1_k27_s42.ply', 'sam3d/wooden_piece_1_k27_s7.ply', 'sam3d/wooden_piece_2_k6_s42.ply',
          'sam3d/wooden_piece_2_k6_s7.ply', 'pixal_mv/ep23_wooden_piece_1_s42_gen.ply', 'pixal_mv/ep23_wooden_piece_2_s42_gen.ply']:
    m = trimesh.load(f'{G}/{f}', force='mesh'); X, _ = trimesh.sample.sample_surface(m, 300000, seed=0)
    c = X.mean(0); U = np.linalg.svd(X - c, full_matrices=False)[2]; A = (X - c) @ U.T
    # plate thickness: mode band of the thin axis (markers stick out); use the 25-75 % band of |a2| per in-plane cell
    a2 = A[:, 2]; t_core = np.percentile(a2, 75) - np.percentile(a2, 25)
    # plate core: points within the dense band (exclude marker posts)
    h, e = np.histogram(a2, 200); k = np.argmax(h); band = (a2 > e[max(k - 30, 0)]) & (a2 < e[min(k + 30, 199)])
    P = A[band]
    L = np.percentile(A[:, 0], 99.5) - np.percentile(A[:, 0], 0.5); W = np.percentile(A[:, 1], 99.5) - np.percentile(A[:, 1], 0.5)
    px = L / 400.0
    u = ((P[:, 0] - P[:, 0].min()) / px).astype(int); v = ((P[:, 1] - P[:, 1].min()) / px).astype(int)
    img = np.zeros((u.max() + 1, v.max() + 1), bool); img[u, v] = True
    img = ndimage.binary_closing(img, iterations=1)
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(img, iterations=int(0.06 * img.shape[1])))
    gap = filled & ~ndimage.binary_dilation(img, iterations=1)
    lab, n = ndimage.label(gap); best = None
    for i in range(1, n + 1):
        ii, jj = np.nonzero(lab == i)
        if len(ii) < 20: continue
        ext_u = (ii.max() - ii.min() + 1) * px; ext_v = (jj.max() - jj.min() + 1) * px
        rec = dict(area=len(ii), width=min(ext_u, ext_v), length=max(ext_u, ext_v), cu=ii.mean() * px / L, cv=jj.mean() * px / W)
        if best is None or rec['length'] > best['length']: best = rec
    # true plate thickness: thin-axis spread of the core band
    t = np.percentile(P[:, 2], 95) - np.percentile(P[:, 2], 5)
    r = dict(L=round(L, 4), W=round(W, 4), t_plate=round(t, 4))
    if best:
        r.update(slot_width_over_t=round(best['width'] / t, 2), slot_length_over_W=round(best['length'] / W, 2),
                 slot_width_over_L=round(best['width'] / L, 3), slot_centre_frac=[round(best['cu'], 2), round(best['cv'], 2)],
                 slot_len_over_L=round(best['length'] / L, 2))
    out[f] = r
print(json.dumps(out, indent=1))
