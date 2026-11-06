#!/usr/bin/env python
"""C2/R amendment A1 (PREREG section 11): GT-free removal of points that are not attached to the object.

The C0b cube ROI (+-0.30 m) admits static clutter around the resting rack. Rule, on the observed points alone:
  1. link points closer than LINK (12 mm = obs_points other_r, 3 vote voxels; AUDIT id 135, KEEP) into connected
     components (on 4 mm voxel representatives, the obs_points vote voxel; every point takes its voxel's component);
  2. the object's main body = the component with the most points;
  3. keep the main body and every other component whose centroid lies inside the convex hull of the main body
     (parts of the object that the removed table band disconnects, e.g. pegs standing on the unseen floor);
  4. drop everything else.
Output: the same npz keys (pts, cam, frame filtered; lo, hi, vox, hits, free, args copied) plus 'clean' (json).
Reads only obs_points npz files. Usage: python -I clean_pts.py IN.npz OUT.npz
"""
import json, sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import ConvexHull, cKDTree

LINK = 0.012
VOX = 0.004


def main():
    src, dst = sys.argv[1:3]
    Z = np.load(src)
    P = Z['pts'].astype(np.float64)
    key = np.floor(P / VOX).astype(np.int64)
    uk, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    rep = np.zeros((len(uk), 3)); np.add.at(rep, inv, P); rep /= np.bincount(inv, minlength=len(uk))[:, None]
    pairs = cKDTree(rep).query_pairs(LINK, output_type='ndarray')
    n = len(rep)
    G = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    nc, lab = connected_components(G, directed=False)
    plab = lab[inv]
    cnt = np.bincount(plab, minlength=nc)
    main = int(np.argmax(cnt))
    H = ConvexHull(rep[lab == main])                   # hull of the main body's voxel representatives
    cen = np.zeros((nc, 3)); np.add.at(cen, plab, P); cen /= np.maximum(cnt, 1)[:, None]
    inside = np.all(cen @ H.equations[:, :3].T + H.equations[:, 3] <= 1e-9, axis=1)
    keepc = inside | (np.arange(nc) == main)
    keep = keepc[plab]
    info = dict(rule='C2/R A1: largest 12 mm-linked component + components with centroid inside its convex hull',
                link_m=LINK, vox_m=VOX, n_in=int(len(P)), n_out=int(keep.sum()), frac_kept=round(float(keep.mean()), 4),
                n_components=int(nc), main_points=int(cnt[main]), kept_components=int(keepc.sum()),
                dropped_points=int((~keep).sum()))
    out = {k: Z[k] for k in Z.files if k not in ('pts', 'cam', 'frame')}
    out.update(pts=Z['pts'][keep], cam=Z['cam'][keep], frame=Z['frame'][keep], clean=np.array(json.dumps(info)))
    np.savez_compressed(dst, **out)
    print(json.dumps(info))


if __name__ == '__main__':
    main()
